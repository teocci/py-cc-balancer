'''Executed-fill model (cost-basis source).'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['Fill']


@dataclass(slots=True, frozen=True)
class Fill:
    '''One executed fill recorded in ``ledger.jsonl``.

    The ledger is the append-only source of truth for cost-basis and P&L
    (consumed by the performance command in a later phase). Values are taken from
    the exchange's order response at placement time; a resting limit order records
    its intended price/qty until a later run reconciles the actual fill.

    Attributes:
        ts: UTC ISO-8601 timestamp of the fill.
        symbol: Trading pair ``BASE/QUOTE``.
        side: ``'buy'`` or ``'sell'``.
        price: Fill price in quote terms (average fill, or limit price if resting).
        qty: Base quantity filled (or ordered, if not yet filled).
        fee: Fee paid, in ``fee_currency`` terms.
        fee_currency: Currency the fee was charged in, or ``None`` if unknown.
        order_id: Exchange order id the fill belongs to, or ``None``.
    '''

    ts: str
    symbol: str
    side: str
    price: float
    qty: float
    fee: float
    fee_currency: str | None
    order_id: str | None
