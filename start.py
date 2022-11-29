from config import Config
from lib.binance.rest.client import BinanceClient

def main():
    client = BinanceClient(base_url="https://testnet.binance.vision", key=Config.API_KEY, secret=Config.API_SECRET)
    print(client.request('getExchangeInfo'))
    print(client.request('getAccount'))
    print(client.request("postOrder", {
            "symbol": Config.SYMBOL,
            "side": "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": "0.1",
            "price": "15000"
        }))

if __name__ == '__main__':
    main()
