from strategy.strategy import Strategy

import queue

import numpy as np
import pandas as pd

from datetime import datetime
from talib import RSI, EMA
from custom_indicators import bull_div, bear_div
from helpers import load_config

from telegram import TelegramBot


class BBRSI(Strategy):
    def __init__(self, events, data_handler, portfolio):
        self.events = events
        self.config = load_config()

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list
        self.portfolio = portfolio

        self.counter = 0

        self.bars_window = 200
        self.rsi_window = 14
        self.div_window = 100

        self.ma_short = 10
        self.ma_long = 50

        self.telegram = TelegramBot(
            bot_token=self.config['telegram']['bot_token'],
            channel_id=self.config['telegram']['channel_id'])

    def calculate_signals(self):
        for symbol in self.symbol_list:
            print(f'Searching for {symbol} signals ...')
            timestamps = self.data_handler.get_latest_bars_values(
                symbol, 'datetime', N=self.bars_window)

            highs = self.data_handler.get_latest_bars_values(
                symbol, 'high', N=self.bars_window)

            lows = self.data_handler.get_latest_bars_values(
                symbol, 'low', N=self.bars_window)

            closes = self.data_handler.get_latest_bars_values(
                symbol, 'close', N=self.bars_window)

            signal_timestamp = timestamps[-1]

            rsi = RSI(closes, timeperiod=self.rsi_window)

            ma_short = EMA(closes, timeperiod=self.ma_short)[-1]
            ma_long = EMA(closes, timeperiod=self.ma_long)[-1]

            # Buy Signal conditions
            if ma_short < ma_long:
                print(f'{symbol}: Short-term bearish')

                bullish_div = bull_div(
                    lows,
                    rsi,
                    timestamps,
                    window=self.div_window,
                    price_prominence=ma_long*0.001,
                )

                if bullish_div and len(bullish_div) > 1:
                    div_type = 'BULLISH DIV'
                    print(
                        f'{symbol} - {div_type}: {signal_timestamp}')

                    self.telegram.send_text({
                        'symbol': symbol,
                        'div_type': div_type,
                        'peaks': bullish_div
                    })

            elif ma_short > ma_long:
                print(f'{symbol}: Short-term bullish')

                bearish_div = bear_div(
                    highs,
                    rsi,
                    timestamps,
                    window=self.div_window,
                    price_prominence=ma_long*0.001,
                )

                if bearish_div and len(bearish_div) > 1:
                    div_type = 'BEARISH DIV'
                    print(
                        f'{symbol} - {div_type}: {signal_timestamp}')

                    self.telegram.send_text({
                        'symbol': symbol,
                        'div_type': div_type,
                        'peaks': bearish_div
                    })
