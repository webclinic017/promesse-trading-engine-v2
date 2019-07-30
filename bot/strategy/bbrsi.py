from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np

from talib import RSI, EMA, BBANDS
import peakutils


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 150
        self.counter = 0

        self.rsi_window = 14
        self.ma_window = 5

        self.position = self._calculate_initial_position()

        self.is_reversal = self._calculate_initial_reversal()

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
        return position

    def _calculate_initial_reversal(self):
        position = dict((s, 0) for s in self.symbol_list)
        return position

    def calculate_signals(self):
        for symbol in self.symbol_list:

            # Gather enough data points to perform indicators calculations
            if self.counter < self.data_points:
                self.counter += 1
                break

            latest_closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            current_close = latest_closes[-1]

            # Init signal infos
            signal_datetime = self.data_handler.get_latest_bar(symbol).Index
            signal_type = ''

            # Init OHLCV bars and indicators
            latest_datetimes = self.data_handler.get_latest_bars_values(
                symbol, 'Index', N=self.data_points)
            latest_highs = self.data_handler.get_latest_bars_values(
                symbol, 'high', N=self.data_points)
            latest_lows = self.data_handler.get_latest_bars_values(
                symbol, 'low', N=self.data_points)

            current_high = latest_highs[-1]
            current_low = latest_lows[-1]

            rsis = RSI(latest_closes, timeperiod=self.rsi_window)
            rsis = rsis[~np.isnan(rsis)]

            index_lows = peakutils.indexes(
                -latest_lows, thres=0.95, min_dist=1)
            index_highs = peakutils.indexes(
                latest_highs, thres=0.95, min_dist=1)

            index_rsi_lows = peakutils.indexes(-rsis,
                                               thres=0., min_dist=1)
            index_rsi_highs = peakutils.indexes(rsis,
                                                thres=0.95, min_dist=1)

            lows_peak = latest_lows[index_lows]
            highs_peak = latest_highs[index_highs]
            rsis_peak_lows = rsis[index_rsi_lows]
            rsis_peak_highs = rsis[index_rsi_highs]

            upper, middle, lower = BBANDS(
                latest_closes, timeperiod=self.ma_window, nbdevup=3, nbdevdn=3)

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                if len(lows_peak) >= 2 and len(rsis_peak_lows) >= 2 and lows_peak[-2] > lows_peak[-1] and rsis_peak_lows[-2] < rsis_peak_lows[-1] and current_low <= lower[-1]:
                    print(f'{symbol} - LONG: {signal_datetime}')
                    signal_type = 'LONG'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type,
                        strength=1
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'IN'
                    break

            elif self.position[symbol] == 'IN':
                current_value = current_close * \
                    self.portfolio.current_positions[symbol]

                trailing_ls = self.portfolio.current_holdings[symbol]['trailing_sl'](
                    current_value)

                if current_value <= trailing_ls:
                    print(f'{symbol} - STOP LOSS: {signal_datetime}')
                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
