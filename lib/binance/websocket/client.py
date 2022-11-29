import websocket
import threading
import json


class BinanceWebsocketClient:
    def __init__(
        self,
        name="default",
        ws_base_url="wss://stream.binance.com:9443/ws",
        topics=[],
        message_handler=None,
        close_handler=None
    ):
        self.name = name
        self.url = ws_base_url
        self.topics = topics
        self.message_handler = message_handler
        self.close_handler = close_handler

    @staticmethod
    def agg_trade(symbol="btcusdt"):
        return f"{symbol.lower()}@aggTrade"

    @staticmethod
    def book_ticker(symbol="btcusdt"):
        return f"{symbol.lower()}@bookTicker"

    def connect(self):
        print(f"{self.name}: Attempting to connect")
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_close=self._on_close,
            on_open=self._on_open,
            on_error=self._on_error
        )

        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()

    def _send_command(self, cmd):
        self.ws.send(json.dumps(cmd))

    def _on_message(self, _, message):
        if self.message_handler:
            self.message_handler(json.loads(message))

    def _on_open(self, _):
        print(f"{self.name}: Connection opened")
        self._subscribe()

    def _on_close(self, _, close_status_code, close_msg):
        print(f"{self.name}: Connection closed {close_status_code}: {close_msg}")
        if self.close_handler:
            self.close_handler()

    def _on_error(self, _, error):
        print(f"{self.name}: Connection error {error}")
        self.ws.close()
        if self.close_handler:
            self.close_handler()

    def _subscribe(self):
        if len(self.topics) > 0:
            self._send_command({
                "method": "SUBSCRIBE",
                "params": self.topics,
                "id": 1
            })
