'''Result of reconciling one tracked order against exchange status.'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['ReconcileResult']


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    '''What one order's reconciliation pass observed and booked.

    Attributes:
        symbol: Pair as ``BASE/QUOTE``.
        client_order_id: The tool's deterministic order tag.
        order_id: Exchange order id, or ``None`` if still unresolved (unconfirmed).
        status: Resulting lifecycle status value (see :class:`OrderStatus`).
        newly_filled: Quantity booked to the ledger this pass (the delta).
        total_filled: Cumulative filled quantity reported by the venue.
        remaining: Intended amount not yet filled (``amount − total_filled``).
    '''

    symbol: str
    client_order_id: str
    order_id: str | None
    status: str
    newly_filled: float
    total_filled: float
    remaining: float
