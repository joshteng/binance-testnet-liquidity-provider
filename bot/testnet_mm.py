import math
from time import sleep
from decimal import Decimal
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
        production_ws_base_url="wss://stream.binance.com:9443/ws",
        distance_from_mid_price="0.005"
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
        self.distance_from_mid_price = distance_from_mid_price

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

    def _place_bid(self, qty:str, price:str):
        res = self.rest_client.request("postOrder", {
            "symbol": self.symbol,
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": qty,
            "price": price
        })

        if not res['orderId']:
            raise TestnetMMOrderFailedException

        order_details = {
            'orderId': res['orderId'],
            'clientOrderId': res['clientOrderId'],
            'transactTime': res['transactTime'],
            'status': res['status'],
            'symbol': res['symbol'],
            'side': res['side'],
            'type': res['type'],
            'price': res['price'],
            'origQty': res['origQty'],
            'executedQty': res['executedQty'],
        }

        TestnetMMState.PAST_ORDERS.append(order_details)
        TestnetMMState.OPEN_ORDERS['bids'].append(order_details)

    def _place_ask(self, qty:str, price:str):
        res = self.rest_client.request("postOrder", {
            "symbol": self.symbol,
            "side": "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": qty,
            "price": price
        })

        if not res['orderId']:
            raise TestnetMMOrderFailedException

        order_details = {
            'orderId': res['orderId'],
            'clientOrderId': res['clientOrderId'],
            'transactTime': res['transactTime'],
            'status': res['status'],
            'symbol': res['symbol'],
            'side': res['side'],
            'type': res['type'],
            'price': res['price'],
            'origQty': res['origQty'],
            'executedQty': res['executedQty'],
        }

        TestnetMMState.PAST_ORDERS.append(order_details)
        TestnetMMState.OPEN_ORDERS['asks'].append(order_details)


    def _truncate_quantity(self, quantity:Decimal) -> str:
        """
        Fix number of decimal places as per Binance filters
        To do: get filters from binance rather than hard coding
        """
        factor = 10 ** 6
        return '{:f}'.format(math.floor(quantity * factor) / factor)

    def _truncate_price(self, price:Decimal) -> str:
        """
        Fix number of decimal places as per Binance filters
        To do: get filters from binance rather than hard coding
        """
        factor = 10 ** 2
        return '{:f}'.format(math.floor(price * factor) / factor)

    def _buy_base_asset(self, quote_asset_available:str):
        """
        Buy base asset with quote asset
        Warning: Hardcoded a ratio of 1/2 base and 1/2 quote asset
        For a symbol like BTCBUSD, BTC is the base asset and BUSD is the quote asset
        """
        bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') - Decimal(self.distance_from_mid_price))
        bid_quantity = (Decimal(quote_asset_available) / Decimal('2')) / bid_price
        self._place_bid(self._truncate_quantity(bid_quantity), self._truncate_price(bid_price))

    def _buy_quote_asset(self, base_asset_available):
        """
        Sells base asset for quote asset
        Warning: Hardcoded a ratio of 1/2 base and 1/2 quote asset
        For a symbol like BTCBUSD, BTC is the base asset and BUSD is the quote asset
        """
        ask_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') + Decimal(self.distance_from_mid_price))
        ask_quantity = Decimal(base_asset_available) / Decimal('2')
        self._place_ask(self._truncate_quantity(ask_quantity), self._truncate_price(ask_price))

    def _provide_liquidity(self, base_asset_available, quote_asset_available):
        bid_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') - Decimal(self.distance_from_mid_price))
        ask_price = Decimal(TestnetMMState.PRODUCTION_LAST_PRICE) * (Decimal('1') + Decimal(self.distance_from_mid_price))

        """
        If base-quote asset ratio isn't 50:50, order_qty should be minimum of what is available to sell or buy to have an order size of equal base value
        """
        max_quantity_to_sell = Decimal(base_asset_available)
        max_quantity_to_buy = Decimal(quote_asset_available) / bid_price
        order_qty = min(max_quantity_to_sell, max_quantity_to_buy)

        truncated_order_qty = self._truncate_quantity(order_qty)
        self._place_bid(truncated_order_qty, self._truncate_price(bid_price))
        self._place_ask(truncated_order_qty, self._truncate_price(ask_price))


    def _trade(self) -> bool:
        # don't trade if price is not updated
        if float(TestnetMMState.PRODUCTION_LAST_PRICE) <= 0:
            return False

        base_asset_qty, quote_asset_qty = self._get_balances(base_asset=self.base_asset, quote_asset=self.quote_asset)

        if float(base_asset_qty) <= 0 and float(quote_asset_qty) <= 0:
            raise TestnetMMInsufficientFundsException(f"Insufficient {self.base_asset} and {self.quote_asset}")

        elif float(quote_asset_qty) > 0 and float(base_asset_qty) <= 0:
            self._buy_base_asset(quote_asset_available=quote_asset_qty)

        elif float(base_asset_qty) > 0 and float(quote_asset_qty) <= 0:
            self._buy_quote_asset(base_asset_available=base_asset_qty)

        else:
            self._provide_liquidity(base_asset_available=base_asset_qty, quote_asset_available=quote_asset_qty)


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
            """
            From aggTrade subscription
            https://binance-docs.github.io/apidocs/spot/en/#aggregate-trade-streams
            """
            self._record_last_price(msg['p'])
            self._trade()

    def _close_handler(self):
        print("Handling close WS conn")
