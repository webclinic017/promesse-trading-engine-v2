from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, BBANDS
from custom_indicators import BULL_DIV, BULL_DIV_2, BEAR_DIV, HBULL_DIV, HBEAR_DIV

from helpers import stop_loss


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 250
        self.counter = 0

        self.rsi_window = 14
        self.ma_short = 10
        self.ma_long = 50
        self.div_window = 20

        self.position = self._calculate_initial_position()

        self.stop_loss = None

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
        return position

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
            bars = self.data_handler.get_latest_bars_df(
                symbol, N=self.data_points)
            current_close = self.data_handler.current_price(symbol)

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                bars['rsi'] = RSI(bars['close'])
                price_set = bars[bars['open'] >
                                 bars['close']]['low'][-self.div_window:]
                rsi_set = bars[bars['open'] > bars['close']
                               ]['rsi'][-self.div_window:]
                result = BULL_DIV_2(price_set, rsi_set)

                if result['is_div'] and result['nb_div'] >= 1:
                    signal_type = 'LONG'
                    print(
                        f'{symbol} - {signal_type}: {signal_datetime}')

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type,
                        strength=1,
                        indicators=result['local_min']
                    )
                    self.events.put(signal)
                    self.position[symbol] = signal_type
                    break

            # Sell Signal conditions
            elif self.position[symbol] == 'LONG':
                hlc3 = (bars['high'] + bars['low'] + bars['close']) / 3
                upper, middle, lower = BBANDS(
                    hlc3, timeperiod=20, nbdevup=2, nbdevdn=2)

                if current_close >= upper[-1]:
                    print(f'{symbol} - TP: {signal_datetime}')
                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
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
                    break
