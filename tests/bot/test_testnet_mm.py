import pytest
import requests_mock as rm
from unittest.mock import MagicMock, patch
from lib.binance.rest.exceptions import BinanceRestException
from tests.bot.mock_responses import MOCK_RESPONSES


def test_default_state():
    from bot.testnet_mm_state import TestnetMMState

    assert TestnetMMState.PRODUCTION_LAST_PRICE == '0'
    assert TestnetMMState.PAST_ORDERS == []
    assert TestnetMMState.OPEN_ORDERS == {
        'bids': [],
        'asks': []
    }

def test_run():
    from bot.testnet_mm import TestnetMM

    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')

    mm._cancel_open_orders = MagicMock()
    mm._connect_to_production_trade_stream = MagicMock()
    mm._keep_alive = MagicMock()
    mm._get_asset_filters = MagicMock()

    mm.run()

    assert mm.keep_alive == True
    assert mm._cancel_open_orders.called
    assert mm._connect_to_production_trade_stream.called
    assert mm._keep_alive.called
    assert mm._get_asset_filters.called

def test_trade_without_last_price():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    mm = TestnetMM('BTC', 'BUSD')
    assert TestnetMMState.PRODUCTION_LAST_PRICE == '0'
    assert mm._trade() == False

@rm.Mocker(kw='mock')
def test_get_balances(**kwargs):
    from bot.testnet_mm import TestnetMM

    kwargs['mock'].get(rm.ANY, json=MOCK_RESPONSES['getAccountWithBalance'])

    base_asset, quote_asset = 'BTC', 'BUSD'

    for balance in MOCK_RESPONSES['getAccountWithBalance']['balances']:
        if balance['asset'] == base_asset:
            base_asset_qty = balance['free']
        if balance['asset'] == quote_asset:
            quote_asset_qty = balance['free']

    assert TestnetMM(base_asset, quote_asset, 'key', 'secret')._get_balances(base_asset, quote_asset) == (base_asset_qty, quote_asset_qty)

@rm.Mocker(kw='mock')
def test_trade_without_funds(**kwargs):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState
    from bot.exceptions import TestnetMMInsufficientFundsException

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    kwargs['mock'].get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm._get_asset_filters()

    kwargs['mock'].get(rm.ANY, json=MOCK_RESPONSES['getAccountWithoutBalance'])
    assert mm._get_balances(base_asset, quote_asset) == ('0.00000000', '0.00000000')

    with pytest.raises(TestnetMMInsufficientFundsException):
        TestnetMMState.PRODUCTION_LAST_PRICE = '1'
        mm._trade()

@rm.Mocker(kw='mock')
def test_trade_with_quote_asset_and_no_base_asset(**kwargs):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    kwargs['mock'].get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm._get_asset_filters()
    mm._buy_base_asset = MagicMock()
    mm._cancel_open_orders = MagicMock()

    # min notional is 10, so any value below or equal to 10 (accounting for fees) is insufficient
    price = 10000
    btc_balance = 10 / price
    TestnetMMState.PRODUCTION_LAST_PRICE = str(price)

    mock_response = MOCK_RESPONSES['getAccountWithoutBase']
    mock_response['balances'].append({'asset': 'BTC', 'free': str(btc_balance), 'locked': '0.00000000'})
    kwargs['mock'].get(rm.ANY, json=mock_response)

    base_asset_qty, quote_asset_qty = mm._get_balances(base_asset, quote_asset)
    assert float(quote_asset_qty) > 0
    assert float(base_asset_qty) == btc_balance

    mm._trade()
    assert mm._cancel_open_orders.called
    assert mm._buy_base_asset.called


