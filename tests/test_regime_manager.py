'''Phase 12 tests: the pure regime signal (price-variance since target-set).'''

from __future__ import annotations

import pytest

from ccbalancer.managers.regime_manager import RegimeManager
from ccbalancer.models import PairConfig, PairSnapshot


def _pair(target_volatile=80.0, target_set_price=None) -> PairConfig:
    return PairConfig(
        symbol='BTC/USDT',
        target_volatile_pct=target_volatile,
        target_stable_pct=100.0 - target_volatile,
        band_pct=5.0,
        min_notional=10.0,
        target_set_price=target_set_price,
        target_set_ts='2026-06-01T00:00:00Z' if target_set_price else None,
    )


def _snapshot(price, base_total=1.0, stable_total=5000.0) -> PairSnapshot:
    return PairSnapshot(
        symbol='BTC/USDT',
        base_total=base_total,
        base_free=base_total,
        stable_total=stable_total,
        stable_free=stable_total,
        price=price,
        bid=price,
        ask=price,
        amount_precision=None,
        market_active=True,
        last_rebalance_at=None,
    )


def test_no_baseline_yields_no_signal():
    signal = RegimeManager().signal(_pair(target_set_price=None), _snapshot(60000.0))
    assert signal.price_change_pct is None
    assert signal.direction == 'none'
    assert signal.flag is False
    assert signal.suggested_volatile_pct is None
    assert signal.suggested_stable_pct is None
    # Scenarios still computed; the current target is always a rung, none suggested.
    assert any(s.is_current for s in signal.scenarios)
    assert not any(s.is_suggested for s in signal.scenarios)


def test_run_up_beyond_band_flags_and_de_risks():
    signal = RegimeManager().signal(_pair(80.0, target_set_price=50000.0), _snapshot(65000.0))
    assert signal.price_change_pct == pytest.approx(30.0)
    assert signal.direction == 'up'
    assert signal.flag is True
    # 80 is the top rung; de-risk steps one rung down to 50.
    assert signal.suggested_volatile_pct == 50.0
    assert signal.suggested_stable_pct == 50.0
    suggested = [s for s in signal.scenarios if s.is_suggested]
    assert [s.volatile_pct for s in suggested] == [50.0]


def test_drop_beyond_band_steps_toward_more_risk():
    signal = RegimeManager().signal(_pair(50.0, target_set_price=50000.0), _snapshot(35000.0))
    assert signal.price_change_pct == pytest.approx(-30.0)
    assert signal.direction == 'down'
    assert signal.flag is True
    # current 50 → ladder (80, 50, 25); a drop steps up to 80.
    assert signal.suggested_volatile_pct == 80.0


def test_within_band_holds_current_ratio():
    signal = RegimeManager().signal(_pair(80.0, target_set_price=50000.0), _snapshot(55000.0))
    assert signal.price_change_pct == pytest.approx(10.0)
    assert signal.direction == 'flat'
    assert signal.flag is False
    assert signal.suggested_volatile_pct == 80.0  # unchanged


def test_band_boundary_is_exclusive():
    manager = RegimeManager(review_band_pct=20.0)
    at_band = manager.signal(_pair(80.0, target_set_price=50000.0), _snapshot(60000.0))
    just_over = manager.signal(_pair(80.0, target_set_price=50000.0), _snapshot(60001.0))
    assert at_band.price_change_pct == pytest.approx(20.0)
    assert at_band.flag is False  # exactly at the band does not fire
    assert just_over.flag is True


def test_current_target_always_a_scenario_rung():
    signal = RegimeManager().signal(_pair(70.0, target_set_price=50000.0), _snapshot(50000.0))
    rungs = [s.volatile_pct for s in signal.scenarios]
    assert rungs == [80.0, 70.0, 50.0, 25.0]  # descending, 70 injected
    current = [s for s in signal.scenarios if s.is_current]
    assert [s.volatile_pct for s in current] == [70.0]


def test_scenario_value_split_and_determinism():
    pair, snap = _pair(80.0, target_set_price=50000.0), _snapshot(60000.0)
    signal = RegimeManager().signal(pair, snap)
    total = 1.0 * 60000.0 + 5000.0  # 65000
    assert signal.total_value == pytest.approx(total)
    fifty = next(s for s in signal.scenarios if s.volatile_pct == 50.0)
    assert fifty.volatile_value == pytest.approx(total * 0.5)
    assert fifty.stable_value == pytest.approx(total * 0.5)
    # Deterministic: identical inputs reproduce the same signal.
    assert RegimeManager().signal(pair, snap) == signal
