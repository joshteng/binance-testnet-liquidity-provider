# A Sample Market Making Bot for Binance Spot (TESTNET)
[![CircleCI](https://dl.circleci.com/status-badge/img/gh/joshteng/binance-testnet-liquidity-provider/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/joshteng/binance-testnet-liquidity-provider/tree/main)

This is an example of providing liquidity programmatically on Binance (Spot). It's the most basic form of market making, placing 1 limit order on each side of the order book - learn more about market making: https://www.youtube.com/watch?v=QqK6H1JPjv0

Orders are placed on Binance Testnet using last price from Binance production.

Sample output:

![output](/docs/assets/sample-output.png)

---

## Dependencies
1. ~ Python 3.9.10
2. See `requirements.txt` for external libraries used. For development and testing, you may choose to use Poetry to manage Python dependencies - `pyproject.toml` and `poetry.lock` is used to manage external dependencies.
3. Get Binance Testnet (Spot) API credentials from https://testnet.binance.vision/

---

## Run the Bot
### Directly
1. Have Python v3.9.10 installed
2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```
3. Obtain API credentials for testnet: https://testnet.binance.vision/
4. Start the bot:
    ```sh
    API_KEY=<YOUR_APY_KEY> API_SECRET=<YOUR_APY_SECRET> python start.py
    ```
### Using Docker
1. Have Docker engine installed
2. Then, at the root of this project:
    ```sh
    docker build -t binance-testnet-mm:latest .
    docker run -e API_KEY=<YOUR_API_KEY> -e API_SECRET=<YOUR_SECRET_KEY> --name=binance-testnet-mm-container binance-testnet-mm
    ```
\* Terminal output when using Docker is not optimized. For a better console viewing experience, run the bot directly rather than using Docker

---

## Settings
The following are parameters you could set in `config.py`
```py
class Config:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    BASE_ASSET = "BTC"
    QUOTE_ASSET = "BUSD"
    DISTANCE_FROM_MID_PRICE = "0.0003" # this is the rate from which limit prices from last price are determined e.g. last_price * (1 - DISTANCE_FROM_MID_PRICE) for bid orders and last_price * (1 + DISTANCE_FROM_MID_PRICE) for ask orders. a lower number will see more action!
```

---

## Development and Testing
1. Have Python v3.9.10 installed
2. Install dependencies:
    ```sh
    pip install -r requirements.dev.txt
    ```
    or use poetry
    ```sh
    poetry install
    ```
3. Run test:
    ```sh
    pytest -v
    ```
4. Start the bot:
    ```sh
    API_KEY=<YOUR_APY_KEY> API_SECRET=<YOUR_APY_SECRET> python start.py
    ```
5. Adding new dependencies
    ```sh
    poetry add <library>
    ```
    or
    ```sh
    poetry add --dev <library>
    ```
    finally
    ```
    poetry export -f requirements.txt --dev --output requirements.dev.txt
    poetry export -f requirements.txt --output requirements.txt
    ```
---

## Disclaimer
1. This repository is intended for educational purpose, integrating Binance's REST and WS API without a SDK
1. Use at your own risks! Risks of financial losses from the use of this bot can occur
1. Manage your API keys safely, even testnet! Never include it in your repository. Use and manage environment variables safely
1. If you're reconfiguring this bot to run against Binance production, it's crucial to never have withdrawal permission enabled on your API credentials if not necessary
