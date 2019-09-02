from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np

from talib import RSI, EMA, BBANDS

from helpers import init_trailing_long, detect_div_v1


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 100
        self.counter = 0

        self.rsi_window = 14
        self.ma_window = 20

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
            signal_datetime = self.data_handler.get_latest_bar(symbol).Index
            signal_type = ''

            # Init OHLCV bars and indicators
            closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            highs = self.data_handler.get_latest_bars_values(
                symbol, 'high', N=self.data_points)
            lows = self.data_handler.get_latest_bars_values(
                symbol, 'low', N=self.data_points)

            current_close = closes[-1]
            current_low = lows[-1]


            hlc = (closes + highs + lows) / 3

            rsis = RSI(closes, timeperiod=self.rsi_window)
            # rsis = rsis[~np.isnan(rsis)]

            upper, middle, lower = BBANDS(
                hlc, timeperiod=self.ma_window, nbdevup=4, nbdevdn=4)

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                trend = detect_div_v1(closes, rsis)
#and current_close <= lower[-1] and ( current_low <= middle[-1] and current_low >= lower[-1])
                if trend == 'bull':
                    self.is_reversal[symbol]=1
                    break
                if self.is_reversal[symbol]==1 and current_close>closes[-2]:
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
                    self.trailing[symbol] = init_trailing_long(
                        current_close,
                        pct_sl=0.07,
                        pct_tp=0.01
                    )
                    self.is_reversal[symbol]=0
                    break

            elif self.position[symbol] == 'IN':
                trailing_sl = self.trailing[symbol](current_close)

                
                if current_close <= trailing_sl:
                    print(f'{symbol} - STOP LOSS: {signal_datetime}')
                    signal_type = 'EXIT'
                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    break