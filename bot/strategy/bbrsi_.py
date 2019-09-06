from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, SMA
from custom_indicators import BULL_DIV, BEAR_DIV, HBULL_DIV, HBEAR_DIV

from helpers import init_trailing_long, init_trailing_short


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 248
        self.counter = 0

        self.rsi_window = 14
        self.ma_short = 10
        self.ma_long = 80

        self.position = self._calculate_initial_position()
        self.trailing = self._calculate_initial_trailing()

        self.is_reversal = self._calculate_initial_reversal()
        self.trend = self._calculate_initial_trend()

        self.prominence = {
            'BTC-USDT': 42
        }

        self.risk_m = {
            'BTC-USDT': {
                'LONG': (0.09, 0.13),
                'SHORT': (0.09, 0.13)
            }
        }

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
        return position

    def _calculate_initial_reversal(self):
        position = dict((s, 0) for s in self.symbol_list)
        return position

    def _calculate_initial_trailing(self):
        trailing = dict((s, None) for s in self.symbol_list)
        return trailing

    def _calculate_initial_trend(self):
        trend = dict((s, None) for s in self.symbol_list)
        return trend

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
            datetimes = self.data_handler.get_latest_bars_values(
                symbol, 'datetime', N=self.data_points)
            closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            current_close = closes[-1]

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                # Init indicators
                rsis = RSI(closes, timeperiod=self.rsi_window)
                ma_long = SMA(closes, timeperiod=self.ma_long)[-1]
                ma_short = EMA(closes, timeperiod=self.ma_short)[-1]

                if ma_short > ma_long:
                    print('↗ Bullish')
                    self.trend[symbol], peak = BULL_DIV(
                        closes, rsis, self.prominence[symbol], window=2)

                    if self.trend[symbol] == 'bull' and peak:
                        print('Divergeance')
                        if current_close > peak and closes[-2] > peak:
                            print(self.trend[symbol], current_close, peak)
                            print(
                                f'{symbol} {self.trend} - LONG: {signal_datetime}')
                            signal_type = 'LONG'

                            signal = SignalEvent(
                                symbol=symbol,
                                datetime=signal_datetime,
                                signal_type=signal_type,
                                strength=1
                            )
                            self.events.put(signal)
                            self.position[symbol] = 'LONG'
                            self.trailing[symbol] = init_trailing_long(
                                current_close,
                                pct_sl=self.risk_m[symbol][signal_type][0],
                                pct_tp=self.risk_m[symbol][signal_type][1]
                            )
                            self.trend[symbol] = None
                    break

                elif ma_short < ma_long:
                    print('↗ Bearish')
                    self.trend[symbol], peak = BEAR_DIV(
                        closes, rsis, self.prominence[symbol])

                    if self.trend[symbol] == 'bear' and peak:
                        print('Divergeance')
                        if current_close < peak and closes[-2] < peak:
                            print(self.trend[symbol], current_close, peak)
                            signal_type = 'SHORT'
                            print(
                                f'{symbol} {self.trend} - {signal_type}: {signal_datetime}')

                            signal = SignalEvent(
                                symbol=symbol,
                                datetime=signal_datetime,
                                signal_type=signal_type,
                                strength=1
                            )
                            self.events.put(signal)
                            self.position[symbol] = signal_type
                            self.trailing[symbol] = init_trailing_short(
                                current_close,
                                pct_sl=self.risk_m[symbol][signal_type][0],
                                pct_tp=self.risk_m[symbol][signal_type][1]
                            )
                            self.trend[symbol] = None
                        break

            # Sell Signal conditions
            elif self.position[symbol] == 'LONG':
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

            elif self.position[symbol] == 'SHORT':
                trailing_sl = self.trailing[symbol](current_close)

                if current_close >= trailing_sl:
                    print(f'{symbol} - TP: {signal_datetime}')
                    signal_type = 'EXITSHORT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    self.trend[symbol] = None
                    self.is_reversal[symbol] = 0
                    break
