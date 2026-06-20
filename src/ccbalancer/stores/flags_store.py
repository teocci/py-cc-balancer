'''Milestone persistence: CRUD over ``flags.json``.

Milestones are agent/user-defined watch-conditions, managed exclusively through
the ``flag`` CLI commands. This store is the only code that reads or writes
``flags.json``; it assigns each milestone a stable integer id and validates entries
via the :class:`Milestone` model. The file carries a ``schema_version`` for the
stable on-disk contract.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.constants import SCHEMA_VERSION
from ccbalancer.exceptions import FlagError
from ccbalancer.models import Milestone

__all__ = ['FlagsStore', 'milestone_to_dict']


def milestone_to_dict(milestone: Milestone) -> dict[str, object]:
    '''Serialize a :class:`Milestone` to a plain dict with a fixed key order.'''
    return {
        'id': milestone.id,
        'symbol': milestone.symbol,
        'metric': milestone.metric,
        'op': milestone.op,
        'threshold': milestone.threshold,
        'note': milestone.note,
        'created_at': milestone.created_at,
    }


@dataclass(slots=True)
class FlagsStore:
    '''Read/write access to the milestones file.

    Attributes:
        path: Location of ``flags.json``.
    '''

    path: Path

    def load(self) -> list[Milestone]:
        '''Return all milestones in registration order (empty if absent).

        Raises:
            FlagError: If the file is unreadable or contains a bad entry.
        '''
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise FlagError(f'Cannot read flags {self.path}: {exc}') from exc
        return [self._from_dict(entry) for entry in data.get('milestones', [])]

    def add(
        self,
        *,
        symbol: str,
        metric: str,
        op: str,
        threshold: float,
        note: str | None,
        created_at: str,
    ) -> Milestone:
        '''Register a new milestone, assigning the next free id; return it.'''
        milestones = self.load()
        milestone = Milestone(
            id=_next_id(milestones),
            symbol=symbol,
            metric=metric,
            op=op,
            threshold=threshold,
            note=note,
            created_at=created_at,
        )
        milestones.append(milestone)
        self.save(milestones)
        return milestone

    def remove(self, milestone_id: int) -> Milestone:
        '''Remove a milestone by id and return it.

        Raises:
            FlagError: If no milestone has that id.
        '''
        milestones = self.load()
        removed = next((m for m in milestones if m.id == milestone_id), None)
        if removed is None:
            raise FlagError(f'No flag with id {milestone_id}; see `ccbalancer flag list`')
        self.save([m for m in milestones if m.id != milestone_id])
        return removed

    def save(self, milestones: list[Milestone]) -> None:
        '''Write all milestones atomically to the flags file.'''
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'schema_version': SCHEMA_VERSION,
            'milestones': [milestone_to_dict(m) for m in milestones],
        }
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def _from_dict(self, entry: dict[str, object]) -> Milestone:
        try:
            return Milestone(
                id=int(entry['id']),
                symbol=str(entry['symbol']).upper(),
                metric=str(entry['metric']),
                op=str(entry['op']),
                threshold=float(entry['threshold']),
                note=_opt_str(entry.get('note')),
                created_at=_opt_str(entry.get('created_at')),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FlagError(f'Invalid milestone entry {entry!r}: {exc}') from exc


def _next_id(milestones: list[Milestone]) -> int:
    '''Smallest unused positive id (max + 1), deterministic from current state.'''
    return max((m.id for m in milestones), default=0) + 1


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)
