import pytest
from lib.binance.rest.client import BinanceClient
from lib.binance.rest.exceptions import BinanceMissingEndpointExceptions, BinanceRestExceptions

base_url = "https://testnet.binance.vision"

def test_get_exchange_info(requests_mock):
    requests_mock.get(f'{base_url}/api/v3/exchangeInfo', json={'timezone': 'UTC', 'symbols': [{'symbol': 'BNBBUSD'}]})

    client = BinanceClient(base_url=base_url)
    resp = client.request('getExchangeInfo')
    assert resp == {'timezone': 'UTC', 'symbols': [{'symbol': 'BNBBUSD'}]}

def test_requests_fail_status_code(requests_mock):
    requests_mock.get(f'{base_url}/api/v3/exchangeInfo', status_code=400, json={'resp': 'bad request'})

    client = BinanceClient(base_url=base_url)
    with pytest.raises(BinanceRestExceptions) as e_info:
        client.request('getExchangeInfo')

def test_missing_endpoint_exception():
    client = BinanceClient(base_url=base_url)
    with pytest.raises(BinanceMissingEndpointExceptions) as e_info:
        client.request('random')


