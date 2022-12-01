import logging
import os
import sys
from datetime import datetime

class BotLogger(object):
    def __init__(self, log_file, log_level):
        self._create_logger(log_file, log_level)
        self.log_history = {
            'info': [],
            'debug': [],
            'past_orders': [],
            'open_orders': [],
            'production_last_price': 0
        }
        self.last_refreshed = datetime.now()

    def _create_logger(self, log_file,  log_level):
        log_format = "%(asctime)s | %(levelname)s | %(message)s"

        self.logger = logging.getLogger(log_file)
        ch = logging.StreamHandler(sys.stdout)
        # formatter = logging.Formatter(
        #     "%(asctime)s - %(name)s - %(message)s", "%m-%d %H:%M:%S")
        # ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        if log_level == "INFO":
            self.logger.setLevel(logging.INFO)
        elif log_level == "ERROR":
            self.logger.setLevel(logging.ERROR)
        elif log_level == "DEBUG":
            self.logger.setLevel(logging.DEBUG)
        return self.logger

    def construct_output(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.logger.info('LAST PRICE')
        self.logger.info(self.log_history['production_last_price'])
        self.logger.info('')

        self.logger.info('-' * 50)
        self.logger.info('OPEN ORDERS')
        self.logger.info("bids:")
        for bid in self.log_history['open_orders']['bids']:
            self.logger.info(bid)
        self.logger.info("asks:")
        for ask in self.log_history['open_orders']['asks']:
            self.logger.info(ask)
        self.logger.info('')

        self.logger.info('-' * 50)
        self.logger.info('SESSION LOG MESSAGES')
        for msg in self.log_history['info']:
            self.logger.info(msg)

        for msg in self.log_history['debug']:
            self.logger.debug(msg)
        self.logger.info('')


        self.logger.info('-' * 50)
        self.logger.info('SESSION PAST ORDERS')
        for order in self.log_history['past_orders']:
            self.logger.info(order)

        self.last_refreshed = datetime.now()

    def update(self, type, msg):
        if type == 'production_last_price':
            self.log_history['production_last_price'] = msg
        elif type == 'open_orders':
            self.log_history['open_orders'] = msg
        elif type == 'info' or type == 'debug':
            self.log_history[type].append(f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')} - {msg}")
            self.log_history[type] = self.log_history[type][-10:]
        else:
            self.log_history[type].append(msg)
            self.log_history[type] = self.log_history[type][-10:]

        if (datetime.now() - self.last_refreshed).seconds > 1:
            self.construct_output()

logger = BotLogger('TestnetMM', "INFO")
