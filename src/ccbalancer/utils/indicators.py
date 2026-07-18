'''Pure technical-indicator math over candle data.

Hand-rolled (no ``TA-Lib`` C dependency) so the bundle stays portable. Every
function is deterministic and exchange-agnostic: it knows nothing about which
exchange supplied the candles. Series functions return a list aligned to the
input length, with ``None`` in the leading positions that lack enough history;
this keeps results composable (e.g. MACD is an EMA of an EMA) and lets tests
assert values at specific indices.

The default periods live in :mod:`ccbalancer.constants`; callers may override
them. ``fib_levels`` is a stateless mapping of swing-high/low to retracements.
'''

from __future__ import annotations

from statistics import pstdev

from ccbalancer import constants as c

__all__ = [
    'sma', 'ema', 'rsi', 'macd', 'bollinger', 'atr', 'adx', 'support_resistance',
    'fib_levels', 'last_value',
]


def sma(values: list[float], period: int) -> list[float | None]:
    '''Simple moving average over a trailing window of ``period`` values.

    Returns a list aligned to ``values``; entries before index ``period - 1``
    are ``None``. Used for the volume moving average.
    '''
    if period <= 0:
        raise ValueError(f'SMA period must be positive, got {period}')
    out: list[float | None] = [None] * len(values)
    for index in range(period - 1, len(values)):
        out[index] = sum(values[index - period + 1: index + 1]) / period
    return out

# A series value is a float once enough history exists, otherwise ``None``.
Series = 'list[float | None]'


def ema(values: list[float], period: int) -> list[float | None]:
    '''Exponential moving average, seeded with the SMA of the first ``period``.

    Args:
        values: Source series (typically closes).
        period: Smoothing window; must be positive.

    Returns:
        A list aligned to ``values``; entries before index ``period - 1`` are
        ``None``.
    '''
    if period <= 0:
        raise ValueError(f'EMA period must be positive, got {period}')
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    multiplier = 2 / (period + 1)
    previous = sum(values[:period]) / period
    out[period - 1] = previous
    for index in range(period, len(values)):
        previous = values[index] * multiplier + previous * (1 - multiplier)
        out[index] = previous
    return out


def rsi(values: list[float], period: int = c.DEFAULT_RSI_PERIOD) -> list[float | None]:
    '''Relative Strength Index using Wilder's smoothing.

    Returns a list aligned to ``values``; the first valid value is at index
    ``period``.
    '''
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains, losses = _gains_losses(values)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for index in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[index - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[index - 1]) / period
        out[index] = _rsi_value(avg_gain, avg_loss)
    return out


