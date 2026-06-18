'''Phase 6 tests: the pure rebalance decision matrix (no I/O, no mocks).'''

from __future__ import annotations

import pytest

from ccbalancer.config import AppConfig, Defaults
from ccbalancer.enums.side import OrderSide
from ccbalancer.enums.skip_reason import SkipReason
from ccbalancer.managers.rebalance_manager import RebalanceManager
from ccbalancer.models import PairConfig, PairSnapshot


def _pair(
    symbol: str = 'BTC/USDT',
    *,
    target_volatile: float = 80.0,
    band: float = 5.0,
    min_notional: float = 10.0,
    max_trade: float = 0.0,
) -> PairConfig:
    return PairConfig(
        symbol=symbol,
        target_volatile_pct=target_volatile,
        target_stable_pct=100.0 - target_volatile,
        band_pct=band,
        min_notional=min_notional,
        max_trade_notional=max_trade,
    )


def _snap(
    *,
    base_total: float = 1.0,
    base_free: float | None = None,
    stable_total: float = 0.0,
    stable_free: float | None = None,
    price: float = 100.0,
    bid: float | None = None,
    ask: float | None = None,
    amount_precision: int | None = 4,
    market_active: bool = True,
    last_rebalance_at: str | None = None,
) -> PairSnapshot:
    return PairSnapshot(
        symbol='BTC/USDT',
        base_total=base_total,
        base_free=base_total if base_free is None else base_free,
        stable_total=stable_total,
        stable_free=stable_total if stable_free is None else stable_free,
        price=price,
        bid=bid if bid is not None else price,
        ask=ask if ask is not None else price,
        amount_precision=amount_precision,
        market_active=market_active,
        last_rebalance_at=last_rebalance_at,
    )


# --- within band / metrics ------------------------------------------------


def test_within_band_skips_without_order():
    # base_value 85 of total 100 -> drift exactly +5pp, equal to the band.
    snap = _snap(base_total=0.85, price=100.0, stable_total=15.0)
    decision = RebalanceManager().decide(_pair(), snap)
    assert decision.reason is SkipReason.WITHIN_BAND
    assert decision.rebalance is False
    assert decision.proposed_order is None
    assert decision.drift_pct == pytest.approx(5.0)
    assert decision.current_volatile_pct == pytest.approx(85.0)
    assert decision.total_value == pytest.approx(100.0)


def test_zero_total_value_falls_through_to_min_notional():
    decision = RebalanceManager().decide(_pair(), _snap(base_total=0.0, stable_total=0.0))
    assert decision.reason is SkipReason.BELOW_MIN_NOTIONAL
    assert decision.current_volatile_pct == 0.0


# --- SELL sizing ----------------------------------------------------------


def test_sell_when_over_target():
    # 100% volatile vs 80% target -> drift +20pp, move 20 quote -> sell 0.2 base.
    snap = _snap(base_total=1.0, price=100.0, stable_total=0.0, bid=99.0, ask=101.0)
    decision = RebalanceManager().decide(_pair(), snap)
    order = decision.proposed_order
    assert decision.reason is SkipReason.OK
    assert decision.rebalance is True
    assert order.side is OrderSide.SELL
    assert order.amount == pytest.approx(0.2)
    assert order.limit_price == pytest.approx(101.0)  # ask, offset 0
    assert order.notional == pytest.approx(20.2)
    assert order.clamped is False


# --- BUY sizing -----------------------------------------------------------


def test_buy_when_under_target():
    # 0% volatile vs 80% target -> drift -80pp, move 80 quote -> buy 0.8 base.
    snap = _snap(base_total=0.0, stable_total=100.0, price=100.0, bid=100.0, ask=100.0)
    decision = RebalanceManager().decide(_pair(), snap)
    order = decision.proposed_order
    assert decision.reason is SkipReason.OK
    assert order.side is OrderSide.BUY
    assert order.amount == pytest.approx(0.8)
    assert order.limit_price == pytest.approx(100.0)
    assert decision.drift_pct == pytest.approx(-80.0)


def test_limit_offset_prices_passively():
    manager = RebalanceManager(limit_offset_pct=1.0)
    sell = manager.decide(_pair(), _snap(base_total=1.0, bid=99.0, ask=100.0))
    assert sell.proposed_order.limit_price == pytest.approx(101.0)  # ask * 1.01
    buy = manager.decide(_pair(), _snap(base_total=0.0, stable_total=100.0, bid=100.0, ask=101.0))
    assert buy.proposed_order.limit_price == pytest.approx(99.0)  # bid * 0.99


# --- min notional ---------------------------------------------------------


def test_below_min_notional_skips():
    # drift +20pp on a tiny book: move only 2 quote, below the 10 floor.
    snap = _snap(base_total=0.1, price=100.0, stable_total=0.0)
    decision = RebalanceManager().decide(_pair(min_notional=10.0), snap)
    assert decision.reason is SkipReason.BELOW_MIN_NOTIONAL
    assert decision.proposed_order is None


# --- precision rounding ---------------------------------------------------


def test_amount_rounds_down_to_precision():
    snap = _snap(base_total=1.0, price=100.0, stable_total=0.0, amount_precision=1)
    order = RebalanceManager().decide(_pair(), snap).proposed_order
    assert order.amount == pytest.approx(0.2)  # 0.20 floored at 1 dp