@rm.Mocker(kw='mock')
def test_trade_with_base_asset_and_no_quote_asset(**kwargs):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    kwargs['mock'].get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm._get_asset_filters()
    mm._buy_quote_asset = MagicMock()
    mm._cancel_open_orders = MagicMock()

    # min notional is 10, so any value below or equal to 10 (accounting for fees) is insufficient
    busd_balance = 10

    mock_response = MOCK_RESPONSES['getAccountWithoutQuote']
    mock_response['balances'].append({'asset': 'BUSD', 'free': f'{busd_balance}.00000000', 'locked': '0.00000000'})
    kwargs['mock'].get(rm.ANY, json=mock_response)
    base_asset_qty, quote_asset_qty = mm._get_balances(base_asset, quote_asset)
    assert float(quote_asset_qty) == busd_balance
    assert float(base_asset_qty) > 0

    TestnetMMState.PRODUCTION_LAST_PRICE = '10000'
    mm._trade()
    assert mm._cancel_open_orders.called
    assert mm._buy_quote_asset.called

@rm.Mocker(kw='mock')
def test_trade_with_sufficient_base_asset_and_quote_asset(**kwargs):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    kwargs['mock'].get(rm.ANY, json=MOCK_RESPONSES['getAccountWithBalance'])
    kwargs['mock'].get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    mm._get_asset_filters()
    mm._provide_liquidity = MagicMock()
    mm._cancel_open_orders = MagicMock()

    base_asset_qty, quote_asset_qty = mm._get_balances(base_asset, quote_asset)
    assert float(quote_asset_qty) > 0
    assert float(base_asset_qty) > 0

    TestnetMMState.PRODUCTION_LAST_PRICE = '1000'
    mm._trade()
    assert mm._cancel_open_orders.called
    mm._provide_liquidity.assert_called_with(
        base_asset_available=base_asset_qty,
        quote_asset_available=quote_asset_qty
    )

@pytest.fixture
def setup_filters(requests_mock):
    from bot.testnet_mm import TestnetMM
    requests_mock.get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm = TestnetMM()
    mm._get_asset_filters()
    return mm

def test_truncate_quantity(setup_filters):
    from decimal import Decimal
    mm = setup_filters
    assert mm._truncate_quantity(Decimal('126.395930994')) == '126.395930'

def test_truncate_price(setup_filters):
    from decimal import Decimal
    mm = setup_filters
    assert mm._truncate_price(Decimal('126.395930294')) == '126.390000'

def test_buy_base_asset(requests_mock):
    from decimal import Decimal
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState


    quote_asset_qty = '10000'
    distance_from_mid_price = '0.1'
    TestnetMMState.PRODUCTION_LAST_PRICE = 1000

    mm = TestnetMM(distance_from_mid_price=distance_from_mid_price)
    requests_mock.get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm._get_asset_filters()

    mm._place_bid = MagicMock()
    mm._buy_base_asset(quote_asset_qty)

    bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') - Decimal(distance_from_mid_price))
    bid_quantity = Decimal(quote_asset_qty) / Decimal('2') / bid_price

    mm._place_bid.assert_called_with(mm._truncate_quantity(bid_quantity), mm._truncate_price(bid_price))


def test_buy_quote_asset(requests_mock):
    from decimal import Decimal
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    base_asset_qty = '2.78'
    distance_from_mid_price = '0.1'
    TestnetMMState.PRODUCTION_LAST_PRICE = 1000

    mm = TestnetMM(distance_from_mid_price=distance_from_mid_price)
    requests_mock.get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm._get_asset_filters()

    mm._place_ask = MagicMock()
    mm._buy_quote_asset(base_asset_qty)

    bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') + Decimal(distance_from_mid_price))
    bid_quantity = Decimal(base_asset_qty) / Decimal('2')

    mm._place_ask.assert_called_with(mm._truncate_quantity(bid_quantity), mm._truncate_price(bid_price))

