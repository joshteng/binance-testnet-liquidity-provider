import pytest
import requests_mock as rm
from tests.bot.mock_responses import MOCK_RESPONSES


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
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState
    from unittest.mock import MagicMock

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
    from bot.testnet_mm import TestnetMM
    from bot.testnet_mm_state import TestnetMMState
    from unittest.mock import MagicMock

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

@rm.Mocker(kw='mock')
def test_truncate_price(**kwargs):
    pass

@rm.Mocker(kw='mock')
def test_truncate_quantity(**kwargs):
    pass

@rm.Mocker(kw='mock')
def test_buy_quote_asset(**kwargs):
    pass

@rm.Mocker(kw='mock')
def test_buy_base_asset(**kwargs):
    pass

