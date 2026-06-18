'''Balance and per-pair market snapshot models.'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['AssetBalance', 'PairSnapshot']


@dataclass(slots=True, frozen=True)
class AssetBalance:
    '''Free and total holdings of a single asset.

    Attributes:
        asset: Asset code (e.g. ``'BTC'``).
        free: Amount available to trade.
        total: Total amount including funds locked in open orders.
    '''

    asset: str
    free: float
    total: float


@dataclass(slots=True, frozen=True)
class PairSnapshot:
    '''Point-in-time view of one pair: balances, prices, and last rebalance.

    All quote-denominated math is derived by the rebalance manager; this model
    carries only raw observed values plus injected state.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        base_total: Total base asset held.
        base_free: Base asset available to trade.
        stable_total: Total quote asset held.
        stable_free: Quote asset available to trade.
        price: Reference price (last/mid) in quote terms.
        bid: Best bid price.
        ask: Best ask price.
        amount_precision: Decimal places allowed for order amount, if known.
        market_active: Whether the market is tradable.
        last_rebalance_at: UTC ISO-8601 of the last rebalance, or ``None``.
    '''

    symbol: str
    base_total: float
    base_free: float
    stable_total: float
    stable_free: float
    price: float
    bid: float
    ask: float
    amount_precision: int | None
    market_active: bool
    last_rebalance_at: str | None
