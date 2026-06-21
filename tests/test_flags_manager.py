'''Phase 12 tests: pure milestone evaluation (metrics and operators).'''

from __future__ import annotations

import pytest

from ccbalancer.enums.skip_reason import SkipReason
from ccbalancer.managers.flags_manager import FlagsManager
from ccbalancer.models import Milestone, PairSnapshot, RebalanceDecision


def _snapshot(price=65000.0) -> PairSnapshot:
    return PairSnapshot(
        symbol='BTC/USDT', base_total=1.0, base_free=1.0, stable_total=5000.0,
        stable_free=5000.0, price=price, bid=price, ask=price,
        amount_precision=None, market_active=True, last_rebalance_at=None,
    )


def _decision(drift=3.0, volatile=92.86, value=70000.0) -> RebalanceDecision:
    return RebalanceDecision(
        symbol='BTC/USDT', rebalance=False, reason=SkipReason.WITHIN_BAND,
        drift_pct=drift, target_volatile_pct=80.0, current_volatile_pct=volatile,
        total_value=value,
    )


def _context() -> dict[str, tuple]:
    return {'BTC/USDT': (_snapshot(), _decision())}


@pytest.mark.parametrize('metric,op,threshold,expected', [
    ('price', 'ge', 60000.0, 'hit'),
    ('price', 'gt', 65000.0, 'miss'),
    ('price', 'eq', 65000.0, 'hit'),
    ('drift_pct', 'le', 5.0, 'hit'),
    ('drift_pct', 'lt', 1.0, 'miss'),
    ('volatile_pct', 'ge', 90.0, 'hit'),
    ('value', 'gt', 100000.0, 'miss'),
    ('value', 'ge', 70000.0, 'hit'),
])
def test_metric_operator_matrix(metric, op, threshold, expected):
    milestone = Milestone(id=1, symbol='BTC/USDT', metric=metric, op=op, threshold=threshold)
    [result] = FlagsManager().evaluate([milestone], _context())
    assert result['status'] == expected
    assert result['current_value'] is not None


def test_unconfigured_symbol_is_unknown():
    milestone = Milestone(id=1, symbol='ETH/USDT', metric='price', op='ge', threshold=1.0)
    [result] = FlagsManager().evaluate([milestone], _context())
    assert result['status'] == 'unknown'
    assert result['current_value'] is None


def test_result_carries_expression_and_note():
    milestone = Milestone(id=4, symbol='BTC/USDT', metric='price', op='ge',
                          threshold=100000.0, note='watch')
    [result] = FlagsManager().evaluate([milestone], _context())
    assert result['id'] == 4
    assert result['expression'] == 'price >= 100000'
    assert result['note'] == 'watch'
