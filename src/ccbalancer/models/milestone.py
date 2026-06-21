'''Agent-defined milestone / watch-condition model.

A :class:`Milestone` is a persistent condition the agent or user registers (via
the ``flag`` commands) for the CLI to evaluate deterministically against live
per-pair snapshots — Layer-2 defines, Layer-1 computes. It is one observed metric
compared against a threshold; the CLI reports whether it is hit, never acting on it.
'''

from __future__ import annotations

from dataclasses import dataclass

from ccbalancer.constants import MILESTONE_METRICS, MILESTONE_OPS
from ccbalancer.exceptions import FlagError

__all__ = ['Milestone']


@dataclass(slots=True, frozen=True)
class Milestone:
    '''One watch-condition: ``<symbol> <metric> <op> <threshold>``.

    Attributes:
        id: Stable integer identifier (assigned by the store on registration).
        symbol: Pair the metric is read from, as ``BASE/QUOTE``.
        metric: Observed metric (one of :data:`MILESTONE_METRICS`).
        op: Comparison operator key (one of :data:`MILESTONE_OPS`).
        threshold: Value the metric is compared against.
        note: Optional free-text note shown when the milestone is reported.
        created_at: UTC ISO-8601 of when the milestone was registered, or ``None``.
    '''

    id: int
    symbol: str
    metric: str
    op: str
    threshold: float
    note: str | None = None
    created_at: str | None = None

    def __post_init__(self) -> None:
        self._validate_symbol()
        self._validate_metric()
        self._validate_op()

    @property
    def expression(self) -> str:
        '''Human-readable form, e.g. ``'price >= 100000'``.'''
        return f'{self.metric} {MILESTONE_OPS[self.op]} {self.threshold:g}'

    def _validate_symbol(self) -> None:
        parts = self.symbol.split('/')
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise FlagError(f'Invalid symbol {self.symbol!r}; expected BASE/QUOTE')

    def _validate_metric(self) -> None:
        if self.metric not in MILESTONE_METRICS:
            allowed = ', '.join(MILESTONE_METRICS)
            raise FlagError(f'Unknown metric {self.metric!r}; choose one of: {allowed}')

    def _validate_op(self) -> None:
        if self.op not in MILESTONE_OPS:
            allowed = ', '.join(MILESTONE_OPS)
            raise FlagError(f'Unknown operator {self.op!r}; choose one of: {allowed}')
