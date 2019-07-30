from __future__ import print_function

from abc import ABCMeta, abstractmethod


class DataHandler(metaclass=ABCMeta):
    """
    DataHandler is an abstract base class providing an interface for all subsequent (inherited) data handlers (both live and historic).
    The goal of a (derived) DataHandler object is to output a generated set of bars (OHLCV) for each symbol requested.
    This will replicate how a live strategy would function as currentmarket data would be sent "down the pipe"
    Thus a historic and live system will be treated identically by the rest of the backtesting suite.
    """
    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        Return the latest bar updated.
        """
        raise NotImplementedError('Should implement get_latest_bar()')

    @abstractmethod
    def get_latest_bars(self, symbol, N=1, M=None):
        """
        Return the latest N bars updated.
        """
        raise NotImplementedError('Should implement get_n_bars()')

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        """
        Returns a Python datetime object for the last bar.
        """
        raise NotImplementedError('Should implement get_latest_bar_datetime()')

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        """
        Returns one of the Open, High, Low, Close or Volume from the last bar.
        """
        raise NotImplementedError('Should implement get_latest_bar_value()')

    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1, M=None):
        """
        Returns the last N bar values from the latest_symbol list, or N-k if less available.
        """
        raise NotImplementedError('Should implement get_n_bars_values()')

    @abstractmethod
    def update_bars(self):
        """
        Pushes the latest bars to the bars_queue for each symbol
        in a tuple OHLCV format: (datetime, open, high, low,
        close, volume).
        """
        raise NotImplementedError("Should implement update_bars()")

    @abstractmethod
    def current_price(self):
        """
        Returns the current close price in Backtesting and current ask in live
        """
        raise NotImplementedError("Should implement current_price()")
