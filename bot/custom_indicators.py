import numpy as np
import pandas as pd


def BULL_DIV(price_set, rsi_set, price_pk_prominence, window=2):
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

        if counter == window:
            return "bull"

    return None


def BEAR_DIV(price_set, rsi_set, price_pk_prominence, window=2):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]
    ref_rsi = [rsi_set[item]
               for item in peaks_price]

    for i in range(len(ref_price)-1, 0, -1):
        if price_set[-1] > ref_price[i] and rsi_set[-1] < ref_rsi[i]:
            return 'bear'


def HBULL_DIV(price_set, rsi_set, price_pk_prominence, window=2):
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

        if counter == window:
            return "hbull"

    return None


def HBEAR_DIV(price_set, rsi_set, price_pk_prominence, window=2):
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
        if counter == window:
            return "hbear"

    return None


def PPSR(high, low, close):
    """
    It calculates Pivot Point Indicator
    It should receive Daily OHLCV bar
    It returns a dictionnary with calculated values of PP, R1, R2, R3, S1, S2 and S3.
    """

    pp = (high + low + close) / 3

    s1 = pp - (0.382 * (high - low))
    s2 = pp - (0.618 * (high - low))
    s3 = pp - (1 * (high - low))

    r1 = pp + (0.382 * (high - low))
    r2 = pp + (0.618 * (high - low))
    r3 = pp + (1 * (high - low))

    return pp, s1, s2, s3, r1, r2, r3


def crossed(series1, series2, direction=None):
    if isinstance(series1, np.ndarray):
        series1 = pd.Series(series1)

    if isinstance(series2, (float, int, np.ndarray)):
        series2 = pd.Series(index=series1.index, data=series2)

    if direction is None or direction == "above":
        above = pd.Series((series1 > series2) & (
            series1.shift(1) <= series2.shift(1)))

    if direction is None or direction == "below":
        below = pd.Series((series1 < series2) & (
            series1.shift(1) >= series2.shift(1)))

    if direction is None:
        return above or below

    return above if direction == "above" else below


def crossed_above(series1, series2):
    return crossed(series1, series2, "above")


def crossed_below(series1, series2):
    return crossed(series1, series2, "below")
