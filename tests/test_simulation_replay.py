'''Phase 18 tests: the pure bar-crosses-limit replay engine.

Deterministic, no I/O: candles + a pair + params in, fills + final balance out.
Covers the load-bearing invariants — no look-ahead (a fill never resolves on its
own decision bar), the crossing fill model, cancel-and-replace on a miss, fee
math, sub-min rejection, balance-mutates-only-on-fills, and determinism.
'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import OrderRejectedError
from ccbalancer.managers.rebalance_manager import RebalanceManager
from ccbalancer.managers.simulation_run_manager import ReplayParams, replay
from ccbalancer.models import PairConfig

_DAY_MS = 86_400_000
_START = 1_661_990_400_000


def _candle(i: int, o: float, h: float, low: float, c: float) -> list[float]:
    return [_START + i * _DAY_MS, o, h, low, c, 1000.0]


def _pair(min_notional: float = 10.0) -> PairConfig:
    return PairConfig('BTC/USDT', 80.0, 20.0, band_pct=5.0, min_notional=min_notional)


def _rebalancer() -> RebalanceManager:
    return RebalanceManager(quote_sanity_pct=15.0, limit_offset_pct=0.0, min_interval_hours=0)


def _params(**kw) -> ReplayParams:
    base = dict(capital=10000.0, fee_rate=0.0, amount_precision=8, min_cost=0.0)
    base.update(kw)
    return ReplayParams(**base)


def test_no_look_ahead_order_does_not_fill_on_its_decision_bar():
    # bar0 decides a BUY @100; bar1 low stays above 100 so it must NOT cross.
    # If look-ahead leaked, bar0's own low (95<=100) would wrongly fill it.
    candles = [_candle(0, 100, 100, 95, 100), _candle(1, 101, 105, 101, 103)]
    outcome = replay(candles, _pair(), _rebalancer(), _params())
    assert outcome.fills == []
    assert outcome.orders_placed == 2  # both bars decide a BUY (still all-stable)


def test_crossing_next_bar_fills_at_limit():
    candles = [_candle(0, 100, 100, 99, 100), _candle(1, 100, 101, 98, 100)]
    outcome = replay(candles, _pair(), _rebalancer(), _params())
    assert len(outcome.fills) == 1
    fill = outcome.fills[0]
    assert fill.side == 'buy'
    assert fill.price == 100.0
    assert fill.qty == 80.0  # 8000 quote / 100
    assert fill.ts == '2022-09-02T00:00:00Z'  # bar1 open, not bar0


def test_non_crossing_rests_and_requotes_no_fill():
    # A gapping-up series: each bar's BUY limit is its close, and every *next* bar's
    # low opens above it, so no resting BUY ever crosses. The order re-quotes each bar.
    candles = [
        _candle(0, 100, 100, 100, 100),
        _candle(1, 101, 110, 101, 110),
        _candle(2, 111, 120, 111, 120),
        _candle(3, 121, 130, 121, 130),
    ]
    outcome = replay(candles, _pair(), _rebalancer(), _params())
    assert outcome.fills == []
    assert outcome.orders_placed == 4  # re-quoted every bar


def test_balance_mutates_only_on_fills():
    params = _params(fee_rate=0.0)
    # First bar's BUY fills on bar1; assert base/stable moved by exactly the fill.
    candles = [_candle(0, 100, 100, 99, 100), _candle(1, 100, 101, 98, 100), _candle(2, 100, 100, 99, 100)]
    outcome = replay(candles, _pair(), _rebalancer(), params)
    # One BUY of 80 @100 = 8000 quote, zero fee.
    assert outcome.final_base == pytest.approx(80.0)
    assert outcome.final_stable == pytest.approx(2000.0)


def test_fee_is_charged_on_notional():
    candles = [_candle(0, 100, 100, 99, 100), _candle(1, 100, 101, 98, 100)]
    outcome = replay(candles, _pair(), _rebalancer(), _params(fee_rate=0.001))
    fill = outcome.fills[0]
    assert fill.fee == pytest.approx(8.0)  # 8000 * 0.001
    assert fill.fee_currency == 'USDT'
    # Stable reduced by notional + fee.
    assert outcome.final_stable == pytest.approx(10000.0 - 8000.0 - 8.0)


def test_sub_min_cost_order_is_rejected_not_filled():
    # min_cost above the order notional -> the sim exchange rejects; nothing fills,
    # balance is untouched (the 'never converges' failure stays visible).
    candles = [_candle(0, 100, 100, 99, 100), _candle(1, 100, 101, 98, 100)]
    outcome = replay(candles, _pair(min_notional=0.0), _rebalancer(), _params(min_cost=1e12))
    assert outcome.fills == []
    assert outcome.rejects >= 1
    assert outcome.final_base == 0.0
    assert outcome.final_stable == 10000.0


def test_validate_order_raises_order_rejected_below_min_cost():
    from ccbalancer.managers.simulation_run_manager import validate_order
    from ccbalancer.enums.side import OrderSide
    from ccbalancer.models import ProposedOrder

    order = ProposedOrder('BTC/USDT', OrderSide.BUY, 0.0001, 100.0, notional=0.01)
    with pytest.raises(OrderRejectedError):
        validate_order(order, min_cost=10.0)


def test_replay_is_deterministic():
    candles = [_candle(0, 100, 100, 99, 100), _candle(1, 100, 101, 98, 100),
               _candle(2, 90, 95, 88, 92), _candle(3, 92, 120, 91, 118)]
    a = replay(candles, _pair(), _rebalancer(), _params(fee_rate=0.001))
    b = replay(candles, _pair(), _rebalancer(), _params(fee_rate=0.001))
    assert a.fills == b.fills  # frozen dataclass equality
    assert (a.final_base, a.final_stable) == (b.final_base, b.final_stable)
