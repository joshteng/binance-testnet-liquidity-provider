from config import Config
from bot.testnet_mm import TestnetMM

def main():
    TestnetMM(
        Config.BASE_ASSET,
        Config.QUOTE_ASSET,
        Config.API_KEY,
        Config.API_SECRET
    ).run()

if __name__ == '__main__':
    main()
