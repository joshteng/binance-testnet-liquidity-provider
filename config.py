import os

class Config:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    BASE_ASSET = "BTC"
    QUOTE_ASSET = "BUSD"
    DISTANCE_FROM_MID_PRICE = "0.0003"
