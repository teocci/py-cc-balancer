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


# --- Multi-timeframe fill alignment (I-15): a finer series resolves fills ---
# within each decision interval, at the finer bar's timestamp, no look-ahead.

_HOUR_MS = 3_600_000


def _hour(day: int, hour: int, low: float, high: float) -> list[float]:
    ts = _START + day * _DAY_MS + hour * _HOUR_MS
    return [ts, 100.0, high, low, 100.0, 10.0]


def test_aligned_fill_resolves_on_finer_bar_within_next_interval():
    from ccbalancer.utils.timeutil import ms_to_iso
    # day0 decides BUY @100; the fill is resolved over day1's hourly bars.
    daily = [_candle(0, 100, 100, 100, 100), _candle(1, 100, 105, 95, 100)]
    # day1 hours: first three stay above 100, the fourth dips to 99 -> first cross.
    fill_candles = [
        _hour(1, 0, low=101, high=106), _hour(1, 1, low=101, high=104),
        _hour(1, 2, low=102, high=103), _hour(1, 3, low=99, high=101),
        _hour(1, 4, low=98, high=102),
    ]
    outcome = replay(daily, _pair(), _rebalancer(), _params(), fill_candles=fill_candles)

    assert len(outcome.fills) == 1
    fill = outcome.fills[0]
    assert fill.price == 100.0
    assert fill.qty == 80.0
    # Filled at the crossing hour (day1 hour3), not the daily bar's open.
    assert fill.ts == ms_to_iso(_START + _DAY_MS + 3 * _HOUR_MS)


def test_aligned_no_look_ahead_finer_bars_of_own_interval_never_fill():
    # day0 decides BUY @100. Its OWN interval's hours dip below 100 (would fill if
    # look-ahead leaked); day1's hours stay above -> the order must NOT fill.
    daily = [_candle(0, 100, 100, 100, 100), _candle(1, 101, 105, 101, 103)]
    fill_candles = [
        _hour(0, 5, low=90, high=100),   # day0 interval — must be ignored
        _hour(0, 6, low=90, high=100),
        _hour(1, 0, low=101, high=105),  # day1 interval — never crosses 100
        _hour(1, 1, low=102, high=106),
    ]
    outcome = replay(daily, _pair(), _rebalancer(), _params(), fill_candles=fill_candles)
    assert outcome.fills == []


def test_aligned_empty_window_rests_without_filling():
    # No finer bars cover day1's interval -> the order rests (re-quoted next bar).
    daily = [_candle(0, 100, 100, 100, 100), _candle(1, 100, 105, 95, 100)]
    fill_candles = [_hour(0, 1, low=90, high=100)]  # only day0-interval bars
    outcome = replay(daily, _pair(), _rebalancer(), _params(), fill_candles=fill_candles)
    assert outcome.fills == []


def test_aligned_replay_is_deterministic():
    daily = [_candle(0, 100, 100, 100, 100), _candle(1, 100, 105, 95, 100)]
    fill_candles = [_hour(1, h, low=99 if h == 2 else 101, high=105) for h in range(5)]
    a = replay(daily, _pair(), _rebalancer(), _params(fee_rate=0.001), fill_candles=fill_candles)
    b = replay(daily, _pair(), _rebalancer(), _params(fee_rate=0.001), fill_candles=fill_candles)
    assert a.fills == b.fills
    assert (a.final_base, a.final_stable) == (b.final_base, b.final_stable)
