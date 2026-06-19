'''Performance snapshot model (cost-basis P&L).

A :class:`PerformanceSnapshot` is the computed P&L view of one pair: position and
cost basis derived from the fill ledger (average-cost method), the current market
value from a live ticker, and the resulting realized, unrealized, and total P&L
plus ROI. It is the answer to DESIGN.md signal #2 — *is the strategy working?* —
and feeds the ``performance`` command's JSON contract.
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['PerformanceSnapshot']


@dataclass(slots=True, frozen=True)
class PerformanceSnapshot:
    '''Cost-basis P&L for one pair at a point in time.

    All monetary fields are in quote terms (e.g. USDT). The position and cost
    basis come from the append-only fill ledger via the average-cost method, or
    from the pair's entry/invested baseline when the ledger has no fills yet.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        position_qty: Base quantity currently held (per the ledger or baseline).
        avg_cost: Average cost per base unit in quote terms, or ``None`` if flat.
        cost_basis: Quote-terms cost basis of the held position.
        current_price: Latest price used to mark the position to market.
        market_value: ``position_qty * current_price`` in quote terms.
        realized_pnl: Cumulative realized P&L from sells (net of fees).
        unrealized_pnl: ``market_value - cost_basis`` for the held position.
        total_pnl: ``realized_pnl + unrealized_pnl``.
        fees_paid: Cumulative fees paid, in quote terms.
        invested: Capital base used as the ROI denominator (baseline or buy cost).
        roi_pct: ``total_pnl / invested * 100``, or ``None`` if nothing invested.
        from_baseline: Whether the position came from the pair baseline (no fills).
        fill_count: Number of ledger fills the snapshot was computed over.
    '''

    symbol: str
    position_qty: float
    avg_cost: float | None
    cost_basis: float
    current_price: float
    market_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    fees_paid: float
    invested: float
    roi_pct: float | None
    from_baseline: bool
    fill_count: int
