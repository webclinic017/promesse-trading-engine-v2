from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, BBANDS, MA_Type
from custom_indicators import bull_div

from helpers import stop_loss, init_trailing_long

from math import floor


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 250
        self.counter = 0

        self.div_window = 30
        self.rsi_window = 14

        self.ma_short = 20
        self.ma_long = 90

        self.bb_std = 2
        self.bb_window = 20

        self.sell_signal = 0
        self.open_price = None

        self.position = self._calculate_initial_position()

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
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

            opens = self.data_handler.get_latest_bars_values(
                symbol, 'open', N=self.data_points)

            highs = self.data_handler.get_latest_bars_values(
                symbol, 'high', N=self.data_points)

            lows = self.data_handler.get_latest_bars_values(
                symbol, 'low', N=self.data_points)

            closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)

            hlc3 = (highs + lows + closes) / 3

            current_open = self.data_handler.get_latest_bar_value(
                symbol, 'open')
            current_high = self.data_handler.get_latest_bar_value(
                symbol, 'high')
            current_low = self.data_handler.get_latest_bar_value(
                symbol, 'low')
            current_close = self.data_handler.current_price(symbol)

            rsi = RSI(closes, timeperiod=self.rsi_window)
            rsi_set = rsi[-self.div_window:]

            ma_long = EMA(hlc3, timeperiod=self.ma_long)[-1]
            ma_short = EMA(hlc3, timeperiod=self.ma_short)[-1]

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                price_set_low = lows[-self.div_window:]

                if current_high < ma_short and ma_short < ma_long:
                    print('Short-term bearish')
                    is_div = bull_div(
                        price_set_low, rsi_set, ma_short*0.001, 1)

                    if is_div:
                        signal_type = 'LONG'
                        print(f'{symbol} - {signal_type}: {signal_datetime}')

                        signal = SignalEvent(
                            symbol=symbol,
                            datetime=signal_datetime,
                            signal_type=signal_type,
                            strength=1,
                            indicators=None
                        )
                        self.events.put(signal)
                        self.position[symbol] = signal_type
                        self.open_price = current_close
                        break

            # Sell Signal conditions
            elif self.position[symbol] == 'LONG':

                upper, middle, lower = BBANDS(
                    hlc3,
                    timeperiod=self.bb_window,
                    nbdevup=self.bb_std,
                    nbdevdn=self.bb_std)

                if current_close >= upper[-1]:
                    self.sell_signal += 1

                if self.sell_signal == 3:
                    if current_close > self.open_price:
                        print(f'{symbol} - WIN: {signal_datetime}')
                        print('Sell Signal: ', self.sell_signal)

                    else:
                        print(f'{symbol} - LOSS: {signal_datetime}')
                        print('Sell Signal: ', self.sell_signal)

                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    self.sl_signal = 0
                    self.sell_signal = 0
                    break
