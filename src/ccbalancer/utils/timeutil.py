'''UTC time helpers.

All timestamps in ccbalancer are timezone-aware UTC, serialized as ISO-8601 with
a trailing ``Z``. Centralizing the format here keeps ``state.json`` and
``history.jsonl`` consistent and their values directly comparable.
'''

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ['now_iso', 'parse_iso', 'hours_between']


def now_iso() -> str:
    '''Return the current UTC time as ISO-8601, e.g. ``2026-06-18T12:00:00Z``.'''
    return _format(datetime.now(timezone.utc))


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


def _format(moment: datetime) -> str:
    iso = moment.astimezone(timezone.utc).isoformat(timespec='seconds')
    return iso.replace('+00:00', 'Z')
