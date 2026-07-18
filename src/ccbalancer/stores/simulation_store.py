'''Append-only, resumable OHLCV persistence for the backtest data foundation.

Historical candles live under
``<app_dir>/simulation/ohlcv/{exchange}/{symbol}/{timeframe}.jsonl`` (one compact
``{"t","o","h","l","c","v"}`` record per line) with a per-symbol ``manifest.json``
tracking provenance, coverage, and gaps. This is the only code that reads or
writes those files; the network never enters here.

The defining contract — and what sets it apart from the overwrite-on-write
:class:`~ccbalancer.stores.market_cache.MarketCache` — is that a range is never
re-downloaded. :meth:`append` only ever adds candles strictly newer than the last
stored open, so prior rows stay byte-identical across resumed fetches and the
boundary candle is never duplicated. Callers resume from :meth:`last_open`.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer import constants as c
from ccbalancer.exceptions import StateError
from ccbalancer.utils.candles import CANDLE_TIME, candle_to_record, dumps_record, record_to_candle
from ccbalancer.utils.timeutil import ms_to_iso, timeframe_to_seconds

__all__ = ['SimulationStore']


@dataclass(slots=True)
class SimulationStore:
    '''Read/append access to the resumable simulation OHLCV tree.

    Attributes:
        root: The ``simulation`` directory holding the ``ohlcv/`` subtree.
    '''

    root: Path

    def path_for(self, exchange: str, symbol: str, timeframe: str) -> Path:
        '''Return the candle-file path for ``exchange``/``symbol``/``timeframe``.'''
        return self._symbol_dir(exchange, symbol) / f'{timeframe}.jsonl'

    def manifest_path(self, exchange: str, symbol: str) -> Path:
        '''Return the per-symbol manifest path.'''
        return self._symbol_dir(exchange, symbol) / c.SIM_MANIFEST_FILENAME

    def read(self, exchange: str, symbol: str, timeframe: str) -> list[list[float]]:
        '''Return stored candles as ccxt ``[t,o,h,l,c,v]`` lists (empty if none).

        Raises:
            StateError: If the file exists but cannot be parsed.
        '''
        path = self.path_for(exchange, symbol, timeframe)
        if not path.is_file():
            return []
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
            return [record_to_candle(json.loads(line)) for line in lines if line.strip()]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise StateError(f'Cannot read simulation OHLCV {path}: {exc}') from exc

    def last_open(self, exchange: str, symbol: str, timeframe: str) -> int | None:
        '''Return the open time (epoch ms) of the newest stored candle, or ``None``.'''
        path = self.path_for(exchange, symbol, timeframe)
        if not path.is_file():
            return None
        lines = [line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        if not lines:
            return None
        try:
            return int(json.loads(lines[-1])['t'])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StateError(f'Cannot read last open in {path}: {exc}') from exc

    def append(
        self, exchange: str, symbol: str, timeframe: str, candles: list[list[float]]
    ) -> int:
        '''Append candles strictly newer than the last stored open; return the count added.

        Candles at or before the current last open are dropped (boundary dedup), so
        the call is idempotent on overlap and the existing rows are never rewritten.
        '''
        cutoff = self.last_open(exchange, symbol, timeframe)
        fresh = [candle for candle in candles if cutoff is None or int(candle[CANDLE_TIME]) > cutoff]
        if not fresh:
            return 0
        path = self.path_for(exchange, symbol, timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = ''.join(dumps_record(candle_to_record(candle)) + '\n' for candle in fresh)
        with path.open('a', encoding='utf-8') as handle:
            handle.write(body)
        return len(fresh)

    def rebuild_manifest(
        self, exchange: str, symbol: str, provenance: dict[str, object] | None = None
    ) -> dict[str, object]:
        '''Recompute the per-symbol manifest from the stored files and persist it.

        Scans every timeframe file present for the symbol, deriving coverage
        (first/last open, row and expected counts) and interior gaps, and mirrors
        the shape of the shipped ``data/simulation`` sample so the two are
        interchangeable. ``provenance`` supplies the non-derivable header fields
        (``market``, ``source_endpoint``, ``fetched_at_utc``); the store never
        reads the clock, so the caller stamps the timestamp. Returns the manifest
        as written.
        '''
        prov = provenance or {}
        symbol_dir = self._symbol_dir(exchange, symbol)
        timeframes = {
            path.stem: self._timeframe_coverage(exchange, symbol, path.stem)
            for path in sorted(symbol_dir.glob('*.jsonl'))
        }
        manifest = {
            'exchange': exchange,
            'market': prov.get('market', 'spot'),
            'symbol': symbol,
            'source_endpoint': prov.get('source_endpoint', f'ccxt:{exchange}:fetchOHLCV'),
            'fetched_at_utc': prov.get('fetched_at_utc'),
            'timeframes': timeframes,
        }
        manifest_path = self.manifest_path(exchange, symbol)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        return manifest

    def _timeframe_coverage(self, exchange: str, symbol: str, timeframe: str) -> dict[str, object]:
        '''Build the coverage/gaps block for one timeframe from its stored candles.'''
        candles = self.read(exchange, symbol, timeframe)
        interval_ms = timeframe_to_seconds(timeframe) * 1000
        opens = [int(candle[CANDLE_TIME]) for candle in candles]
        first, last = opens[0], opens[-1]
        expected = (last - first) // interval_ms + 1
        return {
            'file': f'{timeframe}.jsonl',
            'interval_ms': interval_ms,
            'first_open_iso': ms_to_iso(first),
            'last_close_iso': ms_to_iso(last + interval_ms),
            'row_count': len(opens),
            'expected_count': expected,
            'missing_count': expected - len(opens),
            'gaps': _gaps(opens, interval_ms),
        }

    def _symbol_dir(self, exchange: str, symbol: str) -> Path:
        safe_symbol = symbol.replace('/', '_')
        return self.root / c.SIM_OHLCV_DIRNAME / exchange / safe_symbol


def _gaps(opens: list[int], interval_ms: int) -> list[dict[str, object]]:
    '''Return the interior gaps between consecutive opens (missing candle runs).'''
    gaps: list[dict[str, object]] = []
    for previous, current in zip(opens, opens[1:]):
        missing = (current - previous) // interval_ms - 1
        if missing > 0:
            gaps.append({
                'after': ms_to_iso(previous),
                'before': ms_to_iso(current),
                'missing': missing,
            })
    return gaps
