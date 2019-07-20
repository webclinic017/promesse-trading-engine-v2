from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np

from talib import RSI, EMA
from custom_indicators import PPSR

from helpers import get_prev_daily_hlc


class PPRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 50
        self.counter = 0

        self.rsi_window = 14
        self.ma_window = 5

        self.position = self._calculate_initial_position()
        self.pullback = self._calculate_initial_pullback()

    def _calculate_initial_position(self):
        position = dict((s, 'OUT') for s in self.symbol_list)
        return position

    def _calculate_initial_pullback(self):
        pullback = dict((s, 0) for s in self.symbol_list)
        return pullback

    def calculate_signals(self):
        for symbol in self.symbol_list:

            # Gather enough data points to perform indicators calculations
            if self.counter < self.data_points:
                self.counter += 1
                break

            latest_closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            current_close = latest_closes[-1]

            # Init signal infos
            signal_datetime = self.data_handler.get_latest_bar(symbol).Index
            signal_type = ''

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':

                # Init OHLCV bars and indicators
                latest_datetimes = self.data_handler.get_latest_bars_values(
                    symbol, 'Index', N=self.data_points)
                latest_highs = self.data_handler.get_latest_bars_values(
                    symbol, 'high', N=self.data_points)
                latest_lows = self.data_handler.get_latest_bars_values(
                    symbol, 'low', N=self.data_points)

                current_ema = EMA(latest_closes, timeperiod=self.ma_window)[-1]
                current_rsi = RSI(
                    latest_closes, timeperiod=self.rsi_window)[-1]

                pp, s1, s2, s3, r1, r2, r3 = PPSR(
                    *get_prev_daily_hlc(
                        '1h',
                        latest_datetimes,
                        latest_highs,
                        latest_lows,
                        latest_closes
                    )
                )

                if current_close > pp and current_close < r1 and current_close > current_ema and current_rsi >= 15 and current_rsi <= 60 and self.pullback[symbol] == 0:
                    print('↗↗ PP BULLISH TREND')
                    self.pullback[symbol] = 1
                    break

                if current_close <= pp and self.pullback[symbol] == 1:
                    print('↗↗ PP PULL BACK')
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
                    self.pullback[symbol] = 0
                    break

            elif self.position[symbol] == 'IN':
                current_value = current_close * \
                    self.portfolio.current_positions[symbol]

                trailing_ls = self.portfolio.current_holdings[symbol]['trailing_sl'](
                    current_value)

                if current_value <= trailing_ls:
                    print(f'{symbol} - STOP LOSS: {signal_datetime}')
                    signal_type = 'EXIT'

                    signal = SignalEvent(
                        symbol=symbol,
                        datetime=signal_datetime,
                        signal_type=signal_type
                    )
                    self.events.put(signal)
                    self.position[symbol] = 'OUT'