def test_provide_liquidity(requests_mock):
    from decimal import Decimal
    from bot.testnet_mm_state import TestnetMMState
    from bot.testnet_mm import TestnetMM

    distance_from_mid_price = '0.01'
    base_asset_available = '1'
    quote_asset_available = '10000'
    TestnetMMState.PRODUCTION_LAST_PRICE = '1000'

    bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') - Decimal(distance_from_mid_price))
    ask_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') + Decimal(distance_from_mid_price))

    max_quantity_to_sell = Decimal(base_asset_available)
    max_quantity_to_buy = Decimal(quote_asset_available) / bid_price
    order_qty = min(max_quantity_to_sell, max_quantity_to_buy)

    mm = TestnetMM(distance_from_mid_price=distance_from_mid_price)
    requests_mock.get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])
    mm._get_asset_filters()
    mm._place_bid = MagicMock()
    mm._place_ask = MagicMock()
    mm._provide_liquidity(base_asset_available, quote_asset_available)

    truncated_order_qty = mm._truncate_quantity(order_qty)
    mm._place_bid.assert_called_with(truncated_order_qty, mm._truncate_price(bid_price))
    mm._place_ask.assert_called_with(truncated_order_qty, mm._truncate_price(ask_price))


@pytest.fixture
def place_bid_or_ask_setup(requests_mock):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState
    TestnetMMState.PAST_ORDERS = []
    TestnetMMState.OPEN_ORDERS = {
        'bids': [],
        'asks': []
    }

    base_url = "https://testnet.binance.vision"

    base_asset, quote_asset = 'BTC', 'BUSD'
    symbol = base_asset + quote_asset
    order_qty, order_price = '0.00100000', '1500.00000000'

    mocked = MOCK_RESPONSES['postOrder']
    mocked['symbol'] = symbol
    mocked['price'] = order_price
    mocked['origQty'] = order_qty

    requests_mock.post(base_url + '/api/v3/order', json=mocked)

    return order_qty, order_price, mocked, TestnetMM(base_asset, quote_asset, 'key', 'secret')


def test_place_bid(place_bid_or_ask_setup):
    from bot.testnet_mm_state import TestnetMMState

    order_qty, order_price, mocked, mm = place_bid_or_ask_setup

    mm._place_bid(order_qty, order_price)

    order_details = {
        'orderId': mocked['orderId'],
        'clientOrderId': mocked['clientOrderId'],
        'transactTime': mocked['transactTime'],
        'status': mocked['status'],
        'symbol': mocked['symbol'],
        'side': mocked['side'],
        'type': mocked['type'],
        'price': mocked['price'],
        'origQty': mocked['origQty'],
        'executedQty': mocked['executedQty'],
    }

    assert TestnetMMState.PAST_ORDERS == [order_details]

    assert TestnetMMState.OPEN_ORDERS['bids'] == [order_details]

def test_place_ask(place_bid_or_ask_setup):
    from bot.testnet_mm_state import TestnetMMState

    order_qty, order_price, mocked, mm = place_bid_or_ask_setup

    mm._place_ask(order_qty, order_price)

    order_details = {
        'orderId': mocked['orderId'],
        'clientOrderId': mocked['clientOrderId'],
        'transactTime': mocked['transactTime'],
        'status': mocked['status'],
        'symbol': mocked['symbol'],
        'side': mocked['side'],
        'type': mocked['type'],
        'price': mocked['price'],
        'origQty': mocked['origQty'],
        'executedQty': mocked['executedQty'],
    }

    assert TestnetMMState.PAST_ORDERS == [order_details]

    assert TestnetMMState.OPEN_ORDERS['asks'] == [order_details]


@pytest.fixture
def bad_order(requests_mock):
    base_url = "https://testnet.binance.vision"
    base_asset, quote_asset = 'BTC', 'BUSD'
    symbol = base_asset + quote_asset
    price, quantity = 0, 0

    mocked = MOCK_RESPONSES['postOrder']
    mocked['symbol'] = symbol
    mocked['price'] = price
    mocked['origQty'] = quantity
    mocked['orderId'] = ''

    requests_mock.post(base_url + '/api/v3/order', json=mocked)

    return base_asset, quote_asset, quantity, price

