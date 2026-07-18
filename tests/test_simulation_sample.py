'''Phase 17 tests: ingest the committed backtest sample into ccxt candles.

The loader normalizes both shipped shapes — the wide CSV (``open_time_ms``, ISO
columns, OHLCV) and the compact ``{"t",...}`` JSONL — to the same ccxt
``[t,o,h,l,c,v]`` lists, so a backtest can run offline against ``data/simulation``
with no network pull.
'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import StateError
from ccbalancer.stores.simulation_sample import load_sample

_FIRST_1H = [1661990400000, 20048.44, 20138.15, 19917.01, 20064.43, 11108.70225]


def test_load_csv_normalizes_to_ccxt_candles(sample_dir):
    candles = load_sample(sample_dir / 'binance' / 'BTCUSDT_1h.csv')
    assert candles[0] == _FIRST_1H
    assert isinstance(candles[0][0], int)
    assert all(isinstance(candles[0][i], float) for i in range(1, 6))


def test_load_jsonl_normalizes_to_ccxt_candles(sample_dir):
    candles = load_sample(sample_dir / 'binance' / 'jsonl' / 'BTCUSDT_1h.jsonl')
    assert candles[0] == _FIRST_1H


def test_csv_and_jsonl_agree(sample_dir):
    from_csv = load_sample(sample_dir / 'binance' / 'BTCUSDT_1h.csv')
    from_jsonl = load_sample(sample_dir / 'binance' / 'jsonl' / 'BTCUSDT_1h.jsonl')
    assert from_csv == from_jsonl


def test_candles_are_ascending_and_contiguous_at_head(sample_dir):
    candles = load_sample(sample_dir / 'binance' / 'BTCUSDT_1h.csv')
    hour_ms = 3_600_000
    assert candles[1][0] - candles[0][0] == hour_ms
    assert candles[2][0] > candles[1][0]


def test_missing_file_raises_state_error(tmp_path):
    with pytest.raises(StateError):
        load_sample(tmp_path / 'nope.csv')


def test_unknown_extension_raises_state_error(tmp_path):
    bad = tmp_path / 'candles.parquet'
    bad.write_text('x', encoding='utf-8')
    with pytest.raises(StateError):
        load_sample(bad)
