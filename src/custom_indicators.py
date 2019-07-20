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
