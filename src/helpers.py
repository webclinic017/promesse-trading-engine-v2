import numpy as np


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
