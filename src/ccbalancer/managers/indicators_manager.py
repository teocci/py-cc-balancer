'''Compute multi-timeframe indicator snapshots from OHLCV.

This is the read-side orchestrator for market intelligence: it obtains candles
for a pair and timeframe (a fresh cache hit, an exchange refetch, or a stale
offline fallback), runs the pure indicator math, and assembles an immutable
:class:`IndicatorSnapshot`. It delegates all network access to the injected
exchange store and all caching to the injected market cache, and never imports
ccxt itself.

Resolution order per timeframe:

1. Fresh cached candles -> use them (no network).
2. Otherwise refetch from the data exchange and rewrite the cache.
3. If the exchange is unreachable, fall back to stale cache (flagged ``stale``),
   unless ``require_fresh`` forbids it.
4. If no usable candles remain, return ``None`` for that timeframe.
'''

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ccbalancer import constants as c
from ccbalancer.config import IndicatorSettings
from ccbalancer.exceptions import ExchangeError
from ccbalancer.models import IndicatorSnapshot
from ccbalancer.utils import indicators
from ccbalancer.utils.timeutil import ms_to_iso, now_ms

if TYPE_CHECKING:
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.market_cache import MarketCache

__all__ = ['IndicatorsManager']

# ccxt candle field positions: [time, open, high, low, close, volume].
_HIGH, _LOW, _CLOSE, _VOLUME = 2, 3, 4, 5


@dataclass(slots=True)
class IndicatorsManager:
    '''Builds :class:`IndicatorSnapshot` objects from cached/live OHLCV.

    Attributes:
        exchange: Data-exchange store providing ``fetch_ohlcv``.
        cache: Cache for candles, used on hit and as an offline fallback.
        ohlcv_limit: Number of candles requested per timeframe.
        settings: Indicator parameters and thresholds applied to each snapshot.
    '''

    exchange: ExchangeStore
    cache: MarketCache
    ohlcv_limit: int = c.DEFAULT_OHLCV_LIMIT
    settings: IndicatorSettings = field(default_factory=IndicatorSettings)

    def snapshot(
        self,
        symbol: str,
        timeframe: str,
        *,
        require_fresh: bool = False,
        at_ms: int | None = None,
    ) -> IndicatorSnapshot | None:
        '''Build a snapshot for one pair/timeframe, or ``None`` if no data.'''
        loaded = self._load(symbol, timeframe, require_fresh, at_ms)
        if loaded is None:
            return None
        candles, stale = loaded
        return self._build(symbol, timeframe, candles, stale)

    def snapshots(
        self,
        symbol: str,
        timeframes: list[str],
        *,
        require_fresh: bool = False,
        at_ms: int | None = None,
    ) -> list[IndicatorSnapshot | None]:
        '''Build snapshots for many timeframes, preserving order (``None`` per gap).'''
        return [
            self.snapshot(symbol, tf, require_fresh=require_fresh, at_ms=at_ms)
            for tf in timeframes
        ]

    def _load(
        self,
        symbol: str,
        timeframe: str,
        require_fresh: bool,
        at_ms: int | None,
    ) -> tuple[list[list[float]], bool] | None:
        moment = at_ms if at_ms is not None else now_ms()
        cached = self.cache.read(symbol, timeframe)
        if cached and self.cache.is_fresh(cached, timeframe, moment):
            return cached, False
        fetched = self._try_fetch(symbol, timeframe)
        if fetched:
            self.cache.write(symbol, timeframe, fetched)
            return fetched, False
        if require_fresh or not cached:
            return None
        return cached, True

    def _try_fetch(self, symbol: str, timeframe: str) -> list[list[float]] | None:
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, self.ohlcv_limit)
        except ExchangeError:
            return None

    def _build(
        self,
        symbol: str,
        timeframe: str,
        candles: list[list[float]],
        stale: bool,
    ) -> IndicatorSnapshot:
        s = self.settings
        closes = [candle[_CLOSE] for candle in candles]
        highs = [candle[_HIGH] for candle in candles]
        lows = [candle[_LOW] for candle in candles]
        volumes = [candle[_VOLUME] for candle in candles]
        rsi = indicators.last_value(indicators.rsi(closes, s.get('rsi', 'period')))
        macd_line, signal_line, histogram = indicators.macd(
            closes, s.get('macd', 'fast'), s.get('macd', 'slow'), s.get('macd', 'signal')
        )
        upper, middle, lower = indicators.bollinger(
            closes, s.get('bollinger', 'period'), s.get('bollinger', 'stddev')
        )
        return IndicatorSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            as_of=ms_to_iso(int(candles[-1][0])),
            candle_count=len(candles),
            stale=stale,
            close=closes[-1],
            rsi=rsi,
            macd=indicators.last_value(macd_line),
            macd_signal=indicators.last_value(signal_line),
            macd_histogram=indicators.last_value(histogram),
            rsi_overbought=s.get('rsi', 'overbought'),
            rsi_oversold=s.get('rsi', 'oversold'),
            rsi_zone=self._rsi_zone(rsi),
            ema=self._ema_map(closes),
            bollinger_upper=indicators.last_value(upper),
            bollinger_middle=indicators.last_value(middle),
            bollinger_lower=indicators.last_value(lower),
            atr=indicators.last_value(indicators.atr(highs, lows, closes, s.get('atr', 'period'))),
            volume=volumes[-1] if volumes else None,
            volume_ma=indicators.last_value(indicators.sma(volumes, s.get('volume', 'ma_period'))),
            fib=indicators.fib_levels(max(highs), min(lows)),
        )

    def _ema_map(self, closes: list[float]) -> dict[str, float]:
        result: dict[str, float] = {}
        for period in self.settings.get('ema', 'periods'):
            value = indicators.last_value(indicators.ema(closes, period))
            if value is not None:
                result[str(period)] = value
        return result

    def _rsi_zone(self, rsi: float | None) -> str | None:
        '''Classify RSI against the configured thresholds (a comparison fact).'''
        if rsi is None:
            return None
        if rsi >= self.settings.get('rsi', 'overbought'):
            return c.RSI_ZONE_OVERBOUGHT
        if rsi <= self.settings.get('rsi', 'oversold'):
            return c.RSI_ZONE_OVERSOLD
        return c.RSI_ZONE_NEUTRAL
