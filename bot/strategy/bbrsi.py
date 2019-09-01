from strategy.strategy import Strategy
from event import SignalEvent

import queue

import numpy as np
import pandas as pd

from talib import RSI, EMA
from custom_indicators import BULL_DIV, BEAR_DIV, HBULL_DIV, HBEAR_DIV

from helpers import init_trailing_long, init_trailing_short


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.portfolio = portfolio

        self.data_points = 3360  # 1*24*7*20  (1h timeframe, 20 MA)
        self.counter = 0

        self.rsi_window = 14
        self.ma_short = 10
        self.ma_long = 50

        self.position = self._calculate_initial_position()
        self.trailing = self._calculate_initial_trailing()

        self.is_reversal = self._calculate_initial_reversal()

        self.trend = None

        self.prominence = {
            'BTC-USDT': 42
        }

        self.risk_m = {
            'BTC-USDT': {
                'LONG': (0.08, 0.1),
                'SHORT': (0.08, 0.1)
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
            closes_w = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.data_points)
            closes = closes_w[-250:]
            current_close = closes[-1]
            # highs = self.data_handler.get_latest_bars_values(
            #     symbol, 'high', N=self.data_points)
            # lows = self.data_handler.get_latest_bars_values(
            #     symbol, 'low', N=self.data_points)

            # Buy Signal conditions
            if self.position[symbol] == 'OUT':

                # Init indicators
                rsis = RSI(closes, timeperiod=self.rsi_window)
                ma_long = EMA(closes, timeperiod=self.ma_long)[-1]
                ma_short = EMA(closes, timeperiod=self.ma_short)[-1]

                # Calculate weekly MA
                data_w = pd.DataFrame(
                    data=closes_w, index=datetimes, columns=['close'])

                closes_weekly = data_w.resample('W').agg({
                    'close': lambda x: x[-1]
                })['close'].to_numpy()
                close_weekly = closes_weekly[-1]
                ma20_weekly = EMA(closes_weekly, timeperiod=20)[-1]

                # Long-term bullish trend
                if close_weekly > ma20_weekly:

                    # Short-term bearish trend -> bullish divergence
                    if ma_short < ma_long:
                        self.trend = BULL_DIV(
                            closes, rsis, self.prominence[symbol])

                        if self.trend == 'bull':
                            self.is_reversal[symbol] = 1
                            break

                        if self.is_reversal[symbol] == 1 and current_close > closes[-2]:
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
                            self.is_reversal[symbol] = 0
                            break

                    # Short-term bullish trend -> hidden bullish
                    elif ma_short > ma_long:
                        self.trend = HBULL_DIV(
                            closes, rsis, self.prominence[symbol])

                        if self.trend == 'hbull':
                            self.is_reversal[symbol] = 1
                            break

                        if self.is_reversal[symbol] == 1 and current_close > closes[-2]:
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
                            self.is_reversal[symbol] = 0
                            break

                # Long-term bearish trend
                elif close_weekly < ma20_weekly:

                    # Short-term bullish trend -> bearish divergence
                    if ma_short > ma_long:
                        self.trend = BEAR_DIV(
                            closes, rsis, self.prominence[symbol])

                        if self.trend == 'bear':
                            self.is_reversal[symbol] = 1
                            break

                        if self.is_reversal[symbol] == 1 and current_close < closes[-2]:
                            print(
                                f'{symbol} {self.trend} - SHORT: {signal_datetime}')
                            signal_type = 'SHORT'

                            signal = SignalEvent(
                                symbol=symbol,
                                datetime=signal_datetime,
                                signal_type=signal_type,
                                strength=1
                            )
                            self.events.put(signal)
                            self.position[symbol] = 'SHORT'
                            self.trailing[symbol] = init_trailing_short(
                                current_close,
                                pct_sl=self.risk_m[symbol][signal_type][0],
                                pct_tp=self.risk_m[symbol][signal_type][1]
                            )
                            self.is_reversal[symbol] = 0
                            break

                    # Short-term bearish trend -> hidden bearish
                    elif ma_short < ma_long:
                        self.trend = HBEAR_DIV(
                            closes, rsis, self.prominence[symbol])

                        if self.trend == 'hbear':
                            self.is_reversal[symbol] = 1
                            break

                        if self.is_reversal[symbol] == 1 and current_close < closes[-2]:
                            print(
                                f'{symbol} {self.trend} - SHORT: {signal_datetime}')
                            signal_type = 'SHORT'

                            signal = SignalEvent(
                                symbol=symbol,
                                datetime=signal_datetime,
                                signal_type=signal_type,
                                strength=1
                            )
                            self.events.put(signal)
                            self.position[symbol] = 'SHORT'
                            self.trailing[symbol] = init_trailing_short(
                                current_close,
                                pct_sl=self.risk_m[symbol][signal_type][0],
                                pct_tp=self.risk_m[symbol][signal_type][1]
                            )
                            self.is_reversal[symbol] = 0
                            break

                # if ma_short > ma_long:
                #     self.trend = detect_bull_div(
                #         closes, rsis, self.prominence[symbol])

                #     if self.trend == 'bull':
                #         self.is_reversal[symbol] = 1
                #         break

                #     if self.is_reversal[symbol] == 1 and current_close > closes[-2]:
                #         print(
                #             f'{symbol} - LONG: {signal_datetime}')
                #         signal_type = 'LONG'

                #         signal = SignalEvent(
                #             symbol=symbol,
                #             datetime=signal_datetime,
                #             signal_type=signal_type,
                #             strength=2
                #         )
                #         self.events.put(signal)
                #         self.position[symbol] = 'LONG'
                #         self.trailing[symbol] = init_trailing_long(
                #             current_close,
                #             pct_sl=self.risk_m[symbol][signal_type][0],
                #             pct_tp=self.risk_m[symbol][signal_type][1]
                #         )
                #         self.is_reversal[symbol] = 0
                #         break

                # if ma_short < ma_long:
                #     self.trend = detect_bear_div(
                #         closes, rsis, self.prominence[symbol])

                #     if self.trend == 'bear':
                #         self.is_reversal[symbol] = 1
                #         break

                #     if self.is_reversal[symbol] == 1 and current_close < closes[-2]:
                #         print(
                #             f'{symbol} - SHORT: {signal_datetime}')
                #         signal_type = 'SHORT'

                #         signal = SignalEvent(
                #             symbol=symbol,
                #             datetime=signal_datetime,
                #             signal_type=signal_type,
                #             strength=2
                #         )
                #         self.events.put(signal)
                #         self.position[symbol] = 'SHORT'
                #         self.trailing[symbol] = init_trailing_short(
                #             current_close,
                #             pct_sl=self.risk_m[symbol][signal_type][0],
                #             pct_tp=self.risk_m[symbol][signal_type][1]
                #         )
                #         self.is_reversal[symbol] = 0
                #         break

                if not self.trend and self.is_reversal[symbol] != 0:
                    self.is_reversal[symbol] == 0
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
                    self.is_reversal[symbol] = 0
                    break
