'''Phase 20 (I-15) tests: the Binance public REST klines fallback fetcher.

Exercises pagination, closed-candle trimming, range filtering, normalization to
ccxt's ``[t,o,h,l,c,v]`` shape, 429/418 backoff, and the HTTP-451 archive note —
all against an injected HTTP seam, never the live network.
'''

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from ccbalancer import constants as c
from ccbalancer.exceptions import ExchangeError
from ccbalancer.stores.history_fetch import BinanceHistoryFetch

_MIN_MS = 60_000
_START = 1_661_990_400_000


def _row(open_ms: int, i: int, interval_ms: int = _MIN_MS) -> list:
    '''A Binance kline row (12 fields, prices as strings); only 0..5 are read.'''
    return [
        open_ms, f'{10 + i}', f'{12 + i}', f'{9 + i}', f'{11 + i}', f'{100 + i}',
        open_ms + interval_ms - 1, '0', 1, '0', '0', '0',
    ]


def _page(opens: list[int]) -> list[list]:
    return [_row(t, i) for i, t in enumerate(opens)]


class _FakeHttp:
    '''Serves queued pages in call order; records the requested URLs.'''

    def __init__(self, pages: list[list[list]]) -> None:
        self.pages = pages
        self.calls: list[str] = []
        self._i = 0

    def __call__(self, url: str, timeout: float) -> tuple[int, bytes]:
        self.calls.append(url)
        page = self.pages[self._i] if self._i < len(self.pages) else []
        self._i += 1
        return 200, json.dumps(page).encode()

    def start_time(self, call_index: int) -> int:
        query = parse_qs(urlsplit(self.calls[call_index]).query)
        return int(query['startTime'][0])

    def symbol(self, call_index: int) -> str:
        query = parse_qs(urlsplit(self.calls[call_index]).query)
        return query['symbol'][0]


def _fetcher(http, **kw) -> BinanceHistoryFetch:
    base = dict(http_get=http, sleep=lambda _s: None, limit=3)
    base.update(kw)
    return BinanceHistoryFetch(**base)


def test_single_page_normalizes_to_float_candles():
    opens = [_START, _START + _MIN_MS, _START + 2 * _MIN_MS]
    http = _FakeHttp([_page(opens)])
    until = _START + 3 * _MIN_MS
    fetcher = _fetcher(http)

    candles = fetcher.fetch_ohlcv_range('BTC/USDT', '1m', _START, until)

    assert candles == [
        [_START, 10.0, 12.0, 9.0, 11.0, 100.0],
        [_START + _MIN_MS, 11.0, 13.0, 10.0, 12.0, 101.0],
        [_START + 2 * _MIN_MS, 12.0, 14.0, 11.0, 13.0, 102.0],
    ]
    assert all(isinstance(v, float) for candle in candles for v in candle[1:])


def test_symbol_slash_stripped_in_request():
    http = _FakeHttp([_page([_START])])
    _fetcher(http).fetch_ohlcv_range('BTC/USDT', '1m', _START, _START + _MIN_MS)
    assert http.symbol(0) == 'BTCUSDT'


def test_paginates_across_full_pages_advancing_cursor():
    first = [_START + i * _MIN_MS for i in range(3)]            # full page (limit=3)
    second = [_START + (3 + i) * _MIN_MS for i in range(2)]     # partial -> stop
    http = _FakeHttp([_page(first), _page(second)])
    until = _START + 5 * _MIN_MS
    fetcher = _fetcher(http)

    candles = fetcher.fetch_ohlcv_range('BTC/USDT', '1m', _START, until)

    assert [int(candle[0]) for candle in candles] == first + second
    # Second call resumes one interval past the first page's last open (no dup).
    assert http.start_time(1) == first[-1] + _MIN_MS
    assert len(http.calls) == 2  # partial second page ends pagination


def test_drops_forming_candle_beyond_until():
    opens = [_START, _START + _MIN_MS, _START + 2 * _MIN_MS]
    http = _FakeHttp([_page(opens)])
    # until falls inside the 3rd candle's interval -> it has not closed -> dropped.
    until = _START + 2 * _MIN_MS + 1
    candles = _fetcher(http).fetch_ohlcv_range('BTC/USDT', '1m', _START, until)
    assert [int(candle[0]) for candle in candles] == [_START, _START + _MIN_MS]


def test_range_filter_excludes_candles_before_since():
    opens = [_START, _START + _MIN_MS, _START + 2 * _MIN_MS]
    http = _FakeHttp([_page(opens)])
    since = _START + _MIN_MS
    until = _START + 3 * _MIN_MS
    candles = _fetcher(http).fetch_ohlcv_range('BTC/USDT', '1m', since, until)
    assert [int(candle[0]) for candle in candles] == [since, _START + 2 * _MIN_MS]


def test_retries_on_429_then_succeeds():
    sleeps: list[float] = []
    page = _page([_START])
    responses = [(429, b''), (200, json.dumps(page).encode())]

    def http(url: str, timeout: float) -> tuple[int, bytes]:
        return responses.pop(0)

    fetcher = BinanceHistoryFetch(http_get=http, sleep=sleeps.append, limit=3)
    candles = fetcher.fetch_ohlcv_range('BTC/USDT', '1m', _START, _START + _MIN_MS)

    assert len(candles) == 1
    assert len(sleeps) == 1  # one backoff before the retry


def test_blocked_451_raises_with_archive_note():
    def http(url: str, timeout: float) -> tuple[int, bytes]:
        return c.BINANCE_KLINES_BLOCKED_STATUS, b''

    with pytest.raises(ExchangeError) as excinfo:
        _fetcher(http).fetch_ohlcv_range('BTC/USDT', '1m', _START, _START + _MIN_MS)
    assert c.BINANCE_ARCHIVE_URL in str(excinfo.value)


def test_non_retryable_status_raises():
    def http(url: str, timeout: float) -> tuple[int, bytes]:
        return 500, b''

    with pytest.raises(ExchangeError):
        _fetcher(http).fetch_ohlcv_range('BTC/USDT', '1m', _START, _START + _MIN_MS)


def test_retries_exhausted_raises_after_budget():
    sleeps: list[float] = []

    def http(url: str, timeout: float) -> tuple[int, bytes]:
        return 429, b''

    fetcher = BinanceHistoryFetch(http_get=http, sleep=sleeps.append, limit=3, retries=2)
    with pytest.raises(ExchangeError):
        fetcher.fetch_ohlcv_range('BTC/USDT', '1m', _START, _START + _MIN_MS)
    assert len(sleeps) == 2  # exactly the retry budget, then give up
