import pytest
from lib.binance.rest.client import BinanceClient
from lib.binance.rest.exceptions import BinanceAPICredentialsException, BinanceMissingEndpointException, BinanceRestException
from tests.binance.mock_responses import MOCK_RESPONSES

base_url = "https://testnet.binance.vision"

def test_get_exchange_info(requests_mock):
    requests_mock.get(f'{base_url}/api/v3/exchangeInfo', json=MOCK_RESPONSES['getExchangeInfo'])

    client = BinanceClient(base_url=base_url)
    resp = client.request('getExchangeInfo')
    assert resp == MOCK_RESPONSES['getExchangeInfo']

def test_requests_fail_status_code(requests_mock):
    requests_mock.get(f'{base_url}/api/v3/exchangeInfo', status_code=400, json={'resp': 'bad request'})

    client = BinanceClient(base_url=base_url)
    with pytest.raises(BinanceRestException) as e_info:
        client.request('getExchangeInfo')

def test_missing_endpoint_exception():
    client = BinanceClient(base_url=base_url)
    with pytest.raises(BinanceMissingEndpointException) as e_info:
        client.request('random')

def test_get_account(requests_mock):
    requests_mock.get(f'{base_url}/api/v3/account', json=MOCK_RESPONSES['getAccount'])

    client = BinanceClient(base_url=base_url, key="key", secret="secret")
    resp = client.request('getAccount')
    assert resp == MOCK_RESPONSES['getAccount']

def test_missing_api_credentials_for_signed_endpoints():
    client = BinanceClient(base_url=base_url)
    with pytest.raises(BinanceAPICredentialsException) as e_info:
        client.request('getAccount')
