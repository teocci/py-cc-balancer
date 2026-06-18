'''Render read-command results as stable JSON or human-readable text.

The read commands (`status`, `plan`) share one serialization path so their JSON
contract stays stable for agent consumers: keys emit in a fixed order, enum
reasons render as their string values, and every response is wrapped in an
envelope carrying ``schema_version`` plus the exchange context. Text output is a
compact one-line-per-pair summary for humans.

Both views are built from a :class:`~ccbalancer.models.RebalanceDecision` (and,
for `status`, its originating :class:`~ccbalancer.models.PairSnapshot`); the
quote-denominated metrics are computed once by the rebalance manager and reused
here, never recomputed.
'''

from __future__ import annotations

from typing import TYPE_CHECKING

from ccbalancer.constants import SCHEMA_VERSION

if TYPE_CHECKING:
    from ccbalancer.models import PairSnapshot, ProposedOrder, RebalanceDecision

__all__ = [
    'order_to_dict',
    'decision_to_dict',
    'status_to_dict',
    'plan_response',
    'status_response',
    'plan_lines',
    'status_lines',
]

# Pairs of (snapshot, decision) carried through the status path.
StatusRow = 'tuple[PairSnapshot, RebalanceDecision]'


def order_to_dict(order: ProposedOrder) -> dict[str, object]:
    '''Serialize a :class:`ProposedOrder` with a fixed key order.'''
    return {
        'side': order.side.value,
        'amount': order.amount,
        'limit_price': order.limit_price,
        'notional': order.notional,
        'clamped': order.clamped,
    }


def decision_to_dict(decision: RebalanceDecision) -> dict[str, object]:
    '''Serialize a :class:`RebalanceDecision` with a fixed key order.'''
    order = decision.proposed_order
    return {
        'symbol': decision.symbol,
        'rebalance': decision.rebalance,
        'reason': decision.reason.value,
        'drift_pct': decision.drift_pct,
        'target_volatile_pct': decision.target_volatile_pct,
        'current_volatile_pct': decision.current_volatile_pct,
        'total_value': decision.total_value,
        'last_rebalance_at': decision.last_rebalance_at,
        'days_since_last': decision.days_since_last,
        'proposed_order': order_to_dict(order) if order else None,
        'detail': decision.detail,
    }


def status_to_dict(snapshot: PairSnapshot, decision: RebalanceDecision) -> dict[str, object]:
    '''Serialize one pair's allocation status (current vs target + holdings).'''
    return {
        'symbol': snapshot.symbol,
        'target_volatile_pct': decision.target_volatile_pct,
        'current_volatile_pct': decision.current_volatile_pct,
        'drift_pct': decision.drift_pct,
        'total_value': decision.total_value,
        'base_total': snapshot.base_total,
        'stable_total': snapshot.stable_total,
        'price': snapshot.price,
        'last_rebalance_at': decision.last_rebalance_at,
        'days_since_last': decision.days_since_last,
    }


def plan_response(decisions: list[RebalanceDecision], meta: dict[str, object]) -> dict[str, object]:
    '''Build the `plan` JSON envelope from per-pair decisions.'''
    return _envelope('plan', meta, {'pairs': [decision_to_dict(d) for d in decisions]})


def status_response(rows: list[StatusRow], meta: dict[str, object]) -> dict[str, object]:
    '''Build the `status` JSON envelope from per-pair (snapshot, decision) rows.'''
    pairs = [status_to_dict(snapshot, decision) for snapshot, decision in rows]
    return _envelope('status', meta, {'pairs': pairs})


def plan_lines(decisions: list[RebalanceDecision]) -> list[str]:
    '''Render `plan` decisions as one text line per pair.'''
    return [_plan_line(decision) for decision in decisions]


def status_lines(rows: list[StatusRow]) -> list[str]:
    '''Render `status` rows as one text line per pair.'''
    return [_status_line(snapshot, decision) for snapshot, decision in rows]


def _envelope(command: str, meta: dict[str, object], body: dict[str, object]) -> dict[str, object]:
    return {
        'schema_version': SCHEMA_VERSION,
        'command': command,
        'exchange': meta['exchange'],
        'testnet': meta['testnet'],
        'generated_at': meta['generated_at'],
        **body,
    }


def _plan_line(decision: RebalanceDecision) -> str:
    drift = f'{decision.drift_pct:+.2f}pp'
    action = _action(decision)
    return f'{decision.symbol}  {action}  drift {drift}  [{decision.reason.value}]'


def _action(decision: RebalanceDecision) -> str:
    order = decision.proposed_order
    if not decision.rebalance or order is None:
        return 'hold'
    return (
        f'REBALANCE {order.side.value} {order.amount:g} @ {order.limit_price:g} '
        f'({order.notional:.2f} {_quote(decision.symbol)})'
    )


def _status_line(snapshot: PairSnapshot, decision: RebalanceDecision) -> str:
    last = _format_last(decision.last_rebalance_at, decision.days_since_last)
    return (
        f'{snapshot.symbol}  current {decision.current_volatile_pct:.2f}% / '
        f'target {decision.target_volatile_pct:.2f}%  drift {decision.drift_pct:+.2f}pp  '
        f'value {decision.total_value:.2f} {_quote(snapshot.symbol)}  last {last}'
    )


def _format_last(last_at: str | None, days_since: float | None) -> str:
    if not last_at:
        return 'never'
    if days_since is None:
        return last_at
    return f'{last_at} ({days_since:.1f}d ago)'


def _quote(symbol: str) -> str:
    parts = symbol.split('/')
    return parts[1] if len(parts) == 2 else ''
