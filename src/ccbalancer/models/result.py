'''Execution result model.'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['ExecutionResult']


@dataclass(slots=True, frozen=True)
class ExecutionResult:
    '''Outcome of attempting to act on a rebalance decision for one pair.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        placed: Whether an order was actually placed.
        order_id: Exchange order id, if any.
        status: One of ``'submitted'``, ``'skipped'``, ``'dry_run'``, ``'failed'``.
        reason: Decision reason or failure cause.
        detail: Short, deterministic human-readable note.
    '''

    symbol: str
    placed: bool
    order_id: str | None
    status: str
    reason: str
    detail: str = ''
