from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np

from talib import RSI, EMA
from custom_indicators import PPSR

from helpers import get_prev_daily_hlc, init_trailing_long, init_trailing_short


class PPRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio
        self.timeframe = self.data_handler.timeframe

        self.data_points = 50
        self.counter = 0

        self.trailing = self._calculate_initial_trailing()
        self.position = self._calculate_initial_position()
        self.pullback = self._calculate_initial_pullback()

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
        return position

    def _calculate_initial_pullback(self):
        pullback = dict((s, 0) for s in self.symbol_list)
        return pullback

    def _calculate_initial_trailing(self):
        trailing = dict((s, None) for s in self.symbol_list)
        return trailing

    def calculate_signals(self):
        for symbol in self.symbol_list:

            # Gather enough data points to perform indicators calculations
            if self.counter < self.data_points:
                self.counter += 1
                break

            latest_closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            current_close = self.data_handler.current_price(symbol)

            # Init signal infos
            signal_datetime = self.data_handler.get_latest_bar(symbol).Index
            signal_type = ''

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':

                # Init OHLCV bars and indicators
                latest_datetimes = self.data_handler.get_latest_bars_values(
                    symbol, 'datetime', N=self.data_points)
                latest_highs = self.data_handler.get_latest_bars_values(
                    symbol, 'high', N=self.data_points)

                latest_opens = self.data_handler.get_latest_bars_values(
                    symbol, 'open', N=self.data_points)
                current_open = latest_opens[-1]

                latest_lows = self.data_handler.get_latest_bars_values(
                    symbol, 'low', N=self.data_points)

                pp, s1, s2, s3, r1, r2, r3 = PPSR(
                    *get_prev_daily_hlc(
                        self.timeframe,
                        latest_datetimes,
                        latest_highs,
                        latest_lows,
                        latest_closes
                    )
                )

                rsi = RSI(latest_closes)[-1]
                ma = EMA(latest_closes, timeperiod=3)[-1]

                if current_close < pp and current_close and ma and rsi < 70 and self.pullback[symbol] == 0:
                    print('↗↗ PP BEARISH TREND')
                    self.pullback[symbol] = 1
                    break

                if current_close >= pp and self.pullback[symbol] == 1:
                    print('↗↗ PP PULL BACK')
                    print(f'{symbol} - SHORT: {signal_datetime}')
                    signal_type = 'SHORT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type,
                        strength=1
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'SHORT'
                    self.pullback[symbol] = 0
                    self.trailing[symbol] = init_trailing_short(
                        current_close,
                        pct_sl=0.04,
                        pct_tp=0.08
                    )
                    break

            elif self.position[symbol] == 'SHORT':
                trailing_ls = self.trailing[symbol](current_close)

                print(
                    self.portfolio.current_holdings[symbol]['open_price'], current_close, trailing_ls)
                if current_close >= trailing_ls:
                    print(f'{symbol} - STOP LOSS: {signal_datetime}')
                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
