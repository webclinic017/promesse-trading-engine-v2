from data_handler.data_handler import DataHandler

import numpy as np
import pandas as pd

from datetime import datetime
import time

import ccxt
from ccxt.base.errors import RequestTimeout
from event import MarketEvent

import queue

from helpers import load_config


class LiveDataHandler(DataHandler):
    def __init__(self, events, symbol_list, timeframe):
        self.events = events
        self.config = load_config()

        self.exchange_id = self.config['exchange']['id']
        self.exchange_api_key = self.config['exchange']['key']
        self.exchange_secret_key = self.config['exchange']['secret']
        self.exchange = self._create_exchange()

        self.timeframe = timeframe
        self.symbol_list = symbol_list
        self.latest_symbol_data = dict()

        self.continue_backtest = True

        self._load_symbol_data()

    def __repr__(self):
        return f'<LiveDataHandler>'

    def __str__(self):
        return f'LiveDataHandler from {self.exchange_id} with {self.timeframe} timeframe'

    def _create_exchange(self):
        exchange_class = getattr(ccxt, self.exchange_id)
        exchange = exchange_class({
            'apiKey': self.exchange_api_key,
            'secret': self.exchange_secret_key,
            'timeout': 30000,
            'enableRateLimit': True,
        })
        return exchange

    def _load_symbol_data(self):
        self.exchange.load_markets(True)

        for symbol in self.symbol_list:
            self.latest_symbol_data[symbol] = self.exchange.fetch_ohlcv(
                symbol, timeframe=self.timeframe, limit=200)
            # Wait a sec before sending a request
            time.sleep(1)

    def update_bars(self):
        self._load_symbol_data()
        self.events.put(MarketEvent())

    def get_latest_bar(self, symbol):
        try:
            return self.latest_symbol_data[symbol][-1]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bars(self, symbol, N=1):
        """
        It returns the latest bars data of a given symbol as a np array
        """
        try:
            return np.array(self.latest_symbol_data[symbol][-N:])
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bar_datetime(self, symbol):
        """
        It returns the latest bar timestamp object of a given symbol
        """
        try:
            return pd.to_datetime(self.latest_symbol_data[symbol][-1][0], unit='ms')
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bar_value(self, symbol, value_type):
        """
        It returns the latest bar value (open, high, low, close or volume) of a given symbol
        """
        try:
            bars_map = {
                'datetime': 0,
                'open': 1,
                'high': 2,
                'low': 3,
                'close': 4,
                'volume': 5
            }
            if value_type == 'datetime':
                return pd.to_datetime(self.latest_symbol_data[symbol][-1][bars_map[value_type]], unit='ms')
            return self.latest_symbol_data[symbol][-1][bars_map[value_type]]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        It returns a numpy array of the latest bars values (open, high, low, close or volume) of a given symbol
        e.g: array([ 89, 88.2, 86.4, ...])
        """
        try:
            bars_map = {
                'datetime': 0,
                'open': 1,
                'high': 2,
                'low': 3,
                'close': 4,
                'volume': 5
            }
            bars = self.latest_symbol_data[symbol][-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            if value_type == 'datetime':
                return np.array([pd.to_datetime(bar[bars_map[value_type]], unit='ms')
                                 for bar in bars])
            return np.array([bar[bars_map[value_type]] for bar in bars])

    def current_price(self, symbol, side='asks'):
        """
        It retuns current ask price
        """
        counter = 2
        try:
            return self.exchange.fetch_order_book(symbol)[side][0][0]
        except RequestTimeout:
            if counter != 0:
                self.current_price(symbol)
                counter -= 1
            else:
                return 0

    def get_latest_bars_df(self, symbol, N=1):
        """
        It returns the latest bars data of a given symbol as a np array
        """
        try:
            bars = pd.DataFrame(self.latest_symbol_data[symbol][-N:])
            bars.set_index('Index', inplace=True)
            return bars
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bars_values_df(self, symbol, value_type, N=1):
        """
        It returns the latest bars data of a given symbol as a np array
        """
        try:
            bars = pd.DataFrame(self.latest_symbol_data[symbol][-N:])
            bars.set_index('Index', inplace=True)
            bars = bars[value_type]
            return bars
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
