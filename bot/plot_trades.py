import matplotlib.pyplot as plt
import pandas as pd

from time import time
from datetime import datetime

from pathlib import Path
from helpers import load_config, parse_ticker, parse_trades

import talib


def plot_trades(ticker, trades, *indicators):
    fig, axes = plt.subplots(2, 1)
    axes[0].plot(ticker.index, ticker['close'])
    axes[0].plot(trades['open_date'], trades['open_market_price'],
                 marker='^', markersize=10, color='g', linestyle='None')
    axes[0].plot(trades['close_date'], trades['close_market_price'],
                 'v', markersize=10, color='r', linestyle='None')

    axes[1] = axes[0].twinx()
    axes[1].plot(ticker.index, indicators[0](
        ticker['close']), linewidth=1, color='r', alpha=0.4)
    plt.show()


if __name__ == '__main__':
    config = load_config()
    timeframe = config['timeframe']
    tickers = ['-'.join(symbol.split('/'))
               for symbol in config['symbol_list']]

    trades_path = f'{Path().absolute()}/backtest_results/trades.csv'
    ticker_path = f'{Path().absolute()}/exchange_data/{tickers[0]}_{timeframe}.csv'

    trades = parse_trades(trades_path)
    ticker = parse_ticker(ticker_path)

    plot_trades(ticker, trades, talib.RSI)


# import plotly as py
# import plotly.graph_objs as go
# import ipywidgets as widgets
# import pandas as pd
# from pathlib import Path
# from helpers import load_config, parse_ticker, parse_trades

# import talib


# def plot_trades(ticker, trades, *indicators):
#     layout = go.Layout(
#         title='BTC/USDT',
#         xaxis=dict(title='Date', anchor='y2'),
#         yaxis=dict(title='Price', anchor='x'),
#         yaxis2=dict(title='RSI', anchor='x')
#     )

#     trace1 = go.Scatter(
#         x=ticker.index,
#         y=ticker['close'],
#         mode='lines',
#         name='price',
#         line=dict(
#             shape='spline'
#         ),
#         xaxis="x",
#         yaxis="y"
#     )


# if __name__ == '__main__':
#     config = load_config()
#     timeframe = config['timeframe']
#     tickers = ['-'.join(symbol.split('/'))
#                for symbol in config['symbol_list']]

#     trades_path = f'{Path().absolute()}/backtest_results/trades.csv'
#     ticker_path = f'{Path().absolute()}/exchange_data/{tickers[0]}_{timeframe}.csv'

#     trades = parse_trades(trades_path)
#     ticker = parse_ticker(ticker_path)

#     plot_trades(ticker, trades, talib.RSI)
