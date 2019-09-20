from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, BBANDS
from custom_indicators import bull_div, bear_div

from helpers import stop_loss, init_trailing_long, init_trailing_short, get_day_of_week

from math import floor


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.counter = 0

        self.bars_window = 250
        self.div_window = 30
        self.rsi_window = 14

        self.ma_short = 10
        self.ma_long = 50

        self.ma_trend = 10
        self.data_points = 4*24*7*self.ma_trend
        self.trend_counter = 0

        self.bb_std = 2
        self.bb_window = 20

        self.open_price = None
        self.trailing = None

        self.stop_loss = 0

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
            rsi_set = rsi[-self.div_window:]

            ma_long = EMA(hlc3, timeperiod=self.ma_long)[-1]
            ma_short = EMA(hlc3, timeperiod=self.ma_short)[-1]

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                dt = get_day_of_week(signal_datetime)
                close_lg = self.data_handler.get_weekly_bar_value(
                    symbol, dt, 'close')
                ma_lg = self.data_handler.get_weekly_bar_value(
                    symbol, dt, f'ema{self.ma_trend}')

                is_bullish_trend = close_lg > ma_lg
                is_bearish_trend = close_lg < ma_lg

                price_set_low = lows[-self.div_window:]
                price_set_high = highs[-self.div_window:]
                prominence = ma_long*0.001

                if is_bullish_trend:
                    print('Long-term BULLISH')
                    if current_close < ma_short:
                        print('Short-term bearish')
                        self.trend_counter += 1

                        if self.trend_counter >= 60:
                            is_div = bull_div(
                                price_set_low, rsi_set, prominence, 1)

                            if is_div:
                                signal_type = 'LONG'
                                print(
                                    f'{symbol} - {signal_type}: {signal_datetime}')

                                signal = SignalEvent(
                                    symbol=symbol,
                                    datetime=signal_datetime,
                                    signal_type=signal_type,
                                    strength=is_div/3,
                                    indicators=None
                                )
                                self.events.put(signal)
                                self.position[symbol] = signal_type
                                self.open_price = current_close
                                self.trailing = init_trailing_long(
                                    self.open_price, 0.02, 0.05)
                                self.trend_counter = 0
                                break

                elif is_bearish_trend:
                    print('Long-term BEARISH')
                    if ma_short > ma_long:
                        print('Short-term bullish')
                        self.trend_counter += 1

                        if self.trend_counter >= 50:
                            is_div = bear_div(
                                price_set_high, rsi_set, prominence, 1)

                            if is_div:
                                signal_type = 'SHORT'
                                print(
                                    f'{symbol} - {signal_type}: {signal_datetime}')

                                signal = SignalEvent(
                                    symbol=symbol,
                                    datetime=signal_datetime,
                                    signal_type=signal_type,
                                    strength=is_div/3,
                                    indicators=None
                                )
                                self.events.put(signal)
                                self.position[symbol] = signal_type
                                self.open_price = current_close
                                self.trailing = init_trailing_short(
                                    self.open_price, 0.04, 0.08)
                                self.trend_counter = 0
                                break

            # Sell Signal conditions
            elif self.position[symbol] == 'LONG':
                returns = ((current_close / self.open_price) - 1)

                current_trailing = self.trailing(current_close)

                if current_close <= current_trailing:
                    if returns > 0:
                        print(f'{symbol} - WIN: {signal_datetime}')
                        print('Returns %: ', returns*100)

                    else:
                        print(f'{symbol} - LOSS: {signal_datetime}')
                        print('Returns %: ', returns*100)

                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    break

            # Sell Signal conditions
            elif self.position[symbol] == 'SHORT':
                returns = ((self.open_price / current_close) - 1)

                current_trailing = self.trailing(current_close)

                if current_close >= current_trailing:
                    if returns > 0:
                        print(f'{symbol} - WIN: {signal_datetime}')
                        print('Returns %: ', returns*100)

                    else:
                        print(f'{symbol} - LOSS: {signal_datetime}')
                        print('Returns %: ', returns*100)

                    signal_type = 'EXITSHORT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    break
