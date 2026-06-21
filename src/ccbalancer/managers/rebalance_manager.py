'''Pure rebalance decision logic.

:class:`RebalanceManager` turns a pair's target plus a point-in-time
:class:`~ccbalancer.models.PairSnapshot` into a :class:`RebalanceDecision`
through an ordered chain of guards. It performs no I/O and places no orders, so
the same inputs always yield the same decision: it is unit-testable without
mocks and auditable offline.

Drift is the signed gap between the volatile share held now and the target
share, in percentage points::

    drift_pct = current_volatile_pct - target_volatile_pct

Positive drift means too much base is held (SELL); negative means too little
(BUY). Guards run in a fixed order and the first failure wins: ``ABNORMAL_PRICE``
-> ``MARKET_UNAVAILABLE`` -> ``TOO_SOON`` (optional) -> ``WITHIN_BAND`` ->
``BELOW_MIN_NOTIONAL`` -> ``INSUFFICIENT_BALANCE`` -> max-trade clamp -> ``OK``.
'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer.constants import (
    DEFAULT_LIMIT_OFFSET_PCT,
    DEFAULT_MIN_INTERVAL_HOURS,
    DEFAULT_QUOTE_SANITY_PCT,
)
from ccbalancer.enums.side import OrderSide
from ccbalancer.enums.skip_reason import SkipReason
from ccbalancer.models import PairConfig, PairSnapshot, ProposedOrder, RebalanceDecision
from ccbalancer.utils.money import notional as quote_notional
from ccbalancer.utils.money import round_amount
from ccbalancer.utils.timeutil import hours_between, now_iso

if TYPE_CHECKING:
    from ccbalancer.config import AppConfig

__all__ = ['RebalanceManager', 'GUARD_ORDER']

_PCT = 100.0
_HOURS_PER_DAY = 24.0

# Fixed evaluation order of the skip guards (first failure wins). This is the
# source of truth for the order in :meth:`RebalanceManager.decide`; the decision
# log reconstructs each guard's pass/fail ladder from it. ``OK`` is the outcome
# when every guard passes and so is not itself a guard.
GUARD_ORDER = (
    SkipReason.ABNORMAL_PRICE,
    SkipReason.MARKET_UNAVAILABLE,
    SkipReason.TOO_SOON,
    SkipReason.WITHIN_BAND,
    SkipReason.BELOW_MIN_NOTIONAL,
    SkipReason.INSUFFICIENT_BALANCE,
)


@dataclass(slots=True, frozen=True)
class _Metrics:
    '''Quote-denominated metrics derived once per :meth:`RebalanceManager.decide`.

    Attributes:
        symbol: Trading pair ``BASE/QUOTE``.
        target_volatile_pct: Configured target share for the base asset.
        current_volatile_pct: Observed share of value held in the base asset.
        drift_pct: Signed gap of the volatile share from target (pp).
        total_value: Total pair value in quote terms.
        delta_value: Quote value that must move to restore the target.
        last_rebalance_at: UTC ISO-8601 of the last rebalance, or ``None``.
        days_since_last: Days since the last rebalance, or ``None``.
    '''

    symbol: str
    target_volatile_pct: float
    current_volatile_pct: float
    drift_pct: float
    total_value: float
    delta_value: float
    last_rebalance_at: str | None
    days_since_last: float | None


@dataclass(slots=True, frozen=True)
class RebalanceManager:
    '''Decide whether and how to rebalance one pair (pure, no I/O).

    Attributes:
        quote_sanity_pct: Max allowed deviation of ``last`` from the bid/ask mid
            before the ticker is rejected as ``ABNORMAL_PRICE``.
        limit_offset_pct: Passive offset applied to the touch when pricing the
            limit order (0 = at best bid/ask).
        min_interval_hours: Optional cadence guard; 0 disables ``TOO_SOON``.
    '''

    quote_sanity_pct: float = DEFAULT_QUOTE_SANITY_PCT
    limit_offset_pct: float = DEFAULT_LIMIT_OFFSET_PCT
    min_interval_hours: int = DEFAULT_MIN_INTERVAL_HOURS

    @classmethod
    def from_config(cls, config: AppConfig) -> RebalanceManager:
        '''Build a manager from a resolved :class:`AppConfig`.'''
        return cls(
            quote_sanity_pct=config.quote_sanity_pct,
            limit_offset_pct=config.limit_offset_pct,
            min_interval_hours=config.min_interval_hours,
        )

    def decide(
        self,
        pair: PairConfig,
        snapshot: PairSnapshot,
        *,
        now: str | None = None,
    ) -> RebalanceDecision:
        '''Evaluate one pair against its target and return a decision.

        Args:
            pair: The pair configuration (target, band, notionals).
            snapshot: Point-in-time balances and prices for the pair.
            now: UTC ISO-8601 reference time; defaults to the current time.
        '''
        moment = now or now_iso()
        metrics = _metrics(pair, snapshot, moment)
        skip = (
            self._abnormal_price(snapshot, metrics)
            or _market_unavailable(snapshot, metrics)
            or self._too_soon(snapshot, metrics, moment)
            or _within_band(pair, metrics)
        )
        if skip is not None:
            return skip
        order = self._size_order(pair, snapshot, metrics)
        skip = _below_min_notional(pair, order, metrics) or _insufficient_balance(
            snapshot, order, metrics
        )
        if skip is not None:
            return skip
        return _ok(metrics, _clamp(order, pair, snapshot))

    def _abnormal_price(self, snapshot: PairSnapshot, m: _Metrics) -> RebalanceDecision | None:
        price, bid, ask = snapshot.price, snapshot.bid, snapshot.ask
        if min(price, bid, ask) <= 0:
            return _skip(m, SkipReason.ABNORMAL_PRICE, 'non-positive price/bid/ask')
        if bid > ask:
            return _skip(m, SkipReason.ABNORMAL_PRICE, f'crossed book: bid {bid} > ask {ask}')
        mid = (bid + ask) / 2
        deviation = abs(price - mid) / mid * _PCT
        if deviation > self.quote_sanity_pct:
            return _skip(
                m,
                SkipReason.ABNORMAL_PRICE,
                f'price deviates {deviation:.2f}% > {self.quote_sanity_pct}% from mid',
            )
        return None

    def _too_soon(
        self, snapshot: PairSnapshot, m: _Metrics, now: str
    ) -> RebalanceDecision | None:
        if self.min_interval_hours <= 0 or not snapshot.last_rebalance_at:
            return None
        elapsed = hours_between(snapshot.last_rebalance_at, now)
        if elapsed >= self.min_interval_hours:
            return None
        return _skip(
            m,
            SkipReason.TOO_SOON,
            f'{elapsed:.1f}h since last rebalance < {self.min_interval_hours}h',
        )

    def _size_order(
        self, pair: PairConfig, snapshot: PairSnapshot, m: _Metrics
    ) -> ProposedOrder:
        side = OrderSide.SELL if m.drift_pct > 0 else OrderSide.BUY
        limit_price = self._limit_price(side, snapshot)
        amount = round_amount(m.delta_value / snapshot.price, snapshot.amount_precision)
        return ProposedOrder(
            symbol=pair.symbol,
            side=side,
            amount=amount,
            limit_price=limit_price,
            notional=quote_notional(amount, limit_price),
        )

    def _limit_price(self, side: OrderSide, snapshot: PairSnapshot) -> float:
        offset = self.limit_offset_pct / _PCT
        if side is OrderSide.BUY:
            return snapshot.bid * (1 - offset)
        return snapshot.ask * (1 + offset)


def _metrics(pair: PairConfig, snapshot: PairSnapshot, now: str) -> _Metrics:
    base_value = snapshot.base_total * snapshot.price
    total_value = base_value + snapshot.stable_total
    current = base_value / total_value * _PCT if total_value > 0 else 0.0
    drift = current - pair.target_volatile_pct
    delta = abs(total_value * drift / _PCT)
    return _Metrics(
        symbol=pair.symbol,
        target_volatile_pct=pair.target_volatile_pct,
        current_volatile_pct=current,
        drift_pct=drift,
        total_value=total_value,
        delta_value=delta,
        last_rebalance_at=snapshot.last_rebalance_at,
        days_since_last=_days_since(snapshot.last_rebalance_at, now),
    )


def _days_since(last: str | None, now: str) -> float | None:
    if not last:
        return None
    return hours_between(last, now) / _HOURS_PER_DAY


def _market_unavailable(snapshot: PairSnapshot, m: _Metrics) -> RebalanceDecision | None:
    if snapshot.market_active:
        return None
    return _skip(m, SkipReason.MARKET_UNAVAILABLE, 'market is not active for trading')


def _within_band(pair: PairConfig, m: _Metrics) -> RebalanceDecision | None:
    if abs(m.drift_pct) > pair.band_pct:
        return None
    return _skip(
        m,
        SkipReason.WITHIN_BAND,
        f'drift {m.drift_pct:.2f}pp within band {pair.band_pct}pp',
    )


def _below_min_notional(
    pair: PairConfig, order: ProposedOrder, m: _Metrics
) -> RebalanceDecision | None:
    if order.amount <= 0:
        return _skip(m, SkipReason.BELOW_MIN_NOTIONAL, 'amount rounds to zero at market precision')
    if m.delta_value < pair.min_notional:
        return _skip(
            m,
            SkipReason.BELOW_MIN_NOTIONAL,
            f'trade {m.delta_value:.2f} < min notional {pair.min_notional}',
        )
    return None


def _insufficient_balance(
    snapshot: PairSnapshot, order: ProposedOrder, m: _Metrics
) -> RebalanceDecision | None:
    if order.side is OrderSide.SELL:
        if snapshot.base_free >= order.amount:
            return None
        detail = f'need {order.amount} base, have {snapshot.base_free} free'
    else:
        if snapshot.stable_free >= order.notional:
            return None
        detail = f'need {order.notional:.2f} quote, have {snapshot.stable_free} free'
    return _skip(m, SkipReason.INSUFFICIENT_BALANCE, detail)


def _clamp(order: ProposedOrder, pair: PairConfig, snapshot: PairSnapshot) -> ProposedOrder:
    cap = pair.max_trade_notional
    if cap <= 0 or order.notional <= cap:
        return order
    amount = round_amount(cap / order.limit_price, snapshot.amount_precision)
    return ProposedOrder(
        symbol=order.symbol,
        side=order.side,
        amount=amount,
        limit_price=order.limit_price,
        notional=quote_notional(amount, order.limit_price),
        clamped=True,
    )


def _skip(m: _Metrics, reason: SkipReason, detail: str) -> RebalanceDecision:
    return RebalanceDecision(
        symbol=m.symbol,
        rebalance=False,
        reason=reason,
        drift_pct=m.drift_pct,
        target_volatile_pct=m.target_volatile_pct,
        current_volatile_pct=m.current_volatile_pct,
        total_value=m.total_value,
        last_rebalance_at=m.last_rebalance_at,
        days_since_last=m.days_since_last,
        proposed_order=None,
        detail=detail,
    )


def _ok(m: _Metrics, order: ProposedOrder) -> RebalanceDecision:
    detail = f'{order.side.value} {order.amount} @ {order.limit_price} ({order.notional:.2f} quote)'
    return RebalanceDecision(
        symbol=m.symbol,
        rebalance=True,
        reason=SkipReason.OK,
        drift_pct=m.drift_pct,
        target_volatile_pct=m.target_volatile_pct,
        current_volatile_pct=m.current_volatile_pct,
        total_value=m.total_value,
        last_rebalance_at=m.last_rebalance_at,
        days_since_last=m.days_since_last,
        proposed_order=order,
        detail=detail,
    )