def macd(
    values: list[float],
    fast: int = c.DEFAULT_MACD_FAST,
    slow: int = c.DEFAULT_MACD_SLOW,
    signal: int = c.DEFAULT_MACD_SIGNAL,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    '''Moving Average Convergence Divergence.

    Returns:
        ``(macd_line, signal_line, histogram)``, each aligned to ``values``.
    '''
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line = [_diff(f, s) for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema_optional(macd_line, signal)
    histogram = [_diff(m, sg) for m, sg in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def bollinger(
    values: list[float],
    period: int = c.DEFAULT_BOLLINGER_PERIOD,
    num_std: float = c.DEFAULT_BOLLINGER_STDDEV,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    '''Bollinger Bands using a population standard deviation.

    Returns:
        ``(upper, middle, lower)``, each aligned to ``values``.
    '''
    upper: list[float | None] = [None] * len(values)
    middle: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)
    for index in range(period - 1, len(values)):
        window = values[index - period + 1: index + 1]
        mean = sum(window) / period
        deviation = pstdev(window)
        middle[index] = mean
        upper[index] = mean + num_std * deviation
        lower[index] = mean - num_std * deviation
    return upper, middle, lower


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = c.DEFAULT_ATR_PERIOD,
) -> list[float | None]:
    '''Average True Range using Wilder's smoothing.

    Returns a list aligned to ``closes``; the first valid value is at index
    ``period``.
    '''
    count = len(closes)
    out: list[float | None] = [None] * count
    if count <= period:
        return out
    true_ranges = _true_ranges(highs, lows, closes)
    previous = sum(true_ranges[1: period + 1]) / period
    out[period] = previous
    for index in range(period + 1, count):
        previous = (previous * (period - 1) + true_ranges[index]) / period
        out[index] = previous
    return out


def adx(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = c.DEFAULT_ADX_PERIOD,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    '''Average Directional Index with +DI/-DI, all using Wilder smoothing.

    Args:
        highs: Candle highs.
        lows: Candle lows.
        closes: Candle closes (defines the output length).
        period: Wilder lookback; must be positive.

    Returns:
        ``(adx, plus_di, minus_di)``, each aligned to ``closes``. ``+DI``/``-DI``
        have their first value at index ``period``; ``adx`` at index
        ``2 * period - 1``. Leading positions are ``None``.
    '''
    if period <= 0:
        raise ValueError(f'ADX period must be positive, got {period}')
    count = len(closes)
    plus_di: list[float | None] = [None] * count
    minus_di: list[float | None] = [None] * count
    adx_series: list[float | None] = [None] * count
    if count < 2 * period:
        return adx_series, plus_di, minus_di
    smoothed_tr = _wilder_smooth(_true_ranges(highs, lows, closes), period)
    plus_dm, minus_dm = _directional_movement(highs, lows)
    smoothed_plus = _wilder_smooth(plus_dm, period)
    smoothed_minus = _wilder_smooth(minus_dm, period)
    dx: list[float | None] = [None] * count
    for index in range(period, count):
        plus_di[index] = _directional_index(smoothed_plus[index], smoothed_tr[index])
        minus_di[index] = _directional_index(smoothed_minus[index], smoothed_tr[index])
        dx[index] = _dx_value(plus_di[index], minus_di[index])
    _fill_adx(adx_series, dx, period)
    return adx_series, plus_di, minus_di


def support_resistance(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    lookback: int = c.DEFAULT_SR_PIVOT_LOOKBACK,
    cluster_pct: float = c.DEFAULT_SR_CLUSTER_PCT,
    max_levels: int = c.DEFAULT_SR_MAX_LEVELS,
) -> tuple[list[float], list[float]]:
    '''Support/resistance price levels from clustered fractal swing pivots.

    A pivot high is a bar whose high tops the ``lookback`` bars on each side; a
    pivot low is the symmetric bottom on lows. Pivots within ``cluster_pct``
    percent of one another merge into a single averaged level. Levels below the
    latest close are supports, at/above it are resistances.

    Args:
        highs: Candle highs.
        lows: Candle lows.
        closes: Candle closes (the last one splits supports from resistances).
        lookback: Bars of confirmation required on each side of a pivot.
        cluster_pct: Percent tolerance that merges nearby pivots.
        max_levels: Cap on levels returned per side.

    Returns:
        ``(supports, resistances)``, each ordered nearest-to-``close`` first and
        capped at ``max_levels``.
    '''
    if lookback <= 0:
        raise ValueError(f'S/R lookback must be positive, got {lookback}')
    if not closes:
        return [], []
    levels = _cluster_levels(_swing_pivots(highs, lows, lookback), cluster_pct)
    close = closes[-1]
    supports = sorted((lv for lv in levels if lv < close), key=lambda price: close - price)
    resistances = sorted((lv for lv in levels if lv >= close), key=lambda price: price - close)
    return supports[:max_levels], resistances[:max_levels]


def fib_levels(high: float, low: float) -> dict[str, float]:
    '''Fibonacci retracement levels between a swing ``high`` and ``low``.

    Ratio ``0`` maps to ``high`` and ``1`` to ``low``; keys are the ratios as
    strings (e.g. ``'0.618'``).
    '''
    span = high - low
    return {f'{ratio:g}': high - span * ratio for ratio in c.FIB_RATIOS}


def last_value(series: list[float | None]) -> float | None:
    '''Return the most recent non-``None`` value of a series, or ``None``.'''
    for value in reversed(series):
        if value is not None:
            return value
    return None


def _gains_losses(values: list[float]) -> tuple[list[float], list[float]]:
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    return gains, losses


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _true_ranges(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    true_ranges = [highs[0] - lows[0]]
    for index in range(1, len(closes)):
        previous_close = closes[index - 1]
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - previous_close),
                abs(lows[index] - previous_close),
            )
        )
    return true_ranges


def _directional_movement(highs: list[float], lows: list[float]) -> tuple[list[float], list[float]]:
    '''Wilder +DM/-DM per bar, aligned to input; index 0 is ``0.0`` (no prior bar).'''
    plus = [0.0] * len(highs)
    minus = [0.0] * len(highs)
    for index in range(1, len(highs)):
        up_move = highs[index] - highs[index - 1]
        down_move = lows[index - 1] - lows[index]
        plus[index] = up_move if up_move > down_move and up_move > 0 else 0.0
        minus[index] = down_move if down_move > up_move and down_move > 0 else 0.0
    return plus, minus


def _wilder_smooth(values: list[float], period: int) -> list[float | None]:
    '''Wilder running sum aligned to ``values``; first sum at index ``period`` over 1..period.'''
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    running = sum(values[1: period + 1])
    out[period] = running
    for index in range(period + 1, len(values)):
        running = running - running / period + values[index]
        out[index] = running
    return out


def _directional_index(smoothed_dm: float | None, smoothed_tr: float | None) -> float:
    if not smoothed_tr:
        return 0.0
    return 100.0 * smoothed_dm / smoothed_tr


def _dx_value(plus_di: float, minus_di: float) -> float:
    total = plus_di + minus_di
    if total == 0:
        return 0.0
    return 100.0 * abs(plus_di - minus_di) / total


def _fill_adx(adx_series: list[float | None], dx: list[float | None], period: int) -> None:
    '''Seed ADX with the mean of the first ``period`` DX values, then Wilder-average.'''
    first = 2 * period - 1
    if first >= len(dx):
        return
    previous = sum(dx[period: first + 1]) / period
    adx_series[first] = previous
    for index in range(first + 1, len(dx)):
        previous = (previous * (period - 1) + dx[index]) / period
        adx_series[index] = previous


def _swing_pivots(highs: list[float], lows: list[float], lookback: int) -> list[float]:
    '''Fractal pivot prices: highs that top their neighbours, lows that bottom theirs.'''
    pivots: list[float] = []
    for index in range(lookback, len(highs) - lookback):
        window = range(index - lookback, index + lookback + 1)
        if _is_pivot_high(highs, index, window):
            pivots.append(highs[index])
        if _is_pivot_low(lows, index, window):
            pivots.append(lows[index])
    return pivots


def _is_pivot_high(highs: list[float], index: int, window: range) -> bool:
    return (all(highs[index] >= highs[j] for j in window)
            and any(highs[index] > highs[j] for j in window))


def _is_pivot_low(lows: list[float], index: int, window: range) -> bool:
    return (all(lows[index] <= lows[j] for j in window)
            and any(lows[index] < lows[j] for j in window))


def _cluster_levels(pivots: list[float], cluster_pct: float) -> list[float]:
    '''Merge sorted pivots within ``cluster_pct`` percent into averaged levels.'''
    levels: list[float] = []
    for price in sorted(pivots):
        if levels and _within_pct(price, levels[-1], cluster_pct):
            levels[-1] = (levels[-1] + price) / 2
        else:
            levels.append(price)
    return levels


def _within_pct(price: float, reference: float, pct: float) -> bool:
    if reference == 0:
        return price == 0
    return abs(price - reference) / abs(reference) * 100.0 <= pct


def _ema_optional(series: list[float | None], period: int) -> list[float | None]:
    '''Run :func:`ema` over the contiguous non-``None`` tail of ``series``.'''
    start = next((i for i, value in enumerate(series) if value is not None), None)
    if start is None:
        return [None] * len(series)
    tail = [value for value in series[start:] if value is not None]
    smoothed = ema(tail, period)
    out: list[float | None] = [None] * len(series)
    out[start:] = smoothed
    return out


def _diff(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right
