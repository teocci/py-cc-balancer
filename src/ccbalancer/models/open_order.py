'''An outstanding order tracked for reconciliation.'''

from __future__ import annotations

from dataclasses import dataclass

from ccbalancer.enums.order_status import OrderStatus

__all__ = ['OpenOrder']


@dataclass(frozen=True, slots=True)
class OpenOrder:
    '''One order recorded in the open-orders store, keyed by client-order-id.

    Written write-ahead (before ``create_order``) so a placement timeout never
    strands an order, and carried until the reconciler books its final fill.

    Attributes:
        client_order_id: Deterministic ``CCB_PREFIX`` tag; the store key.
        order_id: Exchange order id, or ``None`` until the placement is confirmed.
        symbol: Pair as ``BASE/QUOTE``.
        side: ``'buy'`` or ``'sell'`` (ccxt string).
        amount: Intended order amount (base units).
        limit_price: Intended limit price (quote).
        status: Lifecycle state (see :class:`OrderStatus`).
        filled_booked: Cumulative filled qty already written to the ledger; the
            partial-fill delta guard against double-booking.
        placed_at: ISO-8601 placement time.
    '''

    client_order_id: str
    order_id: str | None
    symbol: str
    side: str
    amount: float
    limit_price: float
    status: OrderStatus
    filled_booked: float
    placed_at: str
