'''Load and represent an external target-volatile schedule for backtests.

A *target schedule* is a forward-filled step function of the desired volatile-side
target over time, supplied to ``simulation run --targets``. Each record moves the
target from its decision bar onward; before the first record the pair's configured
target applies. The file is JSONL — one ``{"date": <ISO-8601>, "target_volatile_pct":
<0..100>}`` record per line, ascending by date.

The schedule is validated on load (each target in ``[0, 100]``; dates strictly
increasing) and exposes a bisect lookup by candle-open time (:meth:`TargetSchedule.target_at`)
plus a stable :meth:`TargetSchedule.digest` so a run's id stays deterministic and
unique per schedule.
'''

from __future__ import annotations

import bisect
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer import constants as c
from ccbalancer.exceptions import StateError
from ccbalancer.utils.timeutil import iso_to_ms

__all__ = ['TargetSchedule', 'load_target_schedule']

_DIGEST_LENGTH = 12


@dataclass(frozen=True)
class TargetSchedule:
    '''A forward-filled step function of the volatile-side target over time.

    Attributes:
        steps: ``(effective_ms, target_volatile_pct)`` pairs, strictly increasing
            by ``effective_ms``. Empty is never constructed (an empty file is
            rejected on load).
    '''

    steps: tuple[tuple[int, float], ...]

    def __post_init__(self) -> None:
        # Precompute the parallel key array once for O(log n) lookups on the hot
        # replay path. Frozen dataclass → set via object.__setattr__.
        object.__setattr__(self, '_opens', tuple(effective_ms for effective_ms, _ in self.steps))

    def target_at(self, open_ms: int) -> float | None:
        '''Return the scheduled target in effect at ``open_ms``.

        Returns ``None`` when ``open_ms`` precedes the first step (the caller then
        applies the pair's configured target).
        '''
        idx = bisect.bisect_right(self._opens, open_ms) - 1  # type: ignore[attr-defined]
        if idx < 0:
            return None
        return self.steps[idx][1]

    def covers_start(self, start_ms: int) -> bool:
        '''Whether a step is at/before ``start_ms`` (the recommended alignment).'''
        return bool(self.steps) and self.steps[0][0] <= start_ms

    def digest(self) -> str:
        '''Return a short stable digest of the steps for run-id determinism.'''
        canonical = ';'.join(f'{effective_ms}:{pct}' for effective_ms, pct in self.steps)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:_DIGEST_LENGTH]


def load_target_schedule(path: Path) -> TargetSchedule:
    '''Parse and validate a target-schedule JSONL file.

    Args:
        path: Path to the ``.jsonl`` schedule.

    Returns:
        The validated :class:`TargetSchedule`.

    Raises:
        StateError: If the file is unreadable, empty, malformed, carries a target
            outside ``[0, 100]``, or its dates are not strictly increasing.
    '''
    steps = _parse_steps(_read(path), path)
    if not steps:
        raise StateError(f'Target schedule {path} is empty; add at least one record')
    _validate_increasing(steps, path)
    return TargetSchedule(tuple(steps))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except OSError as exc:
        raise StateError(f'Cannot read target schedule {path}: {exc}') from exc


def _parse_steps(text: str, path: Path) -> list[tuple[int, float]]:
    '''Parse each non-blank line into a validated ``(effective_ms, target_pct)``.'''
    steps: list[tuple[int, float]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        steps.append(_parse_line(line, lineno, path))
    return steps


def _parse_line(line: str, lineno: int, path: Path) -> tuple[int, float]:
    try:
        record = json.loads(line)
    except json.JSONDecodeError as exc:
        raise StateError(f'{path} line {lineno}: not valid JSON: {exc}') from exc
    if not isinstance(record, dict) or 'date' not in record or 'target_volatile_pct' not in record:
        raise StateError(
            f'{path} line {lineno}: each record needs "date" and "target_volatile_pct"'
        )
    effective_ms = iso_to_ms(str(record['date']))
    pct = _target_pct(record['target_volatile_pct'], lineno, path)
    return effective_ms, pct


def _target_pct(value: object, lineno: int, path: Path) -> float:
    try:
        pct = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise StateError(f'{path} line {lineno}: target_volatile_pct must be a number') from exc
    if not 0.0 <= pct <= c.RATIO_TOTAL_PCT:
        raise StateError(
            f'{path} line {lineno}: target_volatile_pct {pct} out of range [0, {c.RATIO_TOTAL_PCT}]'
        )
    return pct


def _validate_increasing(steps: list[tuple[int, float]], path: Path) -> None:
    '''Raise unless every step's date is strictly after the previous one.'''
    for (prev_ms, _), (curr_ms, _) in zip(steps, steps[1:]):
        if curr_ms <= prev_ms:
            raise StateError(f'{path}: dates must be strictly increasing (UTC)')
