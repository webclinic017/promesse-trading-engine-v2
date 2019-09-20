import numpy as np
import pandas as pd
from pathlib import Path
import json


def load_config():
    config_path = f'{Path().absolute()}/bot/config.json'

    with open(config_path) as f:
        config = json.load(f)
    return config


def parse_trades(filepath):
    trades = pd.read_csv(filepath, header=0,
                         parse_dates=True, index_col=0)
    trades['open_date'] = pd.to_datetime(trades['open_date'])
    trades['close_date'] = pd.to_datetime(trades['close_date'])

    return trades


def parse_ticker(filepath):
    columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    ticker = pd.read_csv(filepath,
                         header=None, index_col=0, names=columns)
    ticker.index = pd.to_datetime(ticker.index, unit='ms')
    ticker = ticker.drop_duplicates()

    return ticker


def init_trailing_long(open_price, pct_sl, pct_tp):
    trailing = open_price*(1-pct_sl)

    def update_sl(current_price):
        nonlocal trailing
        nonlocal pct_sl

        returns = (current_price / open_price) - 1
        current_trailing = 0.0

        if returns >= pct_tp:
            pct_sl = pct_sl / 1
            current_trailing = current_price*(1-pct_sl)

        trailing = max(trailing, current_trailing)

        return trailing

    return update_sl


def init_trailing_short(open_price, pct_sl, pct_tp):
    trailing = open_price*(1+pct_sl)

    def update_sl(current_price):
        nonlocal trailing

        returns = (open_price / current_price) - 1
        current_trailing = trailing

        if returns >= pct_tp:
            current_trailing = current_price*(1+pct_sl)

        trailing = min(trailing, current_trailing)

        return trailing
    return update_sl


def init_trailing(open_price, pct_sl, pct_tp, direction):
    if direction == 'LONG':
        return init_trailing_long(open_price, pct_sl, pct_tp)
    else:
        return init_trailing_short(open_price, pct_sl, pct_tp)


def stop_loss(open_price, pct_sl):
    return open_price*(1-pct_sl)


def get_prev_daily_hlc(timeframe, latest_datetimes, latest_highs, latest_lows, latest_closes):
    """
    Returns previous daily HLC data
    """
    current_hour = latest_datetimes[-1].hour
    current_minute = latest_datetimes[-1].minute

    i = 0
    j = 0

    if timeframe == '1h':
        i = 1
        j = 1
    elif timeframe == '30m':
        i = 2
        if current_minute <= 0:
            j = 1
        else:
            j = 2
    elif timeframe == '15m':
        i = 4
        if current_minute == 15:
            j = 2
        elif current_minute == 30:
            j = 3
        elif current_minute == 45:
            j = 4
        else:
            j = 1

    start = -(i * (current_hour + 24) + j)
    end = -(i * current_hour + j)

    daily_high = latest_highs[start:end].max()
    daily_low = latest_lows[start:end].min()
    daily_close = latest_closes[start:end][-1]

    return daily_high, daily_low, daily_close


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


def get_day_of_week(dt):
    import pendulum
    dt = pendulum.parse(dt.isoformat())
    dt_w = dt.start_of('week')
    date_w_str = f'{dt_w.year}-{dt_w.month}-{dt_w.day}'

    return date_w_str
