import math
import traceback
from time import sleep
from decimal import Decimal
from datetime import datetime
from lib.binance import BinanceWebsocketClient, BinanceClient
from lib.binance.rest.exceptions import BinanceRestException
from bot.testnet_mm_state import TestnetMMState
from bot.exceptions import *
from bot.logger import logger


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
        testnet_ws_base_url="wss://testnet.binance.vision/ws",
        production_ws_base_url="wss://stream.binance.com:9443/ws",
        distance_from_mid_price="0.01"
    ):
        self.base_asset = base_asset.upper()
        self.quote_asset = quote_asset.upper()
        self.symbol = self.base_asset + self.quote_asset
        self.rest_client = BinanceClient(
            testnet_rest_base_url,
            testnet_api_key,
            testnet_api_secret
        )
        self.testnet_ws_base_url = testnet_ws_base_url
        self.production_ws_base_url = production_ws_base_url
        self.distance_from_mid_price = distance_from_mid_price
        self.base_asset_precision = {}
        self.price_precision = {}
        self.min_notional = {}
        logger.update('open_orders', TestnetMMState.OPEN_ORDERS)

    def run(self):
        self._get_asset_filters()
        self._cancel_open_orders()
        self.keep_alive = True
        self.bws = self._connect_to_production_trade_stream()
        self.last_keep_listen_key_alive_at = datetime.now()
        self.uws = self._connect_to_testnet_user_stream()
        self._keep_alive()

    def terminate(self):
        self._cancel_open_orders()
        self.keep_alive = False

    def _keep_alive(self):
        while self.keep_alive:
            if (datetime.now() - self.last_keep_listen_key_alive_at).seconds > 60 * 50:
                self._keep_listen_key_alive()

            sleep(1)

        self.bws.disconnect()
        self.uws.disconnect()

    def _get_asset_filters(self):
        exchange_info = self.rest_client.request("getExchangeInfo")

        for asset in exchange_info["symbols"]:
            for f in asset['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    self.base_asset_precision[asset["symbol"]] = f['stepSize'].find('1') - 1

                if f['filterType'] == 'PRICE_FILTER':
                    self.price_precision[asset["symbol"]] = f['tickSize'].find('1') - 1

                if f['filterType'] == 'MIN_NOTIONAL':
                    self.min_notional[asset["symbol"]] = f['minNotional']

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
        logger.update('past_orders', res)
        logger.update('open_orders', TestnetMMState.OPEN_ORDERS)
        logger.update('info', f"Placed bid order for {res['symbol']} {res['origQty']} at {res['price']}")

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
        logger.update('past_orders', res)
        logger.update('open_orders', TestnetMMState.OPEN_ORDERS)
        logger.update('info', f"Placed ask order for {res['symbol']} {res['origQty']} at {res['price']}")

    def _truncate_quantity(self, quantity:Decimal) -> str:
        """
        Fix number of decimal places as per Binance filters
        """
        factor = 10 ** self.base_asset_precision[self.symbol]
        return '{:f}'.format(math.floor(quantity * factor) / factor)

    def _truncate_price(self, price:Decimal) -> str:
        """
        Fix number of decimal places as per Binance filters
        """
        factor = 10 ** self.price_precision[self.symbol]
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
        """
        Places 2 limit bid and ask orders of equivalent size in testnet, at prices `distance_from_mid_price` away from the last price on production
        """
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

    def _cancel_open_orders(self):
        try:
            self.rest_client.request("deleteOpenOrders", {
                "symbol": self.symbol,
            })
            TestnetMMState.clear_open_orders()
            logger.update('info', "Cancelled open orders")

        except BinanceRestException as err:
            # error -2011 indicates cancel rejected. we shall ignore this since it is possible for us to not have open orders
            # https://github.com/binance/binance-spot-api-docs/blob/master/errors.md#-2011-cancel_rejected
            if err.code == -2011 and err.details['msg'] == 'Unknown order sent.':
                return

            raise err

    def _terminate_if_error(func):
        def execute(self):
            try:
                return func(self)
            except Exception as err:
                self.terminate()
                logger.update('debug', traceback.format_exc())
                raise err

        return execute

    def _prevent_multiple_trade_at_once(func):
        def execute(self):
            self.in_process = self.in_process if hasattr(self, "in_process") else False
            if self.in_process:
                return

            self.in_process = True
            try:
                return func(self)
            except Exception as err:
                raise err
            finally:
                self.in_process = False

        return execute

    @_terminate_if_error
    @_prevent_multiple_trade_at_once
    def _trade(self) -> bool:
        # don't trade if price is not updated
        if float(TestnetMMState.PRODUCTION_LAST_PRICE) <= 0:
            return False

        if self._has_no_open_orders() or\
            self._has_open_orders_and_production_price_reached():
            self._place_trade()

    def _has_no_open_orders(self):
        return len(TestnetMMState.OPEN_ORDERS['bids']) == 0 and len(TestnetMMState.OPEN_ORDERS['asks']) == 0

    def _has_open_orders_and_production_price_reached(self):
        return (len(TestnetMMState.OPEN_ORDERS['bids']) > 0 and float(TestnetMMState.PRODUCTION_LAST_PRICE) <= float(TestnetMMState.OPEN_ORDERS['bids'][0]['price'])) or (len(TestnetMMState.OPEN_ORDERS['asks']) > 0 and float(TestnetMMState.PRODUCTION_LAST_PRICE) >= float(TestnetMMState.OPEN_ORDERS['asks'][0]['price']))

    def _has_sufficient_base_asset(self, base_asset_qty):
        return float(Decimal(base_asset_qty) * Decimal(TestnetMMState.PRODUCTION_LAST_PRICE)) > float(self.min_notional[self.symbol])

    def _has_sufficient_quote_asset(self, quote_asset_qty):
        return float(quote_asset_qty) > float(self.min_notional[self.symbol])

    def _place_trade(self):
        base_asset_qty, quote_asset_qty = self._get_balances(base_asset=self.base_asset, quote_asset=self.quote_asset)

        if not self._has_sufficient_base_asset(base_asset_qty) and not self._has_sufficient_quote_asset(quote_asset_qty):
            raise TestnetMMInsufficientFundsException(f"Insufficient {self.base_asset} and {self.quote_asset}")

        self._cancel_open_orders()

        if self._has_sufficient_quote_asset(quote_asset_qty) and not self._has_sufficient_base_asset(base_asset_qty):
            logger.update('info', 'No base asset, buying base asset')
            self._buy_base_asset(quote_asset_available=quote_asset_qty)

        elif self._has_sufficient_base_asset(base_asset_qty) and not self._has_sufficient_quote_asset(quote_asset_qty):
            logger.update('info', 'No quote asset, selling base asset')
            self._buy_quote_asset(base_asset_available=base_asset_qty)

        else:
            self._provide_liquidity(base_asset_available=base_asset_qty, quote_asset_available=quote_asset_qty)

    # Stream related Methods
    def _get_listen_key(self):
        res = self.rest_client.request("postUserDataStream")
        self.listen_key = res["listenKey"]

    def _keep_listen_key_alive(self):
        self.last_keep_listen_key_alive_at = datetime.now()
        self.rest_client.request("putUserDataStream", { "listenKey": self.listen_key })

    def _connect_to_testnet_user_stream(self):
        self._get_listen_key()

        bws = BinanceWebsocketClient(
            name="testnet",
            ws_base_url=f"{self.testnet_ws_base_url}/{self.listen_key}",
            topics=[],
            message_handler=self._message_handler,
            close_handler=self._close_handler)
        bws.connect()
        return bws

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
            logger.update('production_last_price', msg['p'])
            self._trade()
        elif 'e' in msg and msg['e'] == 'executionReport':
            logger.update('debug', msg)
            TestnetMMState.update_order_state(msg)
        else:
            logger.update('debug', f"Unhandled ws message: {msg}")

    def _close_handler(self):
        self.terminate()
        logger.info("Handling close WS conn")
