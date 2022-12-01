from config import Config
from bot.testnet_mm import TestnetMM


def main():
    TestnetMM(
        Config.BASE_ASSET,
        Config.QUOTE_ASSET,
        Config.API_KEY,
        Config.API_SECRET,
        distance_from_mid_price=Config.DISTANCE_FROM_MID_PRICE
    ).run()


if __name__ == '__main__':
    main()
