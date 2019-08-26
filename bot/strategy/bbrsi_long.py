from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np

from talib import RSI, EMA, SMA, BBANDS

from helpers import init_trailing_long, init_trailing_short, detect_div


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 210
        self.counter = 0

        self.rsi_window = 14
        self.ma_window = 21

        self.position = self._calculate_initial_position()
        self.trailing = self._calculate_initial_trailing()

        self.is_reversal = self._calculate_initial_reversal()

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
        return position

    def _calculate_initial_reversal(self):
        position = dict((s, 0) for s in self.symbol_list)
        return position

    def _calculate_initial_trailing(self):
        trailing = dict((s, None) for s in self.symbol_list)
        return trailing

    def calculate_signals(self):
        for symbol in self.symbol_list:

            # Gather enough data points to perform indicators calculations
            if self.counter < self.data_points:
                self.counter += 1
                break

            # Init signal infos
            signal_datetime = self.data_handler.get_latest_bar(
                symbol).Index
            signal_type = ''

            # Init OHLCV bars and indicators
            closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            highs = self.data_handler.get_latest_bars_values(
                symbol, 'high', N=self.data_points)
            lows = self.data_handler.get_latest_bars_values(
                symbol, 'low', N=self.data_points)

            current_close = closes[-1]

            rsis = RSI(closes, timeperiod=self.rsi_window)
            ma_long = SMA(closes, timeperiod=200)[-1]
            ma_short = SMA(closes, timeperiod=20)[-1]

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                trend = detect_div(lows, rsis)

                if trend == 'bull' and ma_short > ma_long:
                    self.is_reversal[symbol] = 1
                    break

                if self.is_reversal[symbol] == 1 and closes[-1] > closes[-2]:
                    print(
                        f'{symbol} - LONG: {signal_datetime}')
                    signal_type = 'LONG'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type,
                        strength=1
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'IN'
                    self.trailing[symbol] = init_trailing_long(
                        current_close,
                        pct_sl=0.09,
                        pct_tp=0.1
                    )
                    self.is_reversal[symbol] = 0
                    break

                if trend != 'bull' and self.is_reversal[symbol] != 0:
                    self.is_reversal[symbol] = 0
                    break

            if self.position[symbol] == 'IN':
                trailing_sl = self.trailing[symbol](current_close)

                if current_close <= trailing_sl:
                    print(f'{symbol} - TP: {signal_datetime}')
                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    self.is_reversal[symbol] = 0
                    break
