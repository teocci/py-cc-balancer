'''Result of fetching one timeframe into the simulation store.'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['SimFetchResult']


@dataclass(frozen=True, slots=True)
class SimFetchResult:
    '''Outcome of a single ``simulation fetch`` timeframe pull.

    Attributes:
        symbol: The pair fetched, as ``BASE/QUOTE``.
        timeframe: The ccxt timeframe string (e.g. ``'1h'``).
        appended: Candles newly appended this run (0 when already up to date).
        total_rows: Total stored candles for the timeframe after the fetch.
        first_open_ms: Open time of the earliest stored candle, or ``None`` if empty.
        last_open_ms: Open time of the newest stored candle, or ``None`` if empty.
        up_to_date: Whether the store already covered the requested range (no pull).
    '''

    symbol: str
    timeframe: str
    appended: int
    total_rows: int
    first_open_ms: int | None
    last_open_ms: int | None
    up_to_date: bool
