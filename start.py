from lib.binance.rest.client import BinanceClient

def main():
    client = BinanceClient(base_url="https://testnet.binance.vision")
    print(client.request('getExchangeInfo'))

if __name__ == '__main__':
    main()