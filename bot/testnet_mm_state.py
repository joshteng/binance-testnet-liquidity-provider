class TestnetMMState:
    PRODUCTION_LAST_PRICE = '0'
    PAST_ORDERS = []
    OPEN_ORDERS = {
        'bids': [],
        'asks': []
    }

    @staticmethod
    def clear_open_orders():
        TestnetMMState.OPEN_ORDERS = {
            'bids': [],
            'asks': []
        }
