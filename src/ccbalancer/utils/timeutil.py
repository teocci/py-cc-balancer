'''UTC time helpers.

All timestamps in ccbalancer are timezone-aware UTC, serialized as ISO-8601 with
a trailing ``Z``. Centralizing the format here keeps ``state.json`` and
``history.jsonl`` consistent and their values directly comparable.
'''

from __future__ import annotations

from datetime import datetime, timezone

from ccbalancer.exceptions import ConfigError

__all__ = ['now_iso', 'now_ms', 'parse_iso', 'hours_between', 'timeframe_to_seconds', 'ms_to_iso']

# Suffix -> seconds for ccxt-style timeframe strings (e.g. ``15m``, ``4h``).
_TIMEFRAME_UNITS = {
    'm': 60,
    'h': 3600,
    'd': 86400,
    'w': 604800,
}


def now_iso() -> str:
    '''Return the current UTC time as ISO-8601, e.g. ``2026-06-18T12:00:00Z``.'''
    return _format(datetime.now(timezone.utc))


def now_ms() -> int:
    '''Return the current UTC time as epoch milliseconds (ccxt's candle unit).'''
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def parse_iso(value: str) -> datetime:
    '''Parse an ISO-8601 timestamp into a UTC-aware :class:`datetime`.

    A naive input is assumed to be UTC; an offset-aware input is converted to UTC.
    '''
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def hours_between(start: str, end: str) -> float:
    '''Return the number of hours from ``start`` to ``end`` (both ISO-8601).'''
    delta = parse_iso(end) - parse_iso(start)
    return delta.total_seconds() / 3600.0


def timeframe_to_seconds(timeframe: str) -> int:
    '''Convert a ccxt timeframe string (``'15m'``, ``'4h'``, ``'1d'``) to seconds.

    Raises:
        ConfigError: If the timeframe is malformed or uses an unknown unit.
    '''
    if len(timeframe) < 2:
        raise ConfigError(f'Invalid timeframe {timeframe!r}')
    quantity, unit = timeframe[:-1], timeframe[-1]
    seconds = _TIMEFRAME_UNITS.get(unit)
    if seconds is None or not quantity.isdigit() or int(quantity) <= 0:
        raise ConfigError(f'Invalid timeframe {timeframe!r}; expected e.g. 1m, 15m, 4h, 1d, 1w')
    return int(quantity) * seconds


def ms_to_iso(epoch_ms: int) -> str:
    '''Convert epoch milliseconds (ccxt candle time) to an ISO-8601 UTC string.'''
    return _format(datetime.fromtimestamp(epoch_ms / 1000, timezone.utc))


def _format(moment: datetime) -> str:
    iso = moment.astimezone(timezone.utc).isoformat(timespec='seconds')
    return iso.replace('+00:00', 'Z')
