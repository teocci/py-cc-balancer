'''Regime signal models (DESIGN.md signal #3).

The regime signal answers *should the target ratio change?* It compares the price
now against the price when the current target ratio was chosen and, once the move
exceeds the review band, raises a flag plus a deterministic suggested ratio and a
set of what-if scenarios. The CLI computes these facts; it never changes the ratio
(that judgment is Layer 2).
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['RegimeScenario', 'RegimeSignal']


@dataclass(slots=True, frozen=True)
class RegimeScenario:
    '''A candidate target ratio and the value/risk split it implies right now.

    Attributes:
        volatile_pct: Candidate share held in the volatile base asset.
        stable_pct: Candidate share held in the stable quote asset.
        volatile_value: At-risk value (quote terms) under this ratio now.
        stable_value: Stable value (quote terms) under this ratio now.
        is_current: Whether this rung equals the pair's current target ratio.
        is_suggested: Whether this rung is the heuristic-suggested ratio.
    '''

    volatile_pct: float
    stable_pct: float
    volatile_value: float
    stable_value: float
    is_current: bool
    is_suggested: bool


@dataclass(slots=True, frozen=True)
class RegimeSignal:
    '''Price-variance-since-target-set view of one pair (the regime fact).

    All monetary fields are in quote terms. ``price_change_pct`` and the suggested
    ratio are ``None`` when the pair has no ``target_set_price`` baseline.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        target_set_price: Price when the target ratio was chosen, or ``None``.
        target_set_ts: UTC ISO-8601 of when the target was set, or ``None``.
        current_price: Latest price used for the comparison.
        price_change_pct: Signed percent move since the target was set, or ``None``.
        review_band_pct: Move magnitude beyond which a review is flagged.
        direction: ``'up'``, ``'down'``, ``'flat'``, or ``'none'`` (no baseline).
        flag: Whether the move warrants a target-ratio review.
        total_value: Total pair value in quote terms.
        current_volatile_pct: The pair's current target share for the base asset.
        current_stable_pct: The pair's current target share for the quote asset.
        suggested_volatile_pct: Heuristic-suggested base share, or ``None``.
        suggested_stable_pct: Heuristic-suggested quote share, or ``None``.
        scenarios: What-if ratios with their value/risk split (the current target
            is always present; the suggested rung is flagged).
    '''

    symbol: str
    target_set_price: float | None
    target_set_ts: str | None
    current_price: float
    price_change_pct: float | None
    review_band_pct: float
    direction: str
    flag: bool
    total_value: float
    current_volatile_pct: float
    current_stable_pct: float
    suggested_volatile_pct: float | None
    suggested_stable_pct: float | None
    scenarios: tuple[RegimeScenario, ...]
