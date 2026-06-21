'''Local rebalance state and history persistence.

Two files live under the app directory: ``state.json`` holds the most recent
rebalance event per pair (overwritten on each rebalance), and ``history.jsonl`` is
an append-only log of every event. This store is the only code that reads or
writes them; the exchange is never touched here. Reads of corrupt files raise
:class:`StateError`.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.exceptions import StateError
from ccbalancer.models import HistoryEvent, RebalanceState

__all__ = ['StateStore', 'state_to_dict', 'event_to_dict']


def state_to_dict(state: RebalanceState) -> dict[str, object]:
    '''Serialize a :class:`RebalanceState` to a plain dict.'''
    return {
        'symbol': state.symbol,
        'last_rebalance_at': state.last_rebalance_at,
        'last_side': state.last_side,
        'last_amount': state.last_amount,
        'last_price': state.last_price,
        'last_drift_pct': state.last_drift_pct,
        'last_reason': state.last_reason,
    }


def event_to_dict(event: HistoryEvent) -> dict[str, object]:
    '''Serialize a :class:`HistoryEvent` to a plain dict.'''
    return {
        'ts': event.ts,
        'symbol': event.symbol,
        'side': event.side,
        'amount': event.amount,
        'price': event.price,
        'notional': event.notional,
        'drift_pct': event.drift_pct,
        'reason': event.reason,
        'exchange': event.exchange,
        'testnet': event.testnet,
        'order_id': event.order_id,
        'status': event.status,
    }


@dataclass(slots=True)
class StateStore:
    '''Read/write access to ``state.json`` and ``history.jsonl``.

    Attributes:
        state_path: Location of ``state.json``.
        history_path: Location of ``history.jsonl``.
    '''

    state_path: Path
    history_path: Path

    def load(self) -> dict[str, RebalanceState]:
        '''Return all stored states keyed by symbol (empty if the file is absent).

        Raises:
            StateError: If the file is unreadable or contains a bad entry.
        '''
        if not self.state_path.is_file():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f'Cannot read state {self.state_path}: {exc}') from exc
        states = data.get('states', {})
        return {symbol: self._from_dict(entry) for symbol, entry in states.items()}

    def get(self, symbol: str) -> RebalanceState | None:
        '''Return the stored state for ``symbol`` (case-insensitive) or ``None``.'''
        return self.load().get(symbol.upper())

    def last_rebalance_at(self, symbol: str) -> str | None:
        '''Return the last rebalance timestamp for ``symbol``, or ``None``.'''
        state = self.get(symbol)
        return state.last_rebalance_at if state else None

    def save(self, state: RebalanceState) -> None:
        '''Upsert ``state`` into ``state.json`` (atomic write).'''
        states = self.load()
        states[state.symbol] = state
        payload = {'states': {symbol: state_to_dict(s) for symbol, s in states.items()}}
        self._write_atomic(self.state_path, json.dumps(payload, indent=2))

    def append_event(self, event: HistoryEvent) -> None:
        '''Append one event as a JSON line to ``history.jsonl``.'''
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event_to_dict(event)) + '\n'
        with open(self.history_path, 'a', encoding='utf-8') as handle:
            handle.write(line)

    def record(self, state: RebalanceState, event: HistoryEvent) -> None:
        '''Persist the latest state and append the matching history event.'''
        self.save(state)
        self.append_event(event)

    def load_history(self) -> list[dict[str, object]]:
        '''Return every ``history.jsonl`` event as a dict, in append order.

        Records are returned raw (not parsed into models) so the audit reader
        tolerates older log schemas. Empty if the file is absent.

        Raises:
            StateError: If the file is unreadable or contains a malformed line.
        '''
        if not self.history_path.is_file():
            return []
        try:
            text = self.history_path.read_text(encoding='utf-8')
        except OSError as exc:
            raise StateError(f'Cannot read history {self.history_path}: {exc}') from exc
        return [self._parse_event(line) for line in text.splitlines() if line.strip()]

    def _parse_event(self, line: str) -> dict[str, object]:
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise StateError(f'Corrupt history record in {self.history_path}: {exc}') from exc

    def _from_dict(self, entry: dict[str, object]) -> RebalanceState:
        try:
            return RebalanceState(
                symbol=str(entry['symbol']),
                last_rebalance_at=str(entry['last_rebalance_at']),
                last_side=str(entry['last_side']),
                last_amount=float(entry['last_amount']),
                last_price=float(entry['last_price']),
                last_drift_pct=float(entry['last_drift_pct']),
                last_reason=str(entry['last_reason']),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StateError(f'Invalid state entry {entry!r}: {exc}') from exc

    def _write_atomic(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(content, encoding='utf-8')
        tmp.replace(path)
