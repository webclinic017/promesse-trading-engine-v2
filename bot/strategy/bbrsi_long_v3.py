from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, BBANDS
from custom_indicators import bull_div, bear_div

from helpers import stop_loss, init_trailing_long, get_day_of_week

from math import floor

from colored import fg, bg, attr
red = fg('red')
green = fg('green')
bold = attr(1)
reset = attr('reset')


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.counter = 0

        self.bars_window = 250
        self.div_window = 200
        self.rsi_window = 14

        self.ma_short = 20
        self.ma_long = 90

        self.ma_trend = 5
        self.data_points = 4*24*7*self.ma_trend
        self.trend_counter = 0

        self.bb_std = 2
        self.bb_window = 20

        self.open_price = None
        self.trailing = None

        self.stop_loss = 0

        self.sell_signal = 0
        self.trend_counter = 0

        self.position = self._calculate_initial_position()

        self.is_div = None
        self.div_signal = 0
        self.buy_signal = 0

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
                symbol, 'open', N=self.bars_window)

            highs = self.data_handler.get_latest_bars_values(
                symbol, 'high', N=self.bars_window)

            lows = self.data_handler.get_latest_bars_values(
                symbol, 'low', N=self.bars_window)

            closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.bars_window)

            hlc3 = (highs + lows + closes) / 3

            current_open = self.data_handler.get_latest_bar_value(
                symbol, 'open')
            current_high = self.data_handler.get_latest_bar_value(
                symbol, 'high')
            current_low = self.data_handler.get_latest_bar_value(
                symbol, 'low')
            current_close = self.data_handler.current_price(symbol)

            rsi = RSI(closes, timeperiod=self.rsi_window)

            ma_long = EMA(closes, timeperiod=self.ma_long)[-1]
            ma_short = EMA(closes, timeperiod=self.ma_short)[-1]
            prominence = ma_long*0.001

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                dt = get_day_of_week(signal_datetime)
                close_lg = self.data_handler.get_weekly_bar_value(
                    symbol, dt, 'close')
                ma_lg = self.data_handler.get_weekly_bar_value(
                    symbol, dt, f'ema{self.ma_trend}')

                is_bullish_trend = close_lg > ma_lg

                if is_bullish_trend:
                    print('Long-term BULLISH')
                    if ma_short < ma_long:
                        print('Short-term bearish')
                        self.trend_counter += 1

                    if self.trend_counter >= 20 and not self.is_div:
                        print('Short-term bearish')
                        self.is_div = bull_div(
                            lows,
                            rsi,
                            window=self.div_window,
                            price_prominence=prominence,
                            rsi_prominence=1)

                        if self.is_div:
                            print('Div detected')
                            self.div_signal += 1

                    if self.div_signal and rsi[-1] >= 30 and current_close > current_open:
                        signal_type = 'LONG'
                        print(
                            f'{symbol} - {signal_type}: {signal_datetime}')

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
                        self.trend_counter = 0
                        self.is_div = None
                        self.div_signal = 0
                        break

                    if self.div_signal >= 4:
                        self.trend_counter = 0
                        self.is_div = None
                        self.div_signal = 0
                        break

            elif self.position[symbol] == 'LONG':
                returns = ((current_close / self.open_price) - 1)

                upper, middle, lower = BBANDS(
                    hlc3,
                    timeperiod=self.bb_window,
                    nbdevup=self.bb_std,
                    nbdevdn=self.bb_std)

                if returns >= 0.05 or returns <= -0.02:
                    if returns > 0:
                        print(bold + green +
                              f'{symbol} - WIN: {signal_datetime}' + reset)
                        print('Returns %: ', returns*100)
                        print('Trend counter: ', self.trend_counter)

                    else:
                        print(bold + red +
                              f'{symbol} - LOSS: {signal_datetime}' + reset)
                        print('Returns %: ', returns*100)
                        print('Trend counter: ', self.trend_counter)

                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    self.sell_signal = 0
                    break
