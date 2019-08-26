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


def detect_div_v0(price_set, rsi_set, nwindow=5, price_pk_prominence=40, rsi_pk_prominence=2):
    from scipy.signal import find_peaks
    # calculating peaks indices
    peaks_price, _ = find_peaks(price_set, prominence=price_pk_prominence)
    peaks_rsi, _ = find_peaks(rsi_set, prominence=rsi_pk_prominence)
    # calculating negative peaks indices
    npeaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    npeaks_rsi, _ = find_peaks(-rsi_set, prominence=rsi_pk_prominence)

    d = dict()
    # defining window size
    n_window = nwindow

    # Detecting bearish divergences
    bearish_div = list()
    bullish_div = list()
    ref_price = list()  # positive peaks in price
    ref_rsi = list()  # positive peaks in rsi
    nref_price = list()  # negative peaks in price
    nref_rsi = list()  # negative peaks in rsi

    for ni, nitem in enumerate(npeaks_price):
        nref_price.append(price_set[nitem])
        nref_rsi.append(rsi_set[nitem])
        for nj in range(ni-1, 0, -1):
            # print(ni,nj,ni-nj)
            if nj == ni-n_window+1:
                break
            if (nref_price[ni]-nref_price[nj]) <= 0 and (nref_rsi[ni]-nref_rsi[nj]) >= 0:
                # bullish_div.append([npeaks_price[ni],npeaks_price[nj]])
                return "bull"

    for i, item in enumerate(peaks_price):
        ref_price.append(price_set[item])
        ref_rsi.append(rsi_set[item])
        for j in range(i-1, 0, -1):
            # print(i,j,i-j)
            if j == i-n_window+1:
                break
            if (ref_price[i]-ref_price[j]) >= 0 and (ref_rsi[i]-ref_rsi[j]) <= 0:
                # bearish_div.append([peaks_price[i],peaks_price[j]])
                return "bear"

def detect_div_v1(price_set, rsi_set, nwindow=5, price_pk_prominence=40, rsi_pk_prominence=2):
    from scipy.signal import find_peaks
    # calculating peaks indices
    peaks_price, _ = find_peaks(price_set, prominence=price_pk_prominence)
    peaks_rsi, _ = find_peaks(rsi_set, prominence=rsi_pk_prominence)
    # calculating negative peaks indices
    npeaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    npeaks_rsi, _ = find_peaks(-rsi_set, prominence=rsi_pk_prominence)

    # defining window size
    n_window = nwindow

    # Detecting bearish divergences
    bearish_div = list()
    bullish_div = list()
    ref_price = list()  # positive peaks in price
    ref_rsi = list()  # positive peaks in rsi
    nref_price = list()  # negative peaks in price
    nref_rsi = list()  # negative peaks in rsi

    for ni, nitem in enumerate(npeaks_price):
        nref_price.append(price_set[nitem])
        nref_rsi.append(rsi_set[nitem])
    
    for nj in range(len(nref_price)):
        # print(ni,nj,ni-nj)
        if (price_set[-1]-nref_price[nj]) <= 0 and (rsi_set[-1]-nref_rsi[nj]) >= 0:
            #bullish_div.append([npeaks_price[ni],npeaks_price[nj]])
            return "bull"


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
