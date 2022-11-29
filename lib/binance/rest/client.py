import hmac
import hashlib
import requests
from lib.binance.rest.exceptions import BinanceRestExceptions, BinanceMissingEndpointExceptions


class BinanceClient:
    endpoints = {
        "getExchangeInfo": {
            "http_method": "GET",
            "path": "/api/v3/exchangeInfo",
        },
    }

    def __init__(self, base_url="https://api.binance.com"):
        self.base_url = base_url

    def _dispatch_request(self, http_method, url_path):
        headers= {
            "Content-Type": "application/json;charset=utf-8",
        }

        url = self.base_url + url_path

        return getattr(requests, http_method.lower())(
            url=url,
            headers=headers
        )

    def request(self, endpoint):
        if not endpoint in self.endpoints:
            raise BinanceMissingEndpointExceptions(f"Endpoint {endpoint} not found")

        res = self._dispatch_request(self.endpoints[endpoint]["http_method"], self.endpoints[endpoint]["path"])

        if not (res.status_code > 199 and res.status_code < 300):
            raise BinanceRestExceptions(
                reason=res.reason,
                status_code=res.status_code,
                http_method=self.endpoints[endpoint]["http_method"],
                path=self.endpoints[endpoint]["path"],
                details=res.json()
            )

        return res.json()
