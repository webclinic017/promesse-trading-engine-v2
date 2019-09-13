from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, BBANDS, MA_Type
from custom_indicators import BEAR_DIV_2, BEAR_DIV_RSI_2

from helpers import stop_loss, init_trailing_long

from math import floor


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 4*24*20
        self.counter = 0

        self.bars_window = 250

        self.div_window = 30
        self.rsi_window = 14

        self.ma_short = 10
        self.ma_long = 50
        self.ma_weekly = 20

        self.bb_std = 2
        self.bb_window = 20

        self.trailing = 0
        self.activate_trailing = 0
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

            # Init OHLCV bars and indicators
            # bars_all = self.data_handler.get_latest_bars_df(
            #     symbol, N=self.data_points)
            # bars = bars_all[-self.bars_window:]
            bars = self.data_handler.get_latest_bars_df(symbol, N=250)
            bars['hlc3'] = (bars['high'] + bars['low'] + bars['close']) / 3

            current_open = self.data_handler.get_latest_bar_value(
                symbol, 'open')
            current_high = self.data_handler.get_latest_bar_value(
                symbol, 'high')
            current_low = self.data_handler.get_latest_bar_value(
                symbol, 'low')
            current_close = self.data_handler.current_price(symbol)

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                bars['rsi'] = RSI(bars['hlc3'], timeperiod=self.rsi_window)
                is_green_bars = bars['open'] < bars['close']
                price_set = bars[is_green_bars]['high'][-self.div_window:]
                rsi_set = bars[is_green_bars]['rsi'][-self.div_window:]

                ma_long = EMA(bars['close'], timeperiod=self.ma_long)[-1]
                ma_short = EMA(bars['close'], timeperiod=self.ma_short)[-1]

                # if is_bullish:
                #     print('Long-term bullish')
                div_price = BEAR_DIV_2(price_set, rsi_set,
                                       bars['open'], bars['close'], 10)
                div_rsi = BEAR_DIV_RSI_2(price_set, rsi_set,
                                         bars['open'], bars['close'], 1)

                if ma_short > ma_long:
                    if div_price['is_div'] and div_rsi['is_div']:
                        signal_type = 'SHORT'
                        print(
                            f'{symbol} - {signal_type}: {signal_datetime}')

                        signal = SignalEvent(
                            symbol=symbol,
                            datetime=signal_datetime,
                            signal_type=signal_type,
                            strength=div_price['nb_div'],
                            indicators=div_price['local_min']
                        )
                        self.events.put(signal)
                        self.position[symbol] = signal_type
                        self.open_price = current_close
                        break

            # Sell Signal conditions
            elif self.position[symbol] == 'SHORT':
                upper, middle, lower = BBANDS(
                    bars['hlc3'],
                    timeperiod=self.bb_window,
                    nbdevup=self.bb_std,
                    nbdevdn=self.bb_std)

                if (current_low <= lower[-1] and current_close < current_open):
                    self.sell_signal += 1

                    if self.sell_signal <= 2:
                        break

                    if current_close < self.open_price:
                        print(f'{symbol} - WIN: {signal_datetime}')
                        print('Sell Signal: ', self.sell_signal)

                    else:
                        print(f'{symbol} - LOSS: {signal_datetime}')
                        print('Sell Signal: ', self.sell_signal)

                    signal_type = 'EXITSHORT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
                    self.sell_signal = 0
                    break
