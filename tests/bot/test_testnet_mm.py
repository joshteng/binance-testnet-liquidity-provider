import pytest
import requests_mock as rm
from tests.bot.mock_responses import MOCK_RESPONSES


def test_default_state():
    from bot.testnet_mm_state import TestnetMMState

    assert TestnetMMState.PRODUCTION_LAST_PRICE == '0'
    assert TestnetMMState.PAST_ORDERS == []
    assert TestnetMMState.OPEN_ORDERS == {
        'bids': [],
        'asks': []
    }

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

    kwargs['mock'].get(rm.ANY, json=MOCK_RESPONSES['getAccountWithoutBalance'])

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

    assert mm._get_balances(base_asset, quote_asset) == ('0.00000000', '0.00000000')

    with pytest.raises(TestnetMMInsufficientFundsException):
        TestnetMMState.PRODUCTION_LAST_PRICE = '1'
        mm._trade()

@rm.Mocker(kw='mock')
def test_trade_with_quote_asset_and_no_base_asset(**kwargs):
    from unittest.mock import MagicMock
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    kwargs['mock'].get(rm.ANY, json=MOCK_RESPONSES['getAccountWithoutBase'])

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    mm._buy_base_asset = MagicMock()

    base_asset_qty, quote_asset_qty = mm._get_balances(base_asset, quote_asset)
    assert float(quote_asset_qty) > 0
    assert float(base_asset_qty) == 0

    TestnetMMState.PRODUCTION_LAST_PRICE = '1'
    mm._trade()
    assert mm._buy_base_asset.called


@rm.Mocker(kw='mock')
def test_trade_with_base_asset_and_no_quote_asset(**kwargs):
    from unittest.mock import MagicMock
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    kwargs['mock'].get(rm.ANY, json=MOCK_RESPONSES['getAccountWithoutQuote'])

    base_asset, quote_asset = 'BTC', 'BUSD'

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')
    mm._buy_quote_asset = MagicMock()

    base_asset_qty, quote_asset_qty = mm._get_balances(base_asset, quote_asset)
    assert float(quote_asset_qty) == 0
    assert float(base_asset_qty) > 0

    TestnetMMState.PRODUCTION_LAST_PRICE = '1'
    mm._trade()
    assert mm._buy_quote_asset.called

def test_truncate_quantity():
    from decimal import Decimal
    from bot.testnet_mm import TestnetMM

    mm = TestnetMM()
    assert mm._truncate_quantity(Decimal('126.395930994')) == '126.395930'

def test_truncate_price():
    from decimal import Decimal
    from bot.testnet_mm import TestnetMM

    mm = TestnetMM()
    assert mm._truncate_price(Decimal('126.395930294')) == '126.390000'

def test_buy_base_asset():
    from decimal import Decimal
    from unittest.mock import MagicMock
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    quote_asset_qty = '10000'
    distance_from_mid_price = '0.1'
    TestnetMMState.PRODUCTION_LAST_PRICE = 1000

    mm = TestnetMM(distance_from_mid_price=distance_from_mid_price)

    mm._place_bid = MagicMock()
    mm._buy_base_asset(quote_asset_qty)

    bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') - Decimal(distance_from_mid_price))
    bid_quantity = Decimal(quote_asset_qty) / Decimal('2') / bid_price

    mm._place_bid.assert_called_with(mm._truncate_quantity(bid_quantity), mm._truncate_price(bid_price))


def test_buy_quote_asset():
    from decimal import Decimal
    from unittest.mock import MagicMock
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    base_asset_qty = '2.78'
    distance_from_mid_price = '0.1'
    TestnetMMState.PRODUCTION_LAST_PRICE = 1000

    mm = TestnetMM(distance_from_mid_price=distance_from_mid_price)

    mm._place_ask = MagicMock()
    mm._buy_quote_asset(base_asset_qty)

    bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') + Decimal(distance_from_mid_price))
    bid_quantity = Decimal(base_asset_qty) / Decimal('2')

    mm._place_ask.assert_called_with(mm._truncate_quantity(bid_quantity), mm._truncate_price(bid_price))


@pytest.fixture
def reset_state():
    from bot.testnet_mm_state import TestnetMMState
    TestnetMMState.PAST_ORDERS = []
    TestnetMMState.OPEN_ORDERS = {
        'bids': [],
        'asks': []
    }

def test_place_bid(requests_mock, reset_state):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    base_url = "https://testnet.binance.vision"

    base_asset, quote_asset = 'BTC', 'BUSD'
    symbol = base_asset + quote_asset
    order_qty, order_price = '0.00100000', '1500.00000000'

    mocked = MOCK_RESPONSES['postOrderBuySuccess']
    mocked['symbol'] = symbol
    mocked['price'] = order_price
    mocked['origQty'] = order_qty

    requests_mock.post(base_url + '/api/v3/order', json=mocked)

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

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

def test_place_ask(requests_mock, reset_state):
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState

    base_url = "https://testnet.binance.vision"

    base_asset, quote_asset = 'BTC', 'BUSD'
    symbol = base_asset + quote_asset
    order_qty, order_price = '0.00100000', '1500.00000000'

    mocked = MOCK_RESPONSES['postOrderSellSuccess']
    mocked['symbol'] = symbol
    mocked['price'] = order_price
    mocked['origQty'] = order_qty

    requests_mock.post(base_url + '/api/v3/order', json=mocked)

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

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
def failed_order(requests_mock):
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

def test_place_bid_throws_exception_if_failed(failed_order):
    from bot.testnet_mm import TestnetMM
    from bot.exceptions import TestnetMMOrderFailedException

    base_asset, quote_asset, quantity, price = failed_order

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

    with pytest.raises(TestnetMMOrderFailedException):
        mm._place_bid(quantity, price)

def test_place_ask_throws_exception_if_failed(failed_order):
    from bot.testnet_mm import TestnetMM
    from bot.exceptions import TestnetMMOrderFailedException

    base_asset, quote_asset, quantity, price = failed_order

    mm = TestnetMM(base_asset, quote_asset, 'key', 'secret')

    with pytest.raises(TestnetMMOrderFailedException):
        mm._place_ask(quantity, price)