def test_amount_rounding_to_zero_is_below_min_notional():
    # delta 20 quote clears the floor, but 0.2 base floors to 0 at precision 0.
    snap = _snap(base_total=1.0, price=100.0, stable_total=0.0, amount_precision=0)
    decision = RebalanceManager().decide(_pair(), snap)
    assert decision.reason is SkipReason.BELOW_MIN_NOTIONAL
    assert 'rounds to zero' in decision.detail


# --- insufficient balance -------------------------------------------------


def test_insufficient_base_for_sell():
    # wants to sell 0.2 base but only 0.05 is free.
    snap = _snap(base_total=1.0, base_free=0.05, price=100.0, stable_total=0.0)
    decision = RebalanceManager().decide(_pair(), snap)
    assert decision.reason is SkipReason.INSUFFICIENT_BALANCE
    assert decision.proposed_order is None


def test_insufficient_quote_for_buy():
    # wants ~80 quote to buy but only 10 is free.
    snap = _snap(base_total=0.0, stable_total=100.0, stable_free=10.0, price=100.0)
    decision = RebalanceManager().decide(_pair(), snap)
    assert decision.reason is SkipReason.INSUFFICIENT_BALANCE


# --- abnormal price -------------------------------------------------------


def test_abnormal_price_non_positive():
    snap = _snap(base_total=1.0, price=0.0, bid=0.0, ask=0.0)
    assert RebalanceManager().decide(_pair(), snap).reason is SkipReason.ABNORMAL_PRICE


def test_abnormal_price_crossed_book():
    snap = _snap(base_total=1.0, price=100.0, bid=101.0, ask=100.0)
    assert RebalanceManager().decide(_pair(), snap).reason is SkipReason.ABNORMAL_PRICE


def test_abnormal_price_deviates_beyond_sanity():
    # last 130 vs mid 100 -> 30% deviation > 15% sanity threshold.
    snap = _snap(base_total=1.0, price=130.0, bid=100.0, ask=100.0)
    manager = RebalanceManager(quote_sanity_pct=15.0)
    assert manager.decide(_pair(), snap).reason is SkipReason.ABNORMAL_PRICE


def test_deviation_within_sanity_is_allowed():
    # 5% deviation under a 15% threshold -> proceeds past the abnormal guard.
    snap = _snap(base_total=1.0, price=105.0, bid=100.0, ask=100.0, stable_total=0.0)
    decision = RebalanceManager(quote_sanity_pct=15.0).decide(_pair(), snap)
    assert decision.reason is SkipReason.OK


# --- market availability --------------------------------------------------


def test_market_unavailable_skips():
    snap = _snap(base_total=1.0, price=100.0, market_active=False)
    assert RebalanceManager().decide(_pair(), snap).reason is SkipReason.MARKET_UNAVAILABLE


# --- too soon (cadence guard) ---------------------------------------------


def test_too_soon_when_interval_not_elapsed():
    snap = _snap(base_total=1.0, price=100.0, last_rebalance_at='2026-06-18T00:00:00Z')
    manager = RebalanceManager(min_interval_hours=24)
    decision = manager.decide(_pair(), snap, now='2026-06-18T06:00:00Z')
    assert decision.reason is SkipReason.TOO_SOON
    assert decision.days_since_last == pytest.approx(0.25)


def test_not_too_soon_when_interval_elapsed():
    snap = _snap(base_total=1.0, price=100.0, last_rebalance_at='2026-06-17T00:00:00Z')
    manager = RebalanceManager(min_interval_hours=24)
    decision = manager.decide(_pair(), snap, now='2026-06-18T06:00:00Z')
    assert decision.reason is SkipReason.OK


def test_interval_disabled_ignores_recent_rebalance():
    snap = _snap(base_total=1.0, price=100.0, last_rebalance_at='2026-06-18T05:59:00Z')
    decision = RebalanceManager(min_interval_hours=0).decide(
        _pair(), snap, now='2026-06-18T06:00:00Z'
    )
    assert decision.reason is SkipReason.OK


# --- max-trade clamp ------------------------------------------------------


def test_clamp_reduces_to_max_trade_notional():
    # ideal sell 0.2 @ 100 = 20 quote, capped at 10.
    snap = _snap(base_total=1.0, price=100.0, stable_total=0.0, bid=100.0, ask=100.0)
    decision = RebalanceManager().decide(_pair(max_trade=10.0), snap)
    order = decision.proposed_order
    assert decision.reason is SkipReason.OK
    assert order.clamped is True
    assert order.amount == pytest.approx(0.1)
    assert order.notional == pytest.approx(10.0)


def test_no_clamp_when_under_cap():
    snap = _snap(base_total=1.0, price=100.0, stable_total=0.0)
    order = RebalanceManager().decide(_pair(max_trade=1000.0), snap).proposed_order
    assert order.clamped is False


# --- from_config wiring ---------------------------------------------------


def test_from_config_copies_relevant_settings():
    config = AppConfig(
        exchange='bybit',
        testnet=True,
        quote_sanity_pct=12.0,
        limit_offset_pct=0.5,
        min_interval_hours=8,
        http_timeout_ms=10000,
        defaults=Defaults(80.0, 20.0, 5.0, 10.0, 0.0),
        api_key=None,
        api_secret=None,
        app_dir=None,
        config_path=None,
    )
    manager = RebalanceManager.from_config(config)
    assert manager.quote_sanity_pct == 12.0
    assert manager.limit_offset_pct == 0.5
    assert manager.min_interval_hours == 8
