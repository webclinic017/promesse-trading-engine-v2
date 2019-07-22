from data_handler.data_handler import DataHandler

import numpy as np
import pandas as pd

from datetime import datetime

import ccxt
from event import MarketEvent


class LiveDataHandler(DataHandler):
    def __init__(self, events, exchange_id, exchange_api_key=None, exchange_secret_key=None, symbol_list, timeframe):
        self.events = events

        self.exchange_id = exchange_id
        self.exchange_api_key = exchange_api_key
        self.exchange_secret_key = exchange_secret_key
        self.exchange = self._create_exchange()

        self.timeframe = timeframe

        self.symbol_list = symbol_list
        self.latest_symbol_data = dict()

        self._load_symbol_data()

    def __repr__(self):
        return f'<LiveDataHandler>'

    def __str__(self):
        return f'DataDataHandler from {self.exchange_id} with {self.timeframe} timeframe'

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
                symbol, timeframe=self.timeframe)

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
            return datetime.fromtimestamp(self.latest_symbol_data[symbol][-1][0]/1000.0)
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bar_value(self, symbol, value_type):
        """
        It returns the latest bar value (open, high, low, close or volume) of a given symbol
        """
        bars_map = {
            'open': 1,
            'high': 2,
            'low': 3,
            'close': 4,
            'volume': 5
        }
        try:
            return self.latest_symbol_data[symbol][-1][bars_map[value_type]]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        It returns a numpy array of the latest bars values (open, high, low, close or volume) of a given symbol
        e.g: array([ 89, 88.2, 86.4, ...])
        """
        bars_map = {
            'open': 1,
            'high': 2,
            'low': 3,
            'close': 4,
            'volume': 5
        }
        try:
            bars = self.latest_symbol_data[symbol][-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([bar[bars_map[value_type]] for bar in bars])
