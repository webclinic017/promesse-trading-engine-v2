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

        returns = (current_price / open_price) - 1
        current_trailing = 0.0

        if returns >= pct_tp:
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


def detect_bull_div(price_set, rsi_set, price_pk_prominence):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]  # positive peaks in price
    ref_rsi = [rsi_set[item]
               for item in peaks_price]  # positive peaks in rsi
    counter = 0

    for i in range(len(ref_price)):
        if (price_set[-1]-ref_price[i]) <= 0 and (rsi_set[-1]-ref_rsi[i]) >= 0:
            counter += 1

        if counter == 2:
            return "bull"

    return None


def detect_bear_div(price_set, rsi_set, price_pk_prominence):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]  # positive peaks in price
    ref_rsi = [rsi_set[item]
               for item in peaks_price]  # positive peaks in rsi

    counter = 0

    for i in range(len(ref_price)):
        if (price_set[-1]-ref_price[i]) >= 0 and (rsi_set[-1]-ref_rsi[i]) <= 0:
            counter += 1
        if counter == 2:
            return "bear"

    return None


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


def detect_h_bull_div(price_set, rsi_set, price_pk_prominence):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]  # positive peaks in price
    ref_rsi = [rsi_set[item]
               for item in peaks_price]  # positive peaks in rsi
    counter = 0

    for i in range(len(ref_price)):
        if (price_set[-1]-ref_price[i]) >= 0 and (rsi_set[-1]-ref_rsi[i]) <= 0:
            counter += 1

        if counter == 2:
            return "hbull"

    return None


def detect_h_bear_div(price_set, rsi_set, price_pk_prominence):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]  # positive peaks in price
    ref_rsi = [rsi_set[item]
               for item in peaks_price]  # positive peaks in rsi

    counter = 0

    for i in range(len(ref_price)):
        if (price_set[-1]-ref_price[i]) <= 0 and (rsi_set[-1]-ref_rsi[i]) >= 0:
            counter += 1
        if counter == 2:
            return "hbear"

    return None