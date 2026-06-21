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

__all__ = ['sma', 'ema', 'rsi', 'macd', 'bollinger', 'atr', 'fib_levels', 'last_value']


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
