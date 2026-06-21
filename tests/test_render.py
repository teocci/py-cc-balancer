'''Phase 7 tests: stable JSON/text rendering of read-command results.'''

from __future__ import annotations

from ccbalancer.constants import SCHEMA_VERSION
from ccbalancer.enums.side import OrderSide
from ccbalancer.enums.skip_reason import SkipReason
from ccbalancer.models import PairSnapshot, ProposedOrder, RebalanceDecision
from ccbalancer.utils import render

_META = {'exchange': 'bybit', 'testnet': True, 'generated_at': '2026-06-18T12:00:00Z'}


def _snapshot(symbol: str = 'BTC/USDT') -> PairSnapshot:
    return PairSnapshot(
        symbol=symbol,
        base_total=1.0,
        base_free=1.0,
        stable_total=5000.0,
        stable_free=5000.0,
        price=50000.0,
        bid=49990.0,
        ask=50010.0,
        amount_precision=3,
        market_active=True,
        last_rebalance_at='2026-06-01T00:00:00Z',
    )


def _skip(reason: SkipReason = SkipReason.WITHIN_BAND) -> RebalanceDecision:
    return RebalanceDecision(
        symbol='BTC/USDT',
        rebalance=False,
        reason=reason,
        drift_pct=1.23,
        target_volatile_pct=80.0,
        current_volatile_pct=81.23,
        total_value=55000.0,
        last_rebalance_at='2026-06-01T00:00:00Z',
        days_since_last=17.5,
        proposed_order=None,
        detail='drift 1.23pp within band 5pp',
    )


def _ok() -> RebalanceDecision:
    order = ProposedOrder('BTC/USDT', OrderSide.SELL, 0.123, 50010.0, 6151.23)
    return RebalanceDecision(
        symbol='BTC/USDT',
        rebalance=True,
        reason=SkipReason.OK,
        drift_pct=10.9,
        target_volatile_pct=80.0,
        current_volatile_pct=90.9,
        total_value=55000.0,
        last_rebalance_at=None,
        days_since_last=None,
        proposed_order=order,
        detail='sell 0.123 @ 50010.0 (6151.23 quote)',
    )


def test_decision_to_dict_renders_reason_as_string():
    payload = render.decision_to_dict(_skip())
    assert payload['reason'] == 'within_band'
    assert payload['proposed_order'] is None
    assert payload['days_since_last'] == 17.5


def test_decision_to_dict_has_stable_key_order():
    keys = list(render.decision_to_dict(_skip()).keys())
    assert keys == [
        'symbol',
        'rebalance',
        'reason',
        'drift_pct',
        'target_volatile_pct',
        'current_volatile_pct',
        'total_value',
        'last_rebalance_at',
        'days_since_last',
        'proposed_order',
        'detail',
    ]


def test_decision_to_dict_includes_order_when_rebalancing():
    order = render.decision_to_dict(_ok())['proposed_order']
    assert order == {
        'side': 'sell',
        'amount': 0.123,
        'limit_price': 50010.0,
        'notional': 6151.23,
        'clamped': False,
    }


def test_plan_response_wraps_envelope():
    payload = render.plan_response([_skip(), _ok()], _META)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'plan'
    assert payload['exchange'] == 'bybit'
    assert payload['testnet'] is True
    assert payload['generated_at'] == '2026-06-18T12:00:00Z'
    assert len(payload['pairs']) == 2


def test_status_response_carries_holdings():
    payload = render.status_response([(_snapshot(), _skip())], _META)
    assert payload['command'] == 'status'
    row = payload['pairs'][0]
    assert row['base_total'] == 1.0
    assert row['stable_total'] == 5000.0
    assert row['price'] == 50000.0
    assert row['current_volatile_pct'] == 81.23
    assert row['last_rebalance_at'] == '2026-06-01T00:00:00Z'


def test_plan_lines_describe_action_and_reason():
    lines = render.plan_lines([_ok(), _skip()])
    assert 'REBALANCE sell' in lines[0]
    assert '[ok]' in lines[0]
    assert 'hold' in lines[1]
    assert '[within_band]' in lines[1]


def test_status_lines_show_current_vs_target_and_never():
    line = render.status_lines([(_snapshot(), _ok())])[0]
    assert 'current 90.90% / target 80.00%' in line
    assert 'last never' in line
