'''Rebalance decision models.'''

from __future__ import annotations

from dataclasses import dataclass

from ccbalancer.enums.side import OrderSide
from ccbalancer.enums.skip_reason import SkipReason

__all__ = ['ProposedOrder', 'RebalanceDecision']


@dataclass(slots=True, frozen=True)
class ProposedOrder:
    '''A limit order the tool would place to correct drift.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        side: Buy or sell the base asset.
        amount: Base quantity, rounded to market precision.
        limit_price: Limit price in quote terms.
        notional: Order value in quote terms (``amount * limit_price``).
        clamped: Whether the amount was reduced to honor ``max_trade_notional``.
    '''

    symbol: str
    side: OrderSide
    amount: float
    limit_price: float
    notional: float
    clamped: bool = False


@dataclass(slots=True, frozen=True)
class RebalanceDecision:
    '''Outcome of evaluating one pair against its target.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        rebalance: Whether a trade is warranted.
        reason: ``OK`` when rebalancing, else why it was skipped.
        drift_pct: Signed drift of the volatile share from target (pp).
        target_volatile_pct: Configured target share for the base asset.
        current_volatile_pct: Observed share of value in the base asset.
        total_value: Total pair value in quote terms.
        last_rebalance_at: UTC ISO-8601 of the last rebalance, or ``None``.
        days_since_last: Days since the last rebalance, or ``None``.
        proposed_order: The order to place when ``rebalance`` is true, else ``None``.
        detail: Short, deterministic human-readable note.
    '''

    symbol: str
    rebalance: bool
    reason: SkipReason
    drift_pct: float
    target_volatile_pct: float
    current_volatile_pct: float
    total_value: float
    last_rebalance_at: str | None = None
    days_since_last: float | None = None
    proposed_order: ProposedOrder | None = None
    detail: str = ''
