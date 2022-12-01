from bot.logger import logger

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
        logger.update('open_orders', TestnetMMState.OPEN_ORDERS)

    @staticmethod
    def update_order_state(payload):
        # https://binance-docs.github.io/apidocs/spot/en/#payload-order-update
        action = {
            'BUY': 'bids',
            'SELL': 'asks'
        }

        if payload["x"] == "TRADE":
            for order in TestnetMMState.OPEN_ORDERS[action[payload['S']]]:
                if order['orderId'] == payload["i"]:
                    order['executedQty'] = payload["z"]
                    order['status'] = payload["X"]

            logger.update('info', f'Order {payload["i"]} updates: executedQty {payload["z"]}; status: {payload["X"]}')
            logger.update('open_orders', TestnetMMState.OPEN_ORDERS)
