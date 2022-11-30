from time import sleep
from bot.testnet_mm_state import TestnetMMState
from lib.binance import BinanceWebsocketClient

class TestnetMM:
    @staticmethod
    def _record_last_price(price:str):
        TestnetMMState.PRODUCTION_LAST_PRICE = price

    def __init__(self, symbol, production_ws_base_url="wss://stream.binance.com:9443/ws"):
        self.symbol = symbol
        self.production_ws_base_url = production_ws_base_url

    def run(self):
        self.keep_alive = True
        self.bws = self._connect_to_production_trade_stream()
        self._keep_alive()

    def terminate(self):
        self.keep_alive = False

    def _keep_alive(self):
        while self.keep_alive:
            sleep(1)
            print(TestnetMMState.PRODUCTION_LAST_PRICE)

        self.bws.disconnect()

    def _connect_to_production_trade_stream(self):
        bws = BinanceWebsocketClient(
            name="production",
            ws_base_url=self.production_ws_base_url,
            topics=[BinanceWebsocketClient.agg_trade(self.symbol)],
            message_handler=self._message_handler,
            close_handler=self._close_handler)
        bws.connect()
        return bws

    def _message_handler(self, msg):
        if 'e' in msg and msg['e'] == 'aggTrade':
            self._record_last_price(msg['p'])

    def _close_handler(self):
        print("Handling close WS conn")