def test_place_bid_throws_exception_if_failed(bad_order):
    from bot.testnet_mm import TestnetMM
    from bot.exceptions import TestnetMMOrderFailedException

    base_asset, quote_asset, quantity, price = bad_order

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

    with pytest.raises(TestnetMMOrderFailedException):
        mm._place_bid(quantity, price)

def test_place_ask_throws_exception_if_failed(bad_order):
    from bot.testnet_mm import TestnetMM
    from bot.exceptions import TestnetMMOrderFailedException

    base_asset, quote_asset, quantity, price = bad_order

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

    with pytest.raises(TestnetMMOrderFailedException):
        mm._place_ask(quantity, price)

def test_clear_open_order():
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.OPEN_ORDERS = {
        'bids': [{'orderId': 'someOrder'}],
        'asks': [{'orderId': 'someOrder'}]
    }
    TestnetMMState.clear_open_orders()

    assert TestnetMMState.OPEN_ORDERS == {
        'bids': [],
        'asks': []
    }

@rm.Mocker(kw='mock')
def test_cancel_order(**kwargs):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.clear_open_orders = MagicMock()
    kwargs['mock'].delete(rm.ANY, json=MOCK_RESPONSES['deleteOpenOrdersSuccess'])

    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')
    mm._cancel_open_orders()

    assert TestnetMMState.clear_open_orders.called

@patch('lib.binance.rest.client.requests')
def test_cancel_order_handle_exception(mock_requests):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.reason = 'Bad Request'
    mock_response.json.return_value = MOCK_RESPONSES['deleteOpenOrdersHandledError']

    TestnetMMState.clear_open_orders = MagicMock()
    mock_requests.delete.return_value = mock_response

    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')

    try:
        mm._cancel_open_orders()
    except Exception as exc:
        assert False, f"'sum_x_y' raised an exception {exc}"


@patch('lib.binance.rest.client.requests')
def test_cancel_order_unhandled_exception(mock_requests):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.reason = 'Bad Request'
    mock_response.json.return_value = MOCK_RESPONSES['deleteOpenOrdersUnhandledError']

    TestnetMMState.clear_open_orders = MagicMock()
    mock_requests.delete.return_value = mock_response

    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')

    with pytest.raises(BinanceRestException):
        mm._cancel_open_orders()

def test_has_no_open_orders_return_true():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.OPEN_ORDERS = {
        'bids': [],
        'asks': []
    }
    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')
    assert mm._has_no_open_orders() == True

def test_has_no_open_orders_return_false():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.OPEN_ORDERS = {
        'bids': [{
            'price': '995'
        }],
        'asks': [{
            'price': '1005'
        }]
    }
    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')
    assert mm._has_no_open_orders() == False

@pytest.fixture
def open_orders():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.OPEN_ORDERS = {
        'bids': [{
            'price': '995'
        }],
        'asks': [{
            'price': '1005'
        }]
    }
    return TestnetMM('BTC', 'BUSD', 'key', 'secret')

def test_has_open_orders_and_production_price_reached_return_true_when_bid_reached(open_orders):
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.PRODUCTION_LAST_PRICE = '995'

    mm = open_orders

    assert mm._has_open_orders_and_production_price_reached() == True

def test_has_open_orders_and_production_price_reached_return_true_when_ask_reached(open_orders):
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.PRODUCTION_LAST_PRICE = '1005'

    mm = open_orders

    assert mm._has_open_orders_and_production_price_reached() == True

def test_has_open_orders_and_production_price_reached_return_true(open_orders):
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.PRODUCTION_LAST_PRICE = '1000'

    mm = open_orders
    assert mm._has_open_orders_and_production_price_reached() == False

