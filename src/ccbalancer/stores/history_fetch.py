'''Binance public REST klines fetcher — the sub-daily backfill fallback.

For deep 1m/5m history the ccxt pager is impractical; this store goes straight to
Binance's public ``/api/v3/klines`` endpoint (no API key), paginating up to 1000
rows per call and advancing the cursor past each page's last open so no candle is
re-downloaded. Only closed candles with open in ``[since_ms, until_ms)`` are
returned, normalized to ccxt's ``[t,o,h,l,c,v]`` shape so the
:class:`~ccbalancer.stores.simulation_store.SimulationStore` and the replay engine
treat these rows identically to ccxt-sourced ones.

Along with :class:`~ccbalancer.stores.exchange.ExchangeStore` this is the only
module that reaches the network; managers never do. The HTTP call is an injected
seam (:attr:`BinanceHistoryFetch.http_get`) so tests exercise pagination,
closed-candle trimming, 429/418 backoff, and the HTTP-451 archive note entirely
offline. The method signature mirrors ``ExchangeStore.fetch_ohlcv_range`` so the
:class:`~ccbalancer.managers.simulation_manager.SimulationManager` can route to
either source uniformly.
'''

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from ccbalancer import constants as c
from ccbalancer.exceptions import ExchangeError
from ccbalancer.utils.candles import candle_to_record, record_to_candle
from ccbalancer.utils.timeutil import timeframe_to_seconds

__all__ = ['BinanceHistoryFetch']

# Binance kline field indices (12 fields per row); only the first six are read.
_OPEN_TIME = 0
_OHLCV = slice(0, 6)

_USER_AGENT = f'{c.APP_NAME}/history-fetch'


def _urlopen_get(url: str, timeout: float) -> tuple[int, bytes]:
    '''Default HTTP seam: GET ``url``, returning ``(status, body)``.

    An HTTP error status (4xx/5xx) is returned rather than raised so the fetcher
    handles retry/blocked/other uniformly; a transport failure becomes a domain
    error.

    Raises:
        ExchangeError: On a transport-level failure (no HTTP response).
    '''
    request = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https host
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise ExchangeError(f'Cannot reach Binance klines endpoint: {exc.reason}') from exc


@dataclass(slots=True)
class BinanceHistoryFetch:
    '''Paginated Binance REST klines fetcher for deep sub-daily backfill.

    Attributes:
        timeout_ms: Per-request HTTP timeout in milliseconds.
        retries: Backoff-retry budget for a rate-limit/ban status (429/418).
        backoff_ms: Base backoff between retries, in ms, doubled each attempt.
        limit: Rows requested per page (venue max is 1000).
        http_get: Injected ``(url, timeout) -> (status, body)`` HTTP seam.
        sleep: Injected sleep, seconds (patched out in tests).
    '''

    timeout_ms: int = c.DEFAULT_HTTP_TIMEOUT_MS
    retries: int = c.BINANCE_KLINES_RETRIES
    backoff_ms: int = c.BINANCE_KLINES_BACKOFF_MS
    limit: int = c.BINANCE_KLINES_LIMIT
    http_get: Callable[[str, float], tuple[int, bytes]] = field(default=_urlopen_get, repr=False)
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False)

    def fetch_ohlcv_range(
        self, symbol: str, timeframe: str, since_ms: int, until_ms: int
    ) -> list[list[float]]:
        '''Return the closed ``[t,o,h,l,c,v]`` candles with open in ``[since_ms, until_ms)``.

        Pages ``/api/v3/klines`` from ``since_ms``, advancing the cursor past each
        page's last open so no candle repeats, until the venue runs out of data or
        the cursor reaches ``until_ms``. The still-forming last candle (one whose
        interval has not closed by ``until_ms``) is dropped.
        '''
        interval_ms = timeframe_to_seconds(timeframe) * 1000
        market = symbol.replace('/', '')
        collected: list[list[float]] = []
        seen: set[int] = set()
        cursor = since_ms
        while cursor < until_ms:
            page = self._fetch_page(market, timeframe, cursor)
            if not page:
                break
            _collect_closed(page, since_ms, until_ms, interval_ms, seen, collected)
            next_cursor = int(page[-1][_OPEN_TIME]) + interval_ms
            if len(page) < self.limit or next_cursor <= cursor:
                break
            cursor = next_cursor
        return collected

    def _fetch_page(self, market: str, timeframe: str, since_ms: int) -> list[list]:
        '''Fetch one page of raw klines, retrying rate-limit/ban statuses.

        Raises:
            ExchangeError: On a legal block (451, with the archive note), a
                non-retryable status, or exhausted retries.
        '''
        url = self._page_url(market, timeframe, since_ms)
        for attempt in range(self.retries + 1):
            status, body = self.http_get(url, self.timeout_ms / 1000.0)
            if status == 200:
                return json.loads(body)
            if status == c.BINANCE_KLINES_BLOCKED_STATUS:
                raise ExchangeError(
                    f'Binance klines blocked (HTTP 451) for {market} {timeframe}; '
                    f'use the bulk archive at {c.BINANCE_ARCHIVE_URL}'
                )
            if status in c.BINANCE_KLINES_RETRY_STATUS and attempt < self.retries:
                self.sleep(self.backoff_ms / 1000.0 * 2 ** attempt)
                continue
            raise ExchangeError(f'Cannot fetch Binance klines {market} {timeframe} (HTTP {status})')
        raise AssertionError('unreachable: retry loop always returns or raises')

    def _page_url(self, market: str, timeframe: str, since_ms: int) -> str:
        query = urllib.parse.urlencode({
            'symbol': market,
            'interval': timeframe,
            'startTime': since_ms,
            'limit': self.limit,
        })
        return f'{c.BINANCE_KLINES_URL}?{query}'


def _collect_closed(
    page: list[list],
    since_ms: int,
    until_ms: int,
    interval_ms: int,
    seen: set[int],
    out: list[list[float]],
) -> None:
    '''Append normalized, in-range, closed, not-yet-seen candles from ``page``.'''
    for row in page:
        open_ms = int(row[_OPEN_TIME])
        if open_ms < since_ms or open_ms + interval_ms > until_ms or open_ms in seen:
            continue
        seen.add(open_ms)
        # Same normalization as the ccxt path (t->int, OHLCV->float from strings).
        out.append(record_to_candle(candle_to_record(row[_OHLCV])))
