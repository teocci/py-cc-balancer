'''Phase 17 tests: ccxt-candle <-> compact JSONL record mapping.

The simulation store and the sample loader share one on-disk record shape — a
compact ``{"t","o","h","l","c","v"}`` object (open-time epoch ms as int, OHLCV as
floats) — while working in memory with ccxt ``[t,o,h,l,c,v]`` lists. These helpers
are the single, deterministic bridge between the two; a stable serialization is
what makes the append-only store byte-identical across resumed fetches.
'''

from __future__ import annotations

from ccbalancer.utils.candles import candle_to_record, dumps_record, record_to_candle

_CANDLE = [1661990400000, 20048.44, 20138.15, 19917.01, 20064.43, 11108.70225]
_RECORD = {'t': 1661990400000, 'o': 20048.44, 'h': 20138.15, 'l': 19917.01, 'c': 20064.43, 'v': 11108.70225}


def test_candle_to_record_maps_keys_and_types():
    record = candle_to_record(_CANDLE)
    assert record == _RECORD
    assert isinstance(record['t'], int)
    assert all(isinstance(record[k], float) for k in ('o', 'h', 'l', 'c', 'v'))


def test_record_to_candle_returns_ccxt_list():
    assert record_to_candle(_RECORD) == _CANDLE
    assert isinstance(record_to_candle(_RECORD)[0], int)


def test_round_trip_is_identity():
    assert record_to_candle(candle_to_record(_CANDLE)) == _CANDLE


def test_dumps_record_is_compact_and_stable():
    line = dumps_record(candle_to_record(_CANDLE))
    assert line == '{"t":1661990400000,"o":20048.44,"h":20138.15,"l":19917.01,"c":20064.43,"v":11108.70225}'
    # Deterministic: the same candle always serializes byte-identically.
    assert line == dumps_record(candle_to_record(list(_CANDLE)))


def test_candle_to_record_coerces_string_numbers():
    # Some venues hand back numeric strings; normalization must coerce them.
    record = candle_to_record(['1661990400000', '20048.44', '20138.15', '19917.01', '20064.43', '11108.70225'])
    assert record == _RECORD
