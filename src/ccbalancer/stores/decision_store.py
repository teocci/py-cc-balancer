'''Append-only decision memory.

Every rebalance decision the tool makes (on ``plan`` now, ``rebalance`` later) is
recorded as one JSON line in ``decision_log.jsonl`` under the app directory. The
record captures the decision inputs, the signed drift, the full guard pass/fail
ladder, and the proposed order, so an agent can audit *why* the tool decided as it
did — entirely offline, with no exchange access.

The log is the source of the ``decisions`` and ``export`` audit commands. It owns
its own serialization (independent of the read-command JSON) so its on-disk schema
stays stable, and it is the only code that reads or writes the file. Corrupt lines
raise :class:`StateError`.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.constants import SCHEMA_VERSION
from ccbalancer.exceptions import StateError
from ccbalancer.managers.rebalance_manager import GUARD_ORDER
from ccbalancer.models import ProposedOrder, RebalanceDecision

__all__ = ['DecisionStore', 'decision_to_record', 'guard_ladder']

# Guard ladder statuses (derived deterministically from the decision reason).
_PASS = 'pass'
_FAIL = 'fail'
_SKIPPED = 'skipped'


def guard_ladder(decision: RebalanceDecision) -> list[dict[str, str]]:
    '''Reconstruct each guard's pass/fail status from the decision reason.

    Guards run first-failure-wins in :data:`GUARD_ORDER`, so the final reason
    fully determines the ladder: every guard before the triggering one passed,
    the triggering one failed, and the rest were never evaluated. When the
    decision is ``OK`` every guard passed.
    '''
    ladder: list[dict[str, str]] = []
    failed = False
    for guard in GUARD_ORDER:
        if failed:
            status = _SKIPPED
        elif guard is decision.reason:
            status = _FAIL
            failed = True
        else:
            status = _PASS
        ladder.append({'name': guard.value, 'status': status})
    return ladder


def decision_to_record(
    decision: RebalanceDecision,
    *,
    ts: str,
    exchange: str,
    testnet: bool,
    command: str,
) -> dict[str, object]:
    '''Serialize a decision plus audit context into a log record (fixed keys).

    Args:
        decision: The decision to persist.
        ts: UTC ISO-8601 time the decision was made.
        exchange: ccxt exchange id the decision was evaluated against.
        testnet: Whether the sandbox was in effect.
        command: The command that produced the decision (``'plan'``).
    '''
    return {
        'schema_version': SCHEMA_VERSION,
        'ts': ts,
        'command': command,
        'exchange': exchange,
        'testnet': testnet,
        'symbol': decision.symbol,
        'rebalance': decision.rebalance,
        'reason': decision.reason.value,
        'drift_pct': decision.drift_pct,
        'target_volatile_pct': decision.target_volatile_pct,
        'current_volatile_pct': decision.current_volatile_pct,
        'total_value': decision.total_value,
        'last_rebalance_at': decision.last_rebalance_at,
        'days_since_last': decision.days_since_last,
        'guards': guard_ladder(decision),
        'proposed_order': _order_to_dict(decision.proposed_order),
        'detail': decision.detail,
    }


def _order_to_dict(order: ProposedOrder | None) -> dict[str, object] | None:
    if order is None:
        return None
    return {
        'side': order.side.value,
        'amount': order.amount,
        'limit_price': order.limit_price,
        'notional': order.notional,
        'clamped': order.clamped,
    }


@dataclass(slots=True)
class DecisionStore:
    '''Append-only read/write access to ``decision_log.jsonl``.

    Attributes:
        log_path: Location of ``decision_log.jsonl``.
    '''

    log_path: Path

    def append_decision(
        self,
        decision: RebalanceDecision,
        *,
        ts: str,
        exchange: str,
        testnet: bool,
        command: str,
    ) -> dict[str, object]:
        '''Append one decision record and return the serialized record.'''
        record = decision_to_record(
            decision, ts=ts, exchange=exchange, testnet=testnet, command=command
        )
        self.append(record)
        return record

    def append(self, record: dict[str, object]) -> None:
        '''Append one already-serialized record as a JSON line.'''
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, separators=(',', ':'), default=str) + '\n'
        with open(self.log_path, 'a', encoding='utf-8') as handle:
            handle.write(line)

    def load(self) -> list[dict[str, object]]:
        '''Return all decision records in append order (empty if absent).

        Raises:
            StateError: If the file is unreadable or contains a malformed line.
        '''
        if not self.log_path.is_file():
            return []
        try:
            text = self.log_path.read_text(encoding='utf-8')
        except OSError as exc:
            raise StateError(f'Cannot read decision log {self.log_path}: {exc}') from exc
        return [self._parse_line(line) for line in text.splitlines() if line.strip()]

    def _parse_line(self, line: str) -> dict[str, object]:
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise StateError(f'Corrupt decision record in {self.log_path}: {exc}') from exc
