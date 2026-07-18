'''Phase 17 tests: the append-only, resumable simulation OHLCV store.

Unlike the overwrite-on-write :class:`MarketCache`, this store only ever appends
the missing tail: prior rows stay byte-identical across resumed fetches, the
boundary candle is never duplicated, and a per-symbol manifest tracks coverage
and gaps for the backtest engine to read.
'''

from __future__ import annotations

import pytest

from ccbalancer.constants import SIM_MANIFEST_FILENAME, SIM_OHLCV_DIRNAME
from ccbalancer.exceptions import StateError
from ccbalancer.stores.simulation_store import SimulationStore

_HOUR_MS = 3_600_000
_START = 1_661_990_400_000  # 2022-09-01T00:00:00Z, matching the sample's first open


def _candles(count: int, *, start: int = _START, step: int = _HOUR_MS) -> list[list[float]]:
    return [[start + i * step, 10.0 + i, 12.0 + i, 9.0 + i, 11.0 + i, 100.0 + i] for i in range(count)]


def _store(tmp_path) -> SimulationStore:
    return SimulationStore(tmp_path)


def test_path_layout(tmp_path):
    store = _store(tmp_path)
    base = tmp_path / SIM_OHLCV_DIRNAME / 'binance' / 'BTC_USDT'
    assert store.path_for('binance', 'BTC/USDT', '1h') == base / '1h.jsonl'
    assert store.manifest_path('binance', 'BTC/USDT') == base / SIM_MANIFEST_FILENAME


def test_append_then_read_round_trips_ccxt_lists(tmp_path):
    store = _store(tmp_path)
    candles = _candles(3)
    assert store.append('binance', 'BTC/USDT', '1h', candles) == 3
    assert store.read('binance', 'BTC/USDT', '1h') == candles


def test_read_absent_returns_empty(tmp_path):
    assert _store(tmp_path).read('binance', 'ETH/USDT', '4h') == []


def test_read_corrupt_raises_state_error(tmp_path):
    store = _store(tmp_path)
    path = store.path_for('binance', 'BTC/USDT', '1h')
    path.parent.mkdir(parents=True)
    path.write_text('not json\n', encoding='utf-8')
    with pytest.raises(StateError):
        store.read('binance', 'BTC/USDT', '1h')


def test_persisted_as_compact_dict_records(tmp_path):
    store = _store(tmp_path)
    store.append('binance', 'BTC/USDT', '1h', _candles(1))
    line = store.path_for('binance', 'BTC/USDT', '1h').read_text(encoding='utf-8').splitlines()[0]
    assert line == '{"t":1661990400000,"o":10.0,"h":12.0,"l":9.0,"c":11.0,"v":100.0}'


def test_last_open_reports_newest_open_or_none(tmp_path):
    store = _store(tmp_path)
    assert store.last_open('binance', 'BTC/USDT', '1h') is None
    store.append('binance', 'BTC/USDT', '1h', _candles(3))
    assert store.last_open('binance', 'BTC/USDT', '1h') == _START + 2 * _HOUR_MS


def test_append_is_append_only_prior_bytes_unchanged(tmp_path):
    store = _store(tmp_path)
    store.append('binance', 'BTC/USDT', '1h', _candles(3))
    path = store.path_for('binance', 'BTC/USDT', '1h')
    before = path.read_bytes()

    store.append('binance', 'BTC/USDT', '1h', _candles(5)[3:])  # opens 3,4

    after = path.read_bytes()
    assert after.startswith(before)  # earlier rows are never rewritten
    assert store.read('binance', 'BTC/USDT', '1h') == _candles(5)


def test_append_dedups_boundary_and_earlier(tmp_path):
    store = _store(tmp_path)
    store.append('binance', 'BTC/USDT', '1h', _candles(3))  # opens 0,1,2
    # Re-offer opens 1,2,3,4 — only the strictly-newer 3,4 should land.
    appended = store.append('binance', 'BTC/USDT', '1h', _candles(5)[1:])
    assert appended == 2
    assert [row[0] for row in store.read('binance', 'BTC/USDT', '1h')] == [
        _START + i * _HOUR_MS for i in range(5)
    ]


def test_append_empty_is_noop(tmp_path):
    store = _store(tmp_path)
    assert store.append('binance', 'BTC/USDT', '1h', []) == 0
    assert store.read('binance', 'BTC/USDT', '1h') == []


def test_rebuild_manifest_tracks_coverage_and_gaps(tmp_path):
    store = _store(tmp_path)
    # A contiguous run of 5, then a 2-candle hole, then 2 more.
    contiguous = _candles(5)
    after_gap = _candles(2, start=_START + 7 * _HOUR_MS)
    store.append('binance', 'BTC/USDT', '1h', contiguous + after_gap)

    manifest = store.rebuild_manifest(
        'binance', 'BTC/USDT',
        {'market': 'spot', 'source_endpoint': 'ccxt:binance:fetchOHLCV', 'fetched_at_utc': '2026-07-18T00:00:00Z'},
    )

    assert manifest['exchange'] == 'binance'
    assert manifest['market'] == 'spot'
    assert manifest['symbol'] == 'BTC/USDT'
    assert manifest['source_endpoint'] == 'ccxt:binance:fetchOHLCV'
    assert manifest['fetched_at_utc'] == '2026-07-18T00:00:00Z'
    tf = manifest['timeframes']['1h']
    assert tf['interval_ms'] == _HOUR_MS
    assert tf['row_count'] == 7
    assert tf['expected_count'] == 9  # opens span 0..8 inclusive
    assert tf['missing_count'] == 2
    assert len(tf['gaps']) == 1
    assert tf['gaps'][0]['missing'] == 2
    # And it is written to disk.
    assert store.manifest_path('binance', 'BTC/USDT').is_file()
