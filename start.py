import time
from config import Config
from lib.binance import BinanceClient, BinanceWebsocketClient

def main():
    # client = BinanceClient(base_url="https://testnet.binance.vision", key=Config.API_KEY, secret=Config.API_SECRET)
    # print(client.request('getExchangeInfo'))
    # print(client.request('getAccount'))
    # print(client.request("postOrder", {
    #         "symbol": Config.SYMBOL,
    #         "side": "SELL",
    #         "type": "LIMIT",
    #         "timeInForce": "GTC",
    #         "quantity": "0.1",
    #         "price": "15000"
    #     }))

    def message_handler(msg):
        print(msg)

    def close_handler():
        print("Handling close WS conn")

    BinanceWebsocketClient(
        name="production",
        ws_base_url="wss://testnet.binance.vision/ws",
        topics=[BinanceWebsocketClient.agg_trade(Config.SYMBOL)],
        message_handler=message_handler,
        close_handler=close_handler).connect()

    while True:
        time.sleep(5)

if __name__ == '__main__':
    main()
