import numpy as np
import pandas as pd


def find_pos_price(price, price_set):
    return len(price_set) - np.where(price_set == price)[0][0]


def BULL_DIV_2(price_set, rsi_set, price_pk_prominence=10):
    from scipy.signal import find_peaks
    from math import floor

    peaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]
    ref_rsi = [rsi_set[item]
               for item in peaks_price]

    latest_price = price_set[-1]
    latest_rsi = rsi_set[-1]
    latest_peak_price = None
    latest_peak_rsi = None
    latest_peak_pos = None
    is_div = False

    local_min = None
    counter = 0

    for i in range(len(ref_price)-1, 0, -1):
        if floor(latest_price) < floor(ref_price[i]) and floor(latest_rsi) > floor(ref_rsi[i]):
            latest_peak_price = ref_price[i]
            latest_peak_rsi = ref_rsi[i]
            latest_peak_pos = find_pos_price(latest_peak_price, price_set)
            counter += 1
            is_div = True

            # Check for a local min between the 2 detected peaks
            for j in range(latest_peak_pos-1, 1, -1):
                if latest_price > price_set[-j]:
                    local_min = price_set[-j]
                    is_div = False
                    counter = 0
                    break

    return {
        'is_div': is_div,
        'price_peaks': (price_set[-1], latest_peak_price),
        'rsi_peaks': (rsi_set[-1], latest_peak_rsi),
        'local_min': local_min,
        'nb_div': counter
    }


def BULL_DIV(price_set, rsi_set, price_pk_prominence, window=1):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]
    ref_rsi = [rsi_set[item]
               for item in peaks_price]

    counter = 0
    for i in range(len(ref_price)-1, 0, -1):
        if price_set[-1] < ref_price[i] and rsi_set[-1] > ref_rsi[i]:
            counter += 1
            latest_peak_price = ref_price[i]
            latest_peak_rsi = ref_rsi[i]

        if counter == window:
            return {
                'is_div': True,
                'price_peaks': (price_set[-1], latest_peak_price),
                'rsi_peaks': (rsi_set[-1], latest_peak_rsi)
            }
    return False


def BEAR_DIV(price_set, rsi_set, price_pk_prominence, window=2):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]
    ref_rsi = [rsi_set[item]
               for item in peaks_price]

    counter = 0

    for i in range(len(ref_price)-1, 0, -1):
        if (ref_price[-1]-ref_price[i]) >= 0 and (ref_rsi[-1]-ref_rsi[i]) <= 0:
            counter += 1

        if counter == window:
            return "bear", ref_price[-1], ref_rsi[-1]

    return None, 0, 0


def HBULL_DIV(price_set, rsi_set, price_pk_prominence, window=2):
    from scipy.signal import find_peaks

    peaks_price, _ = find_peaks(-price_set, prominence=price_pk_prominence)
    ref_price = [price_set[item]
                 for item in peaks_price]  # positive peaks in price
    ref_rsi = [rsi_set[item]
               for item in peaks_price]  # positive peaks in rsi
    counter = 0

    for i in range(len(ref_price)-1, 0, -1):
        if (ref_price[-1]-ref_price[i]) >= 0 and (ref_rsi[-1]-ref_rsi[i]) <= 0:
            counter += 1

        if counter == window:
            return "hbull", ref_price[-1]

    return None, 0


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
