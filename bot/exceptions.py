class TestnetMMInsufficientFundsException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class TestnetMMOrderFailedException(Exception):
    pass
