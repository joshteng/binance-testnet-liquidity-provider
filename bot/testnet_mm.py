from time import sleep
from lib.binance import BinanceWebsocketClient

class TestnetMM:
    def __init__(self, symbol):
        self.symbol = symbol

    def run(self):
        self._connect_to_production_trade_stream()
        self._trade()

    def _trade(self):
        while True:
            sleep(5)

    def _connect_to_production_trade_stream(self):
        BinanceWebsocketClient(
            name="production",
            ws_base_url="wss://testnet.binance.vision/ws",
            topics=[BinanceWebsocketClient.agg_trade(self.symbol)],
            message_handler=self._message_handler,
            close_handler=self._close_handler).connect()

    def _message_handler(self, msg):
        print(msg)

    def _close_handler(self):
        print("Handling close WS conn")
