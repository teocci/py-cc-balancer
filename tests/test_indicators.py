'''Phase 8 tests: pure indicator math against fixed fixtures.

Values are checked against known references where one exists (the StockCharts
14-period RSI worked example yields 70.53) and against hand-computed values for
small fixtures, so a regression in the math is caught immediately.
'''

from __future__ import annotations

import pytest

from ccbalancer.utils import indicators as ind

# StockCharts' canonical RSI worked example: the 15th close yields RSI 70.53.
_RSI_REFERENCE_CLOSES = [
    44.3389, 44.0902, 44.1497, 43.6124, 44.3278, 44.8264, 45.0955, 45.4245,
    45.8433, 46.0826, 45.8931, 46.0328, 45.6140, 46.2820, 46.2820,
]


def test_sma_trailing_window():
    assert ind.sma([2, 4, 6, 8], 2) == [None, 3.0, 5.0, 7.0]


def test_sma_insufficient_history_is_none():
    assert ind.sma([1.0, 2.0], 5) == [None, None]


def test_ema_small_series_matches_hand_computed():
    assert ind.ema([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_ema_of_constant_series_is_constant():
    assert ind.ema([5.0, 5.0, 5.0, 5.0], 2) == [None, 5.0, 5.0, 5.0]


def test_ema_period_one_returns_input():
    assert ind.ema([3.0, 7.0, 2.0], 1) == [3.0, 7.0, 2.0]


def test_ema_insufficient_history_is_all_none():
    assert ind.ema([1.0, 2.0], 5) == [None, None]


def test_ema_rejects_non_positive_period():
    with pytest.raises(ValueError):
        ind.ema([1.0, 2.0, 3.0], 0)


def test_rsi_matches_stockcharts_reference():
    series = ind.rsi(_RSI_REFERENCE_CLOSES, 14)
    assert series[:14] == [None] * 14
    assert series[14] == pytest.approx(70.53, abs=0.01)


def test_rsi_all_gains_is_100():
    assert ind.rsi(list(range(1, 17)), 14)[-1] == 100.0


def test_rsi_all_losses_is_0():
    assert ind.rsi(list(range(20, 0, -1)), 14)[-1] == 0.0


def test_macd_alignment_and_values():
    values = [
        10, 12, 11, 13, 15, 14, 16, 18, 17, 19, 20, 22, 21, 23, 25, 14, 16, 18,
        17, 19, 20, 22, 21, 23, 25, 24, 26, 28, 27, 29, 30, 32, 31, 33, 35,
    ]
    macd_line, signal_line, histogram = ind.macd(values)
    assert len(macd_line) == len(signal_line) == len(histogram) == len(values)
    assert macd_line[-1] == pytest.approx(4.517048, abs=1e-5)
    assert signal_line[-1] == pytest.approx(3.737258, abs=1e-5)
    assert histogram[-1] == pytest.approx(0.77979, abs=1e-5)


def test_bollinger_bands_from_window():
    window = [2, 4, 4, 4, 5, 5, 7, 9]
    upper, middle, lower = ind.bollinger(window, period=8, num_std=2.0)
    assert middle[-1] == pytest.approx(5.0)
    assert upper[-1] == pytest.approx(9.0)
    assert lower[-1] == pytest.approx(1.0)
    assert middle[:7] == [None] * 7


def test_atr_constant_true_range():
    highs = [10, 11, 12, 13, 14, 15]
    lows = [8, 9, 10, 11, 12, 13]
    closes = [9, 10, 11, 12, 13, 14]
    assert ind.atr(highs, lows, closes, period=3) == [None, None, None, 2.0, 2.0, 2.0]


def test_atr_insufficient_history_is_all_none():
    assert ind.atr([1, 2], [0, 1], [1, 2], period=3) == [None, None]


def test_fib_levels_map_high_low():
    levels = ind.fib_levels(100.0, 0.0)
    assert levels['0'] == 100.0
    assert levels['1'] == 0.0
    assert levels['0.5'] == 50.0
    assert levels['0.618'] == pytest.approx(38.2)


def test_last_value_skips_trailing_none():
    assert ind.last_value([None, 1.0, 2.0]) == 2.0
    assert ind.last_value([None, None]) is None
    assert ind.last_value([]) is None
