'''Phase 17 tests: the fetch orchestration over the exchange + simulation store.

The manager resolves the resume point from the store, pulls only the missing tail
via the exchange range fetch, appends it, and rebuilds the per-symbol manifest.
The exchange is a fake (no network); the store is real (tmp_path).
'''

from __future__ import annotations

from ccbalancer.managers.simulation_manager import SimulationManager
from ccbalancer.stores.simulation_store import SimulationStore

from .conftest import FakeExchangeStore

_HOUR_MS = 3_600_000
_START = 1_661_990_400_000
_FETCHED_AT = '2026-07-18T00:00:00Z'


def _candles(count: int, *, start: int = _START) -> list[list[float]]:
    return [[start + i * _HOUR_MS, 10.0 + i, 12.0 + i, 9.0 + i, 11.0 + i, 100.0 + i] for i in range(count)]


def _manager(tmp_path, candles) -> tuple[SimulationManager, FakeExchangeStore, SimulationStore]:
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={('BTC/USDT', '1h'): candles})
    store = SimulationStore(tmp_path)
    return SimulationManager(exchange, store), exchange, store


def test_initial_fetch_appends_full_range_and_writes_manifest(tmp_path):
    candles = _candles(5)
    manager, exchange, store = _manager(tmp_path, candles)
    until = candles[-1][0] + _HOUR_MS

    results = manager.fetch('BTC/USDT', ['1h'], _START, until, _FETCHED_AT)

    result = results[0]
    assert result.appended == 5
    assert result.total_rows == 5
    assert result.up_to_date is False
    assert result.first_open_ms == _START
    assert result.last_open_ms == candles[-1][0]
    # Pulled from the requested start (empty store -> no resume offset).
    assert exchange.range_calls == [('BTC/USDT', '1h', _START, until)]
    assert store.manifest_path('binance', 'BTC/USDT').is_file()


def test_resume_pulls_only_the_missing_tail(tmp_path):
    candles = _candles(8)
    manager, exchange, store = _manager(tmp_path, candles)
    # Pre-seed the first 5 candles as if a prior run had stored them.
    store.append('binance', 'BTC/USDT', '1h', candles[:5])
    seeded_bytes = store.path_for('binance', 'BTC/USDT', '1h').read_bytes()
    until = candles[-1][0] + _HOUR_MS

    results = manager.fetch('BTC/USDT', ['1h'], _START, until, _FETCHED_AT)

    result = results[0]
    assert result.appended == 3  # only opens 5,6,7
    assert result.total_rows == 8
    # Resume offset: since = last stored open + one interval.
    resume_since = candles[4][0] + _HOUR_MS
    assert exchange.range_calls == [('BTC/USDT', '1h', resume_since, until)]
    # Prior rows are never rewritten.
    assert store.path_for('binance', 'BTC/USDT', '1h').read_bytes().startswith(seeded_bytes)


def test_up_to_date_makes_no_range_call(tmp_path):
    candles = _candles(5)
    manager, exchange, store = _manager(tmp_path, candles)
    store.append('binance', 'BTC/USDT', '1h', candles)
    until = candles[-1][0] + _HOUR_MS  # since would be last+interval == until

    results = manager.fetch('BTC/USDT', ['1h'], _START, until, _FETCHED_AT)

    result = results[0]
    assert result.appended == 0
    assert result.up_to_date is True
    assert result.total_rows == 5
    assert exchange.range_calls == []  # nothing to pull


def test_manifest_stamps_provenance(tmp_path):
    candles = _candles(3)
    manager, _exchange, store = _manager(tmp_path, candles)
    until = candles[-1][0] + _HOUR_MS

    manager.fetch('BTC/USDT', ['1h'], _START, until, _FETCHED_AT)

    import json
    manifest = json.loads(store.manifest_path('binance', 'BTC/USDT').read_text(encoding='utf-8'))
    assert manifest['exchange'] == 'binance'
    assert manifest['market'] == 'spot'
    assert manifest['fetched_at_utc'] == _FETCHED_AT
    assert manifest['timeframes']['1h']['row_count'] == 3
