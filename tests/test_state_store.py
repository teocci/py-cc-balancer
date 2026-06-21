'''Phase 5 tests: rebalance state and history persistence.'''

from __future__ import annotations

import json

import pytest

from ccbalancer.exceptions import StateError
from ccbalancer.models import HistoryEvent, RebalanceState
from ccbalancer.stores.state_store import StateStore


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path / 'state.json', tmp_path / 'history.jsonl')


def _state(symbol: str = 'BTC/USDT', at: str = '2026-06-18T12:00:00Z') -> RebalanceState:
    return RebalanceState(
        symbol=symbol,
        last_rebalance_at=at,
        last_side='sell',
        last_amount=0.5,
        last_price=50000.0,
        last_drift_pct=3.2,
        last_reason='OK',
    )


def _event(symbol: str = 'BTC/USDT') -> HistoryEvent:
    return HistoryEvent(
        ts='2026-06-18T12:00:00Z',
        symbol=symbol,
        side='sell',
        amount=0.5,
        price=50000.0,
        notional=25000.0,
        drift_pct=3.2,
        reason='OK',
        exchange='bybit',
        testnet=True,
        order_id='order-1',
        status='submitted',
    )


def test_load_empty_when_absent(store):
    assert store.load() == {}


def test_save_and_get_roundtrip(store):
    store.save(_state())
    loaded = store.get('BTC/USDT')
    assert loaded == _state()


def test_get_is_case_insensitive(store):
    store.save(_state())
    assert store.get('btc/usdt') is not None


def test_get_missing_returns_none(store):
    assert store.get('ETH/USDT') is None


def test_save_upserts_and_preserves_other_symbols(store):
    store.save(_state('BTC/USDT'))
    store.save(_state('ETH/USDT'))
    store.save(_state('BTC/USDT', at='2026-06-19T00:00:00Z'))
    states = store.load()
    assert set(states) == {'BTC/USDT', 'ETH/USDT'}
    assert states['BTC/USDT'].last_rebalance_at == '2026-06-19T00:00:00Z'


def test_last_rebalance_at_returns_timestamp(store):
    store.save(_state())
    assert store.last_rebalance_at('BTC/USDT') == '2026-06-18T12:00:00Z'


def test_last_rebalance_at_none_when_absent(store):
    assert store.last_rebalance_at('BTC/USDT') is None


def test_append_event_writes_jsonl_lines(store):
    store.append_event(_event('BTC/USDT'))
    store.append_event(_event('ETH/USDT'))
    lines = store.history_path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])['symbol'] == 'BTC/USDT'
    assert json.loads(lines[1])['symbol'] == 'ETH/USDT'


def test_record_saves_state_and_appends_event(store):
    store.record(_state(), _event())
    assert store.get('BTC/USDT') is not None
    assert len(store.history_path.read_text(encoding='utf-8').splitlines()) == 1


def test_load_history_empty_when_absent(store):
    assert store.load_history() == []


def test_load_history_returns_events_in_append_order(store):
    store.append_event(_event('BTC/USDT'))
    store.append_event(_event('ETH/USDT'))
    events = store.load_history()
    assert [event['symbol'] for event in events] == ['BTC/USDT', 'ETH/USDT']
    assert events[0]['side'] == 'sell'


def test_load_history_corrupt_line_raises(store):
    store.history_path.write_text('{ not json\n', encoding='utf-8')
    with pytest.raises(StateError):
        store.load_history()


def test_corrupt_state_file_raises(store):
    store.state_path.write_text('{ not json', encoding='utf-8')
    with pytest.raises(StateError):
        store.load()


def test_invalid_state_entry_raises(store):
    store.state_path.write_text(
        json.dumps({'states': {'BTC/USDT': {'symbol': 'BTC/USDT'}}}), encoding='utf-8'
    )
    with pytest.raises(StateError):
        store.load()
