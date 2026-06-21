'''Evaluate agent-defined milestones against live snapshots (report hits).

:class:`FlagsManager` is the Layer-1 computation behind the agent's Layer-2
watch-conditions: given the registered :class:`Milestone` objects and the current
per-pair ``(snapshot, decision)`` context, it reports for each whether its
condition is hit, missed, or not evaluable. It is pure — no I/O — so the same
inputs always yield the same verdicts.

A milestone's metric is read from the pair it names: ``price`` from the snapshot;
``drift_pct``, ``volatile_pct`` (current allocation), and ``value`` (total pair
value) from the decision. A milestone whose symbol is not in the live context
(not a configured pair, or unfetchable) is reported as ``unknown``.
'''

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccbalancer.models import Milestone, PairSnapshot, RebalanceDecision

__all__ = ['FlagsManager', 'Context']

# Per-symbol live context a milestone is evaluated against.
Context = 'dict[str, tuple[PairSnapshot, RebalanceDecision]]'

_HIT = 'hit'
_MISS = 'miss'
_UNKNOWN = 'unknown'
_EQ_REL_TOL = 1e-9


@dataclass(slots=True, frozen=True)
class FlagsManager:
    '''Evaluate milestones against the current per-pair context (pure, no I/O).'''

    def evaluate(
        self,
        milestones: list[Milestone],
        context: dict[str, tuple[PairSnapshot, RebalanceDecision]],
    ) -> list[dict[str, object]]:
        '''Return one result record per milestone, in registration order.'''
        return [_evaluate_one(m, context.get(m.symbol)) for m in milestones]


def _evaluate_one(
    milestone: Milestone,
    pair_context: tuple[PairSnapshot, RebalanceDecision] | None,
) -> dict[str, object]:
    value = None if pair_context is None else _metric_value(milestone.metric, pair_context)
    if value is None:
        status = _UNKNOWN
    elif _compare(milestone.op, value, milestone.threshold):
        status = _HIT
    else:
        status = _MISS
    return {
        'id': milestone.id,
        'symbol': milestone.symbol,
        'metric': milestone.metric,
        'op': milestone.op,
        'threshold': milestone.threshold,
        'expression': milestone.expression,
        'note': milestone.note,
        'current_value': value,
        'status': status,
    }


def _metric_value(
    metric: str, pair_context: tuple[PairSnapshot, RebalanceDecision]
) -> float | None:
    snapshot, decision = pair_context
    if metric == 'price':
        return snapshot.price
    if metric == 'drift_pct':
        return decision.drift_pct
    if metric == 'volatile_pct':
        return decision.current_volatile_pct
    if metric == 'value':
        return decision.total_value
    return None


def _compare(op: str, value: float, threshold: float) -> bool:
    if op == 'ge':
        return value >= threshold
    if op == 'le':
        return value <= threshold
    if op == 'gt':
        return value > threshold
    if op == 'lt':
        return value < threshold
    return math.isclose(value, threshold, rel_tol=_EQ_REL_TOL)
