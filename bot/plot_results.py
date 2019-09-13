import numpy as np
import pandas as pd

from datetime import datetime

from pathlib import Path

import talib

from math import *

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def open_ticker_csv(ticker_name: str, timeframe: str, directory: str) -> pd.DataFrame:
    ticker_name = '-'.join(ticker_name.split('/'))
    ticker_name = f'{ticker_name}_{timeframe}' if timeframe else f'{ticker_name}'
    ticker_path = f'{directory}/{ticker_name}.csv'
    columns_names = ('timestamp', 'open', 'high', 'low', 'close', 'volume')

    ticker = pd.read_csv(ticker_path,
                         index_col=0,
                         header=None,
                         names=columns_names)

    return ticker


def clean_ticker(ticker: pd.DataFrame) -> pd.DataFrame:
    ticker_copy = ticker.copy()
    ticker_copy.index = pd.to_datetime(ticker_copy.index, unit='ms')
    ticker_copy = ticker_copy.drop_duplicates().sort_index()

    return ticker_copy


data = open_ticker_csv('BTC/USDT', '15m', 'exchange_data')
data = clean_ticker(data)
hlc3 = (data['high'] + data['low'] + data['close']) / 3
rsi = talib.RSI(hlc3, timeperiod=14)

start_date = '2017-11-17 00:00:00'
end_date = '2019-11-25 00:00:00'
mask = (data.index >= start_date) & (data.index <= end_date)
data = data.loc[mask]


fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    specs=[[{"type": "candlestick"}],
           [{"type": "scatter"}]]
)

fig.add_trace(
    go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close']
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=data.index,
        y=rsi,
        mode="lines",
        name="RSI"
    ),
    row=2, col=1
)


fig.update_layout(
    height=800,
    showlegend=False,
    title_text="BTC/USDT",
)

fig.show()
