from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA, SMA
from custom_indicators import BULL_DIV, BULL_DIV_2, BEAR_DIV, HBULL_DIV, HBEAR_DIV

from helpers import init_trailing_long, init_trailing_short


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 250  # 1*24*7*20  (1h timeframe, 20 MA)
        self.counter = 0

        self.rsi_window = 14
        self.ma_short = 5
        self.ma_long = 15

        self.position = self._calculate_initial_position()
        self.trailing = self._calculate_initial_trailing()

        self.is_reversal = self._calculate_initial_reversal()

        self.prominence = {
            'BTC-USDT': 42
        }

        self.risk_m = {
            'BTC-USDT': {
                'LONG': (0.01, 0.02),
                'SHORT': (0.01, 0.018)
            },
            'NEO-BTC': {
                'LONG': (0.01, 0.02),
                'SHORT': (0.01, 0.018)
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
            bars = self.data_handler.get_latest_bars_df(
                symbol, N=self.data_points)

            bars['rsi'] = RSI(bars['close'])

            current_close = self.data_handler.current_price(symbol)
            current_open = self.data_handler.get_latest_bar_value(
                symbol, 'open')

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':
                price_set = bars[bars['open'] > bars['close']]['low'][-20:]
                rsi_set = bars[bars['open'] > bars['close']]['rsi'][-20:]
                result = BULL_DIV_2(price_set, rsi_set, 40)

                if result and result['is_div'] and not result['local_min']:
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
                    self.trailing[symbol] = init_trailing_long(
                        current_close,
                        pct_sl=self.risk_m[symbol][signal_type][0],
                        pct_tp=self.risk_m[symbol][signal_type][1]
                    )
                    self.is_reversal[symbol] = 0
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
                    self.trend_price[symbol] = 0
                    break
