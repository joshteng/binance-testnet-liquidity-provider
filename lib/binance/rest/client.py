import hmac
import hashlib
import requests
from lib.binance.rest.exceptions import BinanceAPICredentialsException, BinanceRestExceptions, BinanceMissingEndpointExceptions
from lib.binance.rest.util import encoded_string, get_timestamp, clean_none_value


class BinanceClient:
    endpoints = {
        "getExchangeInfo": {
            "http_method": "GET",
            "path": "/api/v3/exchangeInfo",
            "is_signed": False
        },
        "getAccount": {
            "http_method": "GET",
            "path": "/api/v3/account",
            "is_signed": True
        },
    }

    def __init__(self, base_url="https://api.binance.com", key="", secret=""):
        self.base_url = base_url
        self.key = key
        self.secret = secret

    def _sign_request(self, payload=None):
        if payload is None:
            payload = {}
        payload["timestamp"] = get_timestamp()
        query_string = self._prepare_params(payload)
        signature = self._get_sign(query_string)
        payload["signature"] = signature
        return payload

    def _prepare_params(self, params):
        return encoded_string(clean_none_value(params))

    def _get_sign(self, data):
        m = hmac.new(self.secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256)
        return m.hexdigest()

    def _dispatch_request(self, http_method, url_path, url_querystring):
        headers= {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": self.key,
        }

        url = self.base_url + url_path

        if url_querystring:
            url += "?" + url_querystring

        return getattr(requests, http_method.lower())(
            url=url,
            headers=headers
        )

    def request(self, endpoint, params=None):
        if not endpoint in self.endpoints:
            raise BinanceMissingEndpointExceptions(f"Endpoint {endpoint} not found")

        if self.endpoints[endpoint]["is_signed"] and (len(self.key) == 0 or len(self.secret) == 0):
            raise BinanceAPICredentialsException("Missing API key or secret")

        if not params:
            params = {}

        querystring = ""

        if self.endpoints[endpoint]["is_signed"]:
            querystring += self._prepare_params(self._sign_request(params))

        res = self._dispatch_request(self.endpoints[endpoint]["http_method"], self.endpoints[endpoint]["path"], querystring)

        if not (res.status_code > 199 and res.status_code < 300):
            raise BinanceRestExceptions(
                reason=res.reason,
                status_code=res.status_code,
                http_method=self.endpoints[endpoint]["http_method"],
                path=self.endpoints[endpoint]["path"],
                details=res.json()
            )

        return res.json()
