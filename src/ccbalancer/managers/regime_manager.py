'''Regime signal: should the target ratio be reviewed? (DESIGN.md signal #3).

:class:`RegimeManager` compares the price now against the price recorded when the
pair's target ratio was set (``target_set_price``). Once that move exceeds the
review band it raises a flag, proposes a deterministic suggested ratio, and lays
out what-if scenarios so the brain can decide whether to de-risk. It is pure: the
same pair + snapshot always yields the same :class:`RegimeSignal`, and it never
changes the ratio (that judgment is Layer 2).

The suggested ratio and the scenarios share one mechanism — a fixed ladder of
candidate volatile shares (:data:`REGIME_SCENARIO_VOLATILE_PCTS`) with the pair's
current target injected as a rung. A run-up beyond the band steps one rung toward
less risk (lower volatile share); a drop steps one rung toward more; a move within
the band keeps the current ratio.
'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer.constants import (
    DEFAULT_TARGET_REVIEW_BAND_PCT,
    RATIO_TOTAL_PCT,
    REGIME_SCENARIO_VOLATILE_PCTS,
)
from ccbalancer.models import RegimeScenario, RegimeSignal

if TYPE_CHECKING:
    from ccbalancer.config import AppConfig
    from ccbalancer.models import PairConfig, PairSnapshot

__all__ = ['RegimeManager']

_PCT = 100.0
_UP = 'up'
_DOWN = 'down'
_FLAT = 'flat'
_NONE = 'none'


@dataclass(slots=True, frozen=True)
class RegimeManager:
    '''Compute the regime signal for a pair (pure, no I/O).

    Attributes:
        review_band_pct: Price-move magnitude (since target-set) beyond which the
            target ratio is flagged for review.
        scenario_volatile_pcts: Candidate volatile shares for the what-if ladder.
    '''

    review_band_pct: float = DEFAULT_TARGET_REVIEW_BAND_PCT
    scenario_volatile_pcts: tuple[float, ...] = REGIME_SCENARIO_VOLATILE_PCTS

    @classmethod
    def from_config(cls, config: AppConfig) -> RegimeManager:
        '''Build a manager from a resolved :class:`AppConfig`.'''
        return cls(review_band_pct=config.target_review_band_pct)

    def signal(self, pair: PairConfig, snapshot: PairSnapshot) -> RegimeSignal:
        '''Evaluate the regime signal for one pair against a live snapshot.'''
        price = snapshot.price
        total = snapshot.base_total * price + snapshot.stable_total
        change = _price_change(pair.target_set_price, price)
        direction = self._direction(change)
        ladder = self._ladder(pair.target_volatile_pct)
        suggested = self._suggested(pair.target_volatile_pct, ladder, direction, change)
        return RegimeSignal(
            symbol=pair.symbol,
            target_set_price=pair.target_set_price,
            target_set_ts=pair.target_set_ts,
            current_price=price,
            price_change_pct=change,
            review_band_pct=self.review_band_pct,
            direction=direction,
            flag=direction in (_UP, _DOWN),
            total_value=total,
            current_volatile_pct=pair.target_volatile_pct,
            current_stable_pct=pair.target_stable_pct,
            suggested_volatile_pct=suggested,
            suggested_stable_pct=None if suggested is None else RATIO_TOTAL_PCT - suggested,
            scenarios=_scenarios(ladder, total, pair.target_volatile_pct, suggested),
        )

    def _direction(self, change: float | None) -> str:
        if change is None:
            return _NONE
        if change > self.review_band_pct:
            return _UP
        if change < -self.review_band_pct:
            return _DOWN
        return _FLAT

    def _ladder(self, current_volatile: float) -> tuple[float, ...]:
        '''Candidate volatile shares, descending, with the current target included.'''
        rungs = set(self.scenario_volatile_pcts) | {current_volatile}
        return tuple(sorted(rungs, reverse=True))

    def _suggested(
        self,
        current_volatile: float,
        ladder: tuple[float, ...],
        direction: str,
        change: float | None,
    ) -> float | None:
        if change is None:
            return None
        index = ladder.index(current_volatile)
        if direction == _UP:  # ran up: step one rung toward less risk
            index = min(index + 1, len(ladder) - 1)
        elif direction == _DOWN:  # dropped: step one rung toward more risk
            index = max(index - 1, 0)
        return ladder[index]


def _price_change(target_set_price: float | None, price: float) -> float | None:
    '''Signed percent move since the target was set, or ``None`` without a baseline.'''
    if not target_set_price or target_set_price <= 0:
        return None
    return (price - target_set_price) / target_set_price * _PCT


def _scenarios(
    ladder: tuple[float, ...],
    total: float,
    current_volatile: float,
    suggested: float | None,
) -> tuple[RegimeScenario, ...]:
    return tuple(
        RegimeScenario(
            volatile_pct=volatile,
            stable_pct=RATIO_TOTAL_PCT - volatile,
            volatile_value=total * volatile / _PCT,
            stable_value=total * (RATIO_TOTAL_PCT - volatile) / _PCT,
            is_current=volatile == current_volatile,
            is_suggested=suggested is not None and volatile == suggested,
        )
        for volatile in ladder
    )
