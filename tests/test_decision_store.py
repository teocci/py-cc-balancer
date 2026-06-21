'''Phase 9 tests: the append-only decision log and its serialization.'''

from __future__ import annotations

import json

import pytest

from ccbalancer.constants import SCHEMA_VERSION
from ccbalancer.enums.skip_reason import SkipReason
from ccbalancer.exceptions import StateError
from ccbalancer.managers.rebalance_manager import GUARD_ORDER, RebalanceManager
from ccbalancer.models import PairConfig, PairSnapshot
from ccbalancer.stores.decision_store import (
    DecisionStore,
    decision_to_record,
    guard_ladder,
)

_PAIR = PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0)
_NOW = '2026-06-19T12:00:00Z'


def _snapshot(**overrides: object) -> PairSnapshot:
    base = {
        'symbol': 'BTC/USDT',
        'base_total': 1.0,
        'base_free': 1.0,
        'stable_total': 5000.0,
        'stable_free': 5000.0,
        'price': 50000.0,
        'bid': 49990.0,
        'ask': 50010.0,
        'amount_precision': 3,
        'market_active': True,
        'last_rebalance_at': None,
    }
    base.update(overrides)
    return PairSnapshot(**base)


def _decide(snapshot: PairSnapshot):
    return RebalanceManager().decide(_PAIR, snapshot, now=_NOW)


def test_guard_ladder_ok_passes_every_guard():
    # 1 BTC (~90.9%) vs 80% target with a 5pp band -> SELL, reason OK.
    decision = _decide(_snapshot())
    assert decision.reason is SkipReason.OK
    ladder = guard_ladder(decision)
    assert [g['name'] for g in ladder] == [g.value for g in GUARD_ORDER]
    assert all(g['status'] == 'pass' for g in ladder)


def test_guard_ladder_marks_first_failure_then_skips_rest():
    # Balanced 0.8 BTC vs 80% -> WITHIN_BAND (the 4th guard).
    decision = _decide(_snapshot(base_total=0.8, base_free=0.8, stable_total=10000.0))
    assert decision.reason is SkipReason.WITHIN_BAND
    statuses = {g['name']: g['status'] for g in guard_ladder(decision)}
    assert statuses['abnormal_price'] == 'pass'
    assert statuses['market_unavailable'] == 'pass'
    assert statuses['too_soon'] == 'pass'
    assert statuses['within_band'] == 'fail'
    assert statuses['below_min_notional'] == 'skipped'
    assert statuses['insufficient_balance'] == 'skipped'


def test_guard_ladder_fails_at_abnormal_price():
    decision = _decide(_snapshot(price=60000.0))
    assert decision.reason is SkipReason.ABNORMAL_PRICE
    ladder = guard_ladder(decision)
    assert ladder[0] == {'name': 'abnormal_price', 'status': 'fail'}
    assert all(g['status'] == 'skipped' for g in ladder[1:])


def test_decision_to_record_carries_inputs_guards_and_order():
    decision = _decide(_snapshot())
    record = decision_to_record(
        decision, ts=_NOW, exchange='bybit', testnet=True, command='plan'
    )
    assert record['schema_version'] == SCHEMA_VERSION
    assert record['ts'] == _NOW
    assert record['command'] == 'plan'
    assert record['exchange'] == 'bybit'
    assert record['testnet'] is True
    assert record['symbol'] == 'BTC/USDT'
    assert record['reason'] == 'ok'
    assert record['rebalance'] is True
    assert record['target_volatile_pct'] == 80.0
    assert isinstance(record['guards'], list) and len(record['guards']) == len(GUARD_ORDER)
    assert record['proposed_order']['side'] == 'sell'


def test_decision_to_record_omits_order_when_holding():
    decision = _decide(_snapshot(base_total=0.8, base_free=0.8, stable_total=10000.0))
    record = decision_to_record(
        decision, ts=_NOW, exchange='bybit', testnet=False, command='plan'
    )
    assert record['rebalance'] is False
    assert record['proposed_order'] is None


def test_append_and_load_round_trip(tmp_path):
    store = DecisionStore(tmp_path / 'decision_log.jsonl')
    written = store.append_decision(
        _decide(_snapshot()), ts=_NOW, exchange='bybit', testnet=True, command='plan'
    )
    loaded = store.load()
    assert loaded == [written]


def test_append_is_append_only(tmp_path):
    store = DecisionStore(tmp_path / 'decision_log.jsonl')
    for _ in range(3):
        store.append_decision(
            _decide(_snapshot()), ts=_NOW, exchange='bybit', testnet=True, command='plan'
        )
    lines = (tmp_path / 'decision_log.jsonl').read_text(encoding='utf-8').splitlines()
    assert len(lines) == 3
    assert all(json.loads(line)['symbol'] == 'BTC/USDT' for line in lines)


def test_load_absent_returns_empty(tmp_path):
    assert DecisionStore(tmp_path / 'missing.jsonl').load() == []


def test_load_corrupt_line_raises_state_error(tmp_path):
    path = tmp_path / 'decision_log.jsonl'
    path.write_text('{not json}\n', encoding='utf-8')
    with pytest.raises(StateError):
        DecisionStore(path).load()


def test_records_are_one_compact_json_line_each(tmp_path):
    # jq-queryable: each line parses on its own and holds no embedded newline.
    store = DecisionStore(tmp_path / 'decision_log.jsonl')
    store.append_decision(
        _decide(_snapshot()), ts=_NOW, exchange='bybit', testnet=True, command='plan'
    )
    raw = (tmp_path / 'decision_log.jsonl').read_text(encoding='utf-8')
    assert raw.endswith('\n')
    assert raw.count('\n') == 1
