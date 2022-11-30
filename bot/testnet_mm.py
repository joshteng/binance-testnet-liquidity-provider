from time import sleep
from lib.binance import BinanceWebsocketClient, BinanceClient
from bot.testnet_mm_state import TestnetMMState
from bot.exceptions import *

class TestnetMM:
    @staticmethod
    def _record_last_price(price:str):
        TestnetMMState.PRODUCTION_LAST_PRICE = price

    def __init__(
        self,
        base_asset="BTC",
        quote_asset="BUSD",
        testnet_api_key="",
        testnet_api_secret="",
        testnet_rest_base_url="https://testnet.binance.vision",
        production_ws_base_url="wss://stream.binance.com:9443/ws"
    ):
        self.base_asset = base_asset.upper()
        self.quote_asset = quote_asset.upper()
        self.symbol = self.base_asset + self.quote_asset
        self.rest_client = BinanceClient(
            testnet_rest_base_url,
            testnet_api_key,
            testnet_api_secret
        )
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

        self.bws.disconnect()

    def _get_balances(self, base_asset="BTC", quote_asset="BUSD") -> tuple[str, str]:
        res = self.rest_client.request("getAccount")

        balances = {}
        for balance in res['balances']:
            balances[balance['asset']] = balance['free']

        return (balances[base_asset], balances[quote_asset])

    def _trade(self) -> bool:
        # don't trade if price is not updated
        if float(TestnetMMState.PRODUCTION_LAST_PRICE) <= 0:
            return False

        base_asset_qty, quote_asset_qty = self._get_balances(base_asset=self.base_asset, quote_asset=self.quote_asset)

        if float(base_asset_qty) <= 0 and float(quote_asset_qty) <= 0:
            raise TestnetMMInsufficientFundsException(f"Insufficient {self.base_asset} and {self.quote_asset}")


    # Price Stream related Methods
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
            self._trade()

    def _close_handler(self):
        print("Handling close WS conn")
