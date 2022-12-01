class BinanceMissingEndpointException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class BinanceMissingParameterException(Exception):
    def __init__(self, parameter):
        super().__init__(f"Missing '{parameter}' in request")


class BinanceAPICredentialsException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class BinanceRestException(Exception):
    def __init__(self, reason, status_code, http_method, path, details):
        self.reason = reason
        self.status_code = status_code
        self.http_method = http_method
        self.path = path
        self.details = details

        super().__init__(reason)

    @property
    def code(self):
        return self.details['code']

    def __str__(self) -> str:
        return f"{self.status_code} {self.reason} {self.http_method} {self.path} {self.details}"
