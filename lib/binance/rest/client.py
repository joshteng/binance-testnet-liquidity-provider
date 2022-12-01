import hmac
import hashlib
import requests
from lib.binance.rest.exceptions import BinanceMissingEndpointException, BinanceAPICredentialsException, BinanceMissingParameterException, BinanceRestException
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
        "postOrder": {
            "http_method": "POST",
            "path": "/api/v3/order",
            "is_signed": True,
            "required_params": ["symbol", "side", "type", "timeInForce", "quantity", "price"]
        },
        "deleteOpenOrders": {
            "http_method": "DELETE",
            "path": "/api/v3/openOrders",
            "is_signed": True,
            "required_params": ["symbol"]
        },
        "postUserDataStream": {
            "http_method": "POST",
            "path": "/api/v3/userDataStream",
            "is_signed": False
        },
        "putUserDataStream": {
            "http_method": "PUT",
            "path": "/api/v3/userDataStream",
            "is_signed": False,
            "required_params": ["listenKey"]
        }
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
        headers = {
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

    def _verify_endpoint(self, endpoint):
        if endpoint not in self.endpoints:
            raise BinanceMissingEndpointException(f"Endpoint {endpoint} not found")

    def _verify_api_credentials(self, endpoint):
        if self.endpoints[endpoint]["is_signed"] and (len(self.key) == 0 or len(self.secret) == 0):
            raise BinanceAPICredentialsException("Missing API key or secret")

    def _verify_parameters(self, endpoint, params):
        if "required_params" not in self.endpoints[endpoint]:
            return

        for key in self.endpoints[endpoint]['required_params']:
            if key not in params:
                raise BinanceMissingParameterException(key)

    def _prepare_querystring(self, endpoint, params):
        if self.endpoints[endpoint]["is_signed"]:
            return self._prepare_params(self._sign_request(params))
        elif params:
            return self._prepare_params(params)

        return ""

    def _check_response(self, endpoint, res):
        if res.status_code < 200 or res.status_code > 299:
            raise BinanceRestException(
                reason=res.reason,
                status_code=res.status_code,
                http_method=self.endpoints[endpoint]["http_method"],
                path=self.endpoints[endpoint]["path"],
                details=res.json()
            )

    def request(self, endpoint, params=None):
        self._verify_endpoint(endpoint)
        self._verify_api_credentials(endpoint)
        self._verify_parameters(endpoint, params)

        params = params if params else {}

        querystring = self._prepare_querystring(endpoint, params)

        res = self._dispatch_request(
            self.endpoints[endpoint]["http_method"],
            self.endpoints[endpoint]["path"],
            querystring
        )

        self._check_response(endpoint, res)

        return res.json()
