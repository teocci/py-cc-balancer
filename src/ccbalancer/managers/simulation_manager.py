'''Orchestrate historical OHLCV fetching into the resumable simulation store.

Coordinates the two stores the backtest data foundation needs: the network-only
:class:`~ccbalancer.stores.exchange.ExchangeStore` (paginated range fetch) and the
append-only :class:`~ccbalancer.stores.simulation_store.SimulationStore`. Per
timeframe it resolves the resume point from the store, pulls only the missing tail
since the last closed candle, appends it, and — once all requested timeframes are
done — rebuilds the per-symbol manifest.

The manager holds no network code and never reads the clock; the caller passes the
range bound (``until_ms``) and the provenance timestamp (``fetched_at``).
'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer import constants as c
from ccbalancer.models import SimFetchResult
from ccbalancer.utils.candles import CANDLE_TIME
from ccbalancer.utils.timeutil import timeframe_to_seconds

if TYPE_CHECKING:
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.history_fetch import BinanceHistoryFetch
    from ccbalancer.stores.simulation_store import SimulationStore

    # Either source exposes fetch_ohlcv_range(symbol, timeframe, since, until).
    RangeSource = ExchangeStore | BinanceHistoryFetch

__all__ = ['SimulationManager']

# This tool is spot-only; recorded as provenance in the manifest.
_MARKET = 'spot'


@dataclass(slots=True)
class SimulationManager:
    '''Fetch-and-persist coordinator for the backtest data foundation.

    Attributes:
        exchange: Network store supplying paginated range candles (ccxt pager).
        store: Append-only simulation OHLCV store the candles land in.
        history_fetch: Optional Binance REST fallback for sub-daily (1m/5m)
            backfill; when absent, every timeframe uses the ccxt pager.
    '''

    exchange: ExchangeStore
    store: SimulationStore
    history_fetch: BinanceHistoryFetch | None = None

    def fetch(
        self,
        symbol: str,
        timeframes: list[str],
        start_ms: int,
        until_ms: int,
        fetched_at: str,
    ) -> list[SimFetchResult]:
        '''Fetch each timeframe's missing tail, then rebuild the symbol manifest.

        Args:
            symbol: Pair as ``BASE/QUOTE``.
            timeframes: ccxt timeframe strings to fetch.
            start_ms: Range start (used only when a timeframe has no stored data).
            until_ms: Exclusive range end (typically now); forming candles excluded.
            fetched_at: ISO-8601 timestamp stamped into the manifest provenance.

        Returns:
            One :class:`SimFetchResult` per requested timeframe, in order.
        '''
        exchange_id = self.exchange.exchange_id
        results = [self._fetch_timeframe(exchange_id, symbol, tf, start_ms, until_ms) for tf in timeframes]
        self.store.rebuild_manifest(exchange_id, symbol, self._provenance(exchange_id, fetched_at))
        return results

    def _fetch_timeframe(
        self, exchange_id: str, symbol: str, timeframe: str, start_ms: int, until_ms: int
    ) -> SimFetchResult:
        '''Pull and append one timeframe's missing tail, then summarize coverage.'''
        interval_ms = timeframe_to_seconds(timeframe) * 1000
        last_open = self.store.last_open(exchange_id, symbol, timeframe)
        since = start_ms if last_open is None else last_open + interval_ms
        appended = 0
        # Skip the network entirely when the store already covers the requested
        # range; otherwise pull only the missing tail from the routed source.
        if since < until_ms:
            candles = self._source_for(timeframe).fetch_ohlcv_range(symbol, timeframe, since, until_ms)
            appended = self.store.append(exchange_id, symbol, timeframe, candles)
        return self._summarize(exchange_id, symbol, timeframe, appended, up_to_date=appended == 0)

    def _source_for(self, timeframe: str) -> RangeSource:
        '''Pick the range source: the Binance REST fallback for sub-daily (1m/5m)
        when available, else the ccxt pager for every other timeframe.'''
        if self.history_fetch is not None and timeframe in c.SIM_LTF_TIMEFRAMES:
            return self.history_fetch
        return self.exchange

    def _summarize(
        self, exchange_id: str, symbol: str, timeframe: str, appended: int, *, up_to_date: bool
    ) -> SimFetchResult:
        '''Read back coverage for the timeframe into a result record.'''
        stored = self.store.read(exchange_id, symbol, timeframe)
        return SimFetchResult(
            symbol=symbol,
            timeframe=timeframe,
            appended=appended,
            total_rows=len(stored),
            first_open_ms=int(stored[0][CANDLE_TIME]) if stored else None,
            last_open_ms=int(stored[-1][CANDLE_TIME]) if stored else None,
            up_to_date=up_to_date,
        )

    @staticmethod
    def _provenance(exchange_id: str, fetched_at: str) -> dict[str, object]:
        return {
            'market': _MARKET,
            'source_endpoint': f'ccxt:{exchange_id}:fetchOHLCV',
            'fetched_at_utc': fetched_at,
        }
