'''Rebalance state and history models.'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['RebalanceState', 'HistoryEvent']


@dataclass(slots=True, frozen=True)
class RebalanceState:
    '''Most recent rebalance event for a pair (stored in ``state.json``).

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        last_rebalance_at: UTC ISO-8601 timestamp of the last rebalance.
        last_side: ``'buy'`` or ``'sell'``.
        last_amount: Base quantity of the last order.
        last_price: Limit price of the last order.
        last_drift_pct: Drift corrected by the last rebalance.
        last_reason: Decision reason recorded at the time.
    '''

    symbol: str
    last_rebalance_at: str
    last_side: str
    last_amount: float
    last_price: float
    last_drift_pct: float
    last_reason: str


@dataclass(slots=True, frozen=True)
class HistoryEvent:
    '''One append-only record in ``history.jsonl``.

    Attributes:
        ts: UTC ISO-8601 timestamp of the event.
        symbol: Trading pair ``BASE/QUOTE``.
        side: ``'buy'`` or ``'sell'``.
        amount: Base quantity ordered.
        price: Limit price in quote terms.
        notional: Order value in quote terms.
        drift_pct: Drift at the time of the event.
        reason: Decision reason.
        exchange: ccxt exchange id.
        testnet: Whether the order targeted the testnet/sandbox.
        order_id: Exchange order id, if returned.
        status: Lifecycle status (e.g. ``'submitted'``).
    '''

    ts: str
    symbol: str
    side: str
    amount: float
    price: float
    notional: float
    drift_pct: float
    reason: str
    exchange: str
    testnet: bool
    order_id: str | None
    status: str
