'''Cached OHLCV persistence for indicators.

Candles are cached per pair and timeframe under
``~/.ccbalancer/ohlcv/{symbol}/{timeframe}.jsonl`` (one candle per line). This is
the only code that reads or writes those files; the exchange is never touched
here. Caching keeps repeated ``analyze`` calls cheap and provides an offline
fallback when the data exchange is unreachable.

Freshness is judged against the newest cached candle: a cache is stale once its
last candle's open time is older than :data:`CACHE_STALE_FACTOR` timeframes,
meaning a newer candle should already exist.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.constants import CACHE_STALE_FACTOR
from ccbalancer.exceptions import StateError
from ccbalancer.utils.timeutil import timeframe_to_seconds

__all__ = ['MarketCache']

# Index of the open-time field in a ccxt candle ``[time, o, h, l, c, v]``.
_CANDLE_TIME = 0


@dataclass(slots=True)
class MarketCache:
    '''Read/write access to cached OHLCV candles.

    Attributes:
        root: Directory holding the per-symbol candle subdirectories.
    '''

    root: Path

    def path_for(self, symbol: str, timeframe: str) -> Path:
        '''Return the cache file path for ``symbol`` and ``timeframe``.'''
        safe_symbol = symbol.replace('/', '_')
        return self.root / safe_symbol / f'{timeframe}.jsonl'

    def read(self, symbol: str, timeframe: str) -> list[list[float]]:
        '''Return cached candles for the pair/timeframe (empty if none cached).

        Raises:
            StateError: If the cache file exists but cannot be parsed.
        '''
        path = self.path_for(symbol, timeframe)
        if not path.is_file():
            return []
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
            return [json.loads(line) for line in lines if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f'Cannot read OHLCV cache {path}: {exc}') from exc

    def write(self, symbol: str, timeframe: str, candles: list[list[float]]) -> None:
        '''Overwrite the cache file with ``candles`` (one JSON line each).'''
        path = self.path_for(symbol, timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = '\n'.join(json.dumps(candle) for candle in candles)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(body + '\n' if body else '', encoding='utf-8')
        tmp.replace(path)

    def is_fresh(self, candles: list[list[float]], timeframe: str, now_ms: int) -> bool:
        '''Return whether ``candles`` are recent enough to use without refetching.'''
        if not candles:
            return False
        newest_open_ms = candles[-1][_CANDLE_TIME]
        max_age_ms = timeframe_to_seconds(timeframe) * 1000 * CACHE_STALE_FACTOR
        return now_ms - newest_open_ms < max_age_ms
