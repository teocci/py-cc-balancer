'''ccxt-candle <-> compact JSONL record mapping.

In memory ccbalancer works with ccxt candles — ``[time, open, high, low, close,
volume]`` lists, open-time in epoch ms. On disk the simulation store persists one
compact ``{"t","o","h","l","c","v"}`` object per line (``separators=(',', ':')``),
matching the rolling-dataset convention shared with the historical-data tooling.

These helpers are the single deterministic bridge between the two forms. Keeping
serialization here (rather than inline at each call site) is what lets the
append-only store guarantee prior rows stay byte-identical across resumed fetches.
'''

from __future__ import annotations

import json

__all__ = ['candle_to_record', 'record_to_candle', 'dumps_record', 'CANDLE_TIME']

# Field order of a ccxt candle list and the JSONL record keys they map to.
_KEYS = ('t', 'o', 'h', 'l', 'c', 'v')
# Index of the open-time field in a ccxt candle (also the record's ``t``).
CANDLE_TIME = 0
# Keys carrying float values (everything except the integer open-time).
_FLOAT_KEYS = ('o', 'h', 'l', 'c', 'v')
# Compact separators: no whitespace, matching the shared JSONL convention.
_COMPACT = (',', ':')


def candle_to_record(candle: list) -> dict:
    '''Map a ccxt ``[t,o,h,l,c,v]`` candle to a compact record.

    Values are coerced (``t`` to ``int``, OHLCV to ``float``) so records written
    from any venue's raw shape — including numeric strings — normalize uniformly.
    '''
    return {
        't': int(candle[0]),
        'o': float(candle[1]),
        'h': float(candle[2]),
        'l': float(candle[3]),
        'c': float(candle[4]),
        'v': float(candle[5]),
    }


def record_to_candle(record: dict) -> list:
    '''Map a compact record back to a ccxt ``[t,o,h,l,c,v]`` candle list.'''
    return [int(record['t']), *(float(record[key]) for key in _FLOAT_KEYS)]


def dumps_record(record: dict) -> str:
    '''Serialize one record to a compact JSON line (no trailing newline).

    Keys emit in canonical ``t,o,h,l,c,v`` order so the output is stable and
    comparable across runs.
    '''
    ordered = {key: record[key] for key in _KEYS}
    return json.dumps(ordered, separators=_COMPACT)
