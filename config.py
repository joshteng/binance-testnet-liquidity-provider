import os


class Config:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    BASE_ASSET = "BTC"
    QUOTE_ASSET = "BUSD"

    # this is the rate from which limit prices from last price are determined e.g. last_price * (1 - DISTANCE_FROM_MID_PRICE) for bid orders and last_price * (1 + DISTANCE_FROM_MID_PRICE) for ask orders. a lower number will see more action!
    DISTANCE_FROM_MID_PRICE = "0.0003"