def test_trade_does_not_place_orders_with_existing_open_orders():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.PRODUCTION_LAST_PRICE = '1000'
    TestnetMMState.OPEN_ORDERS = {
        'bids': [{
            'price': '995'
        }],
        'asks': [{
            'price': '1005'
        }]
    }

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    mm._place_trade = MagicMock()
    mm._trade()
    assert not mm._place_trade.called

def test_trade_places_orders_when_open_bid_orders_price_reached():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.PRODUCTION_LAST_PRICE = '995'
    TestnetMMState.OPEN_ORDERS = {
        'bids': [{
            'price': '995'
        }],
        'asks': [{
            'price': '1005'
        }]
    }

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    mm._place_trade = MagicMock()
    mm._trade()
    assert mm._place_trade.called

def test_trade_places_orders_when_open_ask_orders_price_reached():
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    TestnetMMState.PRODUCTION_LAST_PRICE = '1005'
    TestnetMMState.OPEN_ORDERS = {
        'bids': [{
            'price': '995'
        }],
        'asks': [{
            'price': '1005'
        }]
    }

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    mm._place_trade = MagicMock()
    mm._trade()
    assert mm._place_trade.called

def test_get_asset_filters(requests_mock):
    from bot.testnet_mm import TestnetMM

    requests_mock.get('https://testnet.binance.vision/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])

    mm = TestnetMM('BTC', 'BUSD')
    mm._get_asset_filters()

    assert mm.base_asset_precision == {'BNBBUSD': 2, 'BTCBUSD': 6, 'ETHBUSD': 5, 'LTCBUSD': 5, 'TRXBUSD': 1, 'XRPBUSD': 1, 'BNBUSDT': 2, 'BTCUSDT': 6, 'ETHUSDT': 5, 'LTCUSDT': 5, 'TRXUSDT': 1, 'XRPUSDT': 1, 'BNBBTC': 2, 'ETHBTC': 5, 'LTCBTC': 5, 'TRXBTC': 1, 'XRPBTC': 1, 'LTCBNB': 5, 'TRXBNB': 1, 'XRPBNB': 1}

    assert mm.price_precision == {'BNBBUSD': 2, 'BTCBUSD': 2, 'ETHBUSD': 2, 'LTCBUSD': 2, 'TRXBUSD': 5, 'XRPBUSD': 4, 'BNBUSDT': 2, 'BTCUSDT': 2, 'ETHUSDT': 2, 'LTCUSDT': 2, 'TRXUSDT': 5, 'XRPUSDT': 4, 'BNBBTC': 6, 'ETHBTC': 6, 'LTCBTC': 6, 'TRXBTC': 8, 'XRPBTC': 8, 'LTCBNB': 4, 'TRXBNB': 7, 'XRPBNB': 6}

    assert mm.min_notional == {'BNBBUSD': '10.00000000', 'BTCBUSD': '10.00000000', 'ETHBUSD': '10.00000000', 'LTCBUSD': '10.00000000', 'TRXBUSD': '10.00000000', 'XRPBUSD': '10.00000000', 'BNBUSDT': '10.00000000', 'BTCUSDT': '10.00000000', 'ETHUSDT': '10.00000000', 'LTCUSDT': '10.00000000', 'TRXUSDT': '10.00000000', 'XRPUSDT': '10.00000000', 'BNBBTC': '0.00010000', 'ETHBTC': '0.00010000', 'LTCBTC': '0.00010000', 'TRXBTC': '0.00010000', 'XRPBTC': '0.00010000', 'LTCBNB': '0.10000000', 'TRXBNB': '0.10000000', 'XRPBNB': '0.10000000'}

def test_get_listen_key(requests_mock):
    from bot.testnet_mm import TestnetMM
    mm = TestnetMM('BTC', 'BUSD', 'key', 'secret')

    requests_mock.post('https://testnet.binance.vision/api/v3/userDataStream', json={'listenKey': 'abc'})

    mm._get_listen_key()
    assert mm.listen_key == 'abc'
