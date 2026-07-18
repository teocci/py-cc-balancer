'''Load the committed backtest sample into ccxt candles (read-only ingest).

The shipped ``data/simulation`` tree carries historical OHLCV in two shapes: a
wide CSV (``open_time_ms``, ISO columns, then OHLCV) produced by the fetch
tooling, and the compact ``{"t","o","h","l","c","v"}`` JSONL it converts to. This
module normalizes either to the same ccxt ``[t,o,h,l,c,v]`` lists so a backtest
can run offline with no network pull.

Ingest only — it never writes. Persisting fetched candles is the concern of
:class:`~ccbalancer.stores.simulation_store.SimulationStore`.
'''

from __future__ import annotations

import csv
import json
from pathlib import Path

from ccbalancer.exceptions import StateError
from ccbalancer.utils.candles import record_to_candle

__all__ = ['load_sample']

# CSV column -> ccxt candle index. Open-time is the integer field; the rest float.
_CSV_TIME_COLUMN = 'open_time_ms'
_CSV_FLOAT_COLUMNS = ('open', 'high', 'low', 'close', 'volume')


def load_sample(path: Path) -> list[list[float]]:
    '''Return the file's candles as ccxt ``[t,o,h,l,c,v]`` lists.

    Dispatches on the file extension: ``.csv`` (wide) or ``.jsonl`` (compact
    records).

    Raises:
        StateError: If the file is missing, unreadable, malformed, or has an
            unsupported extension.
    '''
    suffix = path.suffix.lower()
    if suffix == '.csv':
        return _load_csv(path)
    if suffix == '.jsonl':
        return _load_jsonl(path)
    raise StateError(f'Unsupported sample format {path.suffix!r} for {path}; expected .csv or .jsonl')


def _load_csv(path: Path) -> list[list[float]]:
    try:
        with path.open(newline='', encoding='utf-8') as handle:
            return [_csv_row_to_candle(row) for row in csv.DictReader(handle)]
    except (OSError, KeyError, ValueError) as exc:
        raise StateError(f'Cannot read sample CSV {path}: {exc}') from exc


def _load_jsonl(path: Path) -> list[list[float]]:
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
        return [record_to_candle(json.loads(line)) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise StateError(f'Cannot read sample JSONL {path}: {exc}') from exc


def _csv_row_to_candle(row: dict[str, str]) -> list[float]:
    return [int(row[_CSV_TIME_COLUMN]), *(float(row[col]) for col in _CSV_FLOAT_COLUMNS)]
