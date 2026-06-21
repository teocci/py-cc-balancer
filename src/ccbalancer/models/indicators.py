'''Indicator snapshot model.

A :class:`IndicatorSnapshot` is the computed view of one pair on one timeframe:
the latest value of each indicator over the candles available at snapshot time.
It is the market-intelligence counterpart to :class:`PairSnapshot` and feeds the
``analyze`` command's JSON contract.
'''

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ['IndicatorSnapshot']


@dataclass(slots=True, frozen=True)
class IndicatorSnapshot:
    '''Latest indicator values for one pair on one timeframe.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        timeframe: ccxt timeframe (e.g. ``'1h'``).
        as_of: UTC ISO-8601 open time of the newest candle used.
        candle_count: Number of candles the indicators were computed over.
        stale: Whether the candles came from a stale-cache/offline fallback.
        close: Latest close price.
        rsi: Latest RSI, or ``None`` if insufficient history.
        macd: Latest MACD line value, or ``None``.
        macd_signal: Latest MACD signal value, or ``None``.
        macd_histogram: Latest MACD histogram value, or ``None``.
        rsi_overbought: Configured RSI overbought threshold (for interpretation).
        rsi_oversold: Configured RSI oversold threshold (for interpretation).
        rsi_zone: Deterministic zone vs thresholds (``overbought``/``oversold``/
            ``neutral``), or ``None`` if RSI is unavailable. A fact, not advice.
        ema: Period (as string) -> latest EMA value, omitting periods with no value.
        bollinger_upper: Latest upper Bollinger band, or ``None``.
        bollinger_middle: Latest middle Bollinger band, or ``None``.
        bollinger_lower: Latest lower Bollinger band, or ``None``.
        atr: Latest ATR, or ``None``.
        volume: Latest candle volume, or ``None``.
        volume_ma: Latest volume moving average, or ``None``.
        fib: Fibonacci ratio (as string) -> price over the candle window.
    '''

    symbol: str
    timeframe: str
    as_of: str
    candle_count: int
    stale: bool
    close: float
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    rsi_overbought: float | None = None
    rsi_oversold: float | None = None
    rsi_zone: str | None = None
    ema: dict[str, float] = field(default_factory=dict)
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    atr: float | None = None
    volume: float | None = None
    volume_ma: float | None = None
    fib: dict[str, float] = field(default_factory=dict)
