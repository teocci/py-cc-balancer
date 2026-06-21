'''Phase 1 smoke tests: domain primitives import, immutability, completeness.'''

from __future__ import annotations

import dataclasses

import pytest

from ccbalancer.enums import OrderSide, OutputFormat, SkipReason
from ccbalancer.exceptions import AppError, PortfolioError
from ccbalancer.models import (
    AssetBalance,
    ExecutionResult,
    HistoryEvent,
    IndicatorSnapshot,
    PairConfig,
    PairSnapshot,
    ProposedOrder,
    RebalanceDecision,
    RebalanceState,
)


def _valid_pair() -> PairConfig:
    return PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0)


def test_pair_config_base_and_quote() -> None:
    pair = _valid_pair()
    assert pair.base == 'BTC'
    assert pair.quote == 'USDT'


@pytest.mark.parametrize('volatile,stable', [(80.0, 30.0), (50.0, 49.0)])
def test_pair_config_rejects_bad_ratio(volatile: float, stable: float) -> None:
    with pytest.raises(PortfolioError):
        PairConfig('BTC/USDT', volatile, stable, 5.0, 10.0)


@pytest.mark.parametrize('symbol', ['BTCUSDT', 'BTC/', '/USDT', ''])
def test_pair_config_rejects_bad_symbol(symbol: str) -> None:
    with pytest.raises(PortfolioError):
        PairConfig(symbol, 80.0, 20.0, 5.0, 10.0)


def test_pair_config_is_frozen() -> None:
    pair = _valid_pair()
    with pytest.raises(dataclasses.FrozenInstanceError):
        pair.symbol = 'ETH/USDT'  # type: ignore[misc]


def test_skip_reason_covers_all_decision_reasons() -> None:
    expected = {
        'OK',
        'WITHIN_BAND',
        'BELOW_MIN_NOTIONAL',
        'INSUFFICIENT_BALANCE',
        'ABNORMAL_PRICE',
        'MARKET_UNAVAILABLE',
        'TOO_SOON',
    }
    assert {reason.name for reason in SkipReason} == expected


def test_portfolio_error_is_app_error() -> None:
    assert issubclass(PortfolioError, AppError)


def test_models_construct() -> None:
    AssetBalance('BTC', 1.0, 1.0)
    PairSnapshot('BTC/USDT', 1.0, 1.0, 100.0, 100.0, 65000.0, 64990.0, 65010.0, 5, True, None)
    order = ProposedOrder('BTC/USDT', OrderSide.SELL, 0.001, 65000.0, 65.0)
    RebalanceDecision('BTC/USDT', True, SkipReason.OK, 6.0, 80.0, 86.0, 1000.0, None, None, order)
    RebalanceState('BTC/USDT', '2026-06-15T09:00:00Z', 'sell', 0.001, 65000.0, 6.0, 'ok')
    HistoryEvent('2026-06-15T09:00:00Z', 'BTC/USDT', 'sell', 0.001, 65000.0, 65.0, 6.0, 'ok', 'bybit', True, 'id', 'submitted')
    ExecutionResult('BTC/USDT', True, 'id', 'submitted', 'ok')
    assert OutputFormat.JSON.value == 'json'


def test_indicator_snapshot_constructs_and_is_frozen() -> None:
    snap = IndicatorSnapshot(
        symbol='BTC/USDT', timeframe='1h', as_of='2026-06-15T09:00:00Z',
        candle_count=200, stale=False, close=65000.0, rsi=55.0,
        macd=12.0, macd_signal=10.0, macd_histogram=2.0,
        ema={'12': 64900.0}, bollinger_upper=66000.0, bollinger_middle=65000.0,
        bollinger_lower=64000.0, atr=120.0, fib={'0.618': 63000.0},
    )
    assert snap.ema['12'] == 64900.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.close = 1.0  # type: ignore[misc]
