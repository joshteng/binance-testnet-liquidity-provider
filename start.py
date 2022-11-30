from config import Config
from bot.testnet_mm import TestnetMM

def main():
    TestnetMM(Config.SYMBOL).run()

if __name__ == '__main__':
    main()
