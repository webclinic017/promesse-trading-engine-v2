from data_handler.data_handler import DataHandler

import numpy as np
import pandas as pd

from event import MarketEvent
from datetime import datetime

from pathlib import Path


class CSVDataHandler(DataHandler):
    def __init__(self, events, symbol_list, timeframe):
        self.events = events  # Event queue

        self.csv_dir = 'exchange_data'
        self.symbol_list = ['-'.join(symbol.split('/'))
                            for symbol in symbol_list]
        self.timeframe = timeframe

        self.symbol_data = dict()
        self.latest_symbol_data = dict()

        self.continue_backtest = True

        self._load_symbol_data()

    def __repr__(self):
        return f'<CSVDataHandler>'

    def __str__(self):
        return f'CSVDataHandler with {self.timeframe} timeframe'

    def _load_symbol_data(self):
        '''
        It imports historical data from a set of CSV files then prepare them for the backtesting.
        It sets self.symbol_data with all data and init self_latest_symbol_data with empty data.
        '''
        csv_files_path = f'{Path().absolute()}/{self.csv_dir}'
        columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        combined_symbol_index = None

        for symbol in self.symbol_list:
            symbol_csv_path = f'{csv_files_path}/{symbol}_{self.timeframe}.csv'
            self.symbol_data[symbol] = pd.read_csv(
                symbol_csv_path, header=None, index_col=0, names=columns)

            self.symbol_data[symbol].index = pd.to_datetime(
                self.symbol_data[symbol].index, unit='ms')
            self.symbol_data[symbol] = self.symbol_data[symbol].drop_duplicates(
            )
            self.symbol_data[symbol] = self.symbol_data[symbol].sort_index()

            if combined_symbol_index is None:
                combined_symbol_index = self.symbol_data[symbol].index
            else:
                combined_symbol_index = combined_symbol_index.union(
                    self.symbol_data[symbol].index)

            # Init list that will contain latest ohlcv data for each symbol
            self.latest_symbol_data[symbol] = list()

        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol].reindex(
                index=combined_symbol_index, method='pad', fill_value=0).itertuples(name='OHLCV')

    def _get_new_bar(self, symbol):
        for bar in self.symbol_data[symbol]:
            yield bar

    def update_bars(self):
        """
        It feeds the backtest with latest data in each iteration and trigger Market event.
        It sets this data in self.latest_symbol_data.
        If there is no data to feed the backtest, it raises an exception and the backtest stops.
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)

        # Fire Market Event that will be handled by the Strategy and Portfolio
        self.events.put(MarketEvent())

    def get_latest_bar(self, symbol):
        """
        It returns the latest bar data of a given symbol as namedtuple
        e.g: OHLCV(Index=Timestamp('2017-08-08 11:00:00'), open=0.080292,
                   high=0.081039, low=0.079854, close=0.080282, volume=610.868)
        """
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
            return self.latest_symbol_data[symbol][-1].Index
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bar_value(self, symbol, value_type):
        """
        It returns the latest bar value (open, high, low, close or volume) of a given symbol
        """
        try:
            if value_type == 'datetime':
                return getattr(self.latest_symbol_data[symbol][-1], 'Index')
            return getattr(self.latest_symbol_data[symbol][-1], value_type)
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise

    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        It returns a numpy array of the latest bars values (open, high, low, close or volume) of a given symbol
        e.g: array([ 89, 88.2, 86.4, ...])
        """
        try:
            bars = self.latest_symbol_data[symbol][-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            if value_type == 'datetime':
                return np.array([getattr(bar, 'Index') for bar in bars])
            return np.array([getattr(bar, value_type) for bar in bars])

    def current_price(self, symbol):
        """
        It retuns latest close price
        """
        return self.get_latest_bar_value(symbol, 'close')
