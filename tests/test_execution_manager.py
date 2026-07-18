'''Phase 10 tests: ExecutionManager and the pure safety guard helpers.'''

from __future__ import annotations

from pathlib import Path

import pytest

from ccbalancer.constants import CCB_PREFIX
from ccbalancer.enums.side import OrderSide
from ccbalancer.enums.skip_reason import SkipReason
from ccbalancer.exceptions import OrderRejectedError
from ccbalancer.managers.execution_manager import (
    ExecutionManager,
    confirm_token,
    is_ours,
    kill_switch_active,
    session_notional,
)
from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.managers.reconciliation_manager import ReconciliationManager
from ccbalancer.models import ProposedOrder, RebalanceDecision
from ccbalancer.stores.decision_store import DecisionStore
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.stores.order_store import OrderStore
from ccbalancer.stores.state_store import StateStore

from .conftest import FakeExchangeStore

_NOW = '2026-06-19T12:00:00Z'


def _ok(symbol='BTC/USDT', side=OrderSide.SELL, amount=0.12, price=50000.0) -> RebalanceDecision:
    order = ProposedOrder(symbol, side, amount, price, amount * price)
    return RebalanceDecision(
        symbol=symbol, rebalance=True, reason=SkipReason.OK, drift_pct=10.9,
        target_volatile_pct=80.0, current_volatile_pct=90.9, total_value=55000.0,
        proposed_order=order, detail='sell',
    )


def _hold(symbol='ETH/USDT') -> RebalanceDecision:
    return RebalanceDecision(
        symbol=symbol, rebalance=False, reason=SkipReason.WITHIN_BAND, drift_pct=1.0,
        target_volatile_pct=80.0, current_volatile_pct=81.0, total_value=1000.0, detail='within band',
    )


def _manager(tmp_path, exchange) -> ExecutionManager:
    state = StateStore(tmp_path / 'state.json', tmp_path / 'history.jsonl')
    order_store = OrderStore(tmp_path / 'open_orders.json')
    reconciler = ReconciliationManager(
        exchange=exchange,
        order_store=order_store,
        ledger_store=LedgerStore(tmp_path / 'ledger.jsonl'),
        state_store=state,
        exchange_id='bybit',
        testnet=True,
    )
    return ExecutionManager(
        exchange=exchange,
        state_store=state,
        order_store=order_store,
        decision_store=DecisionStore(tmp_path / 'decision_log.jsonl'),
        reconciler=reconciler,
        exchange_id='bybit',
        testnet=True,
    )


# --- pure guard helpers ---------------------------------------------------


def test_confirm_token_is_none_when_no_actionable():
    assert confirm_token([_hold()], exchange='bybit', testnet=True) is None


def test_confirm_token_stable_across_price_and_amount_changes():
    a = confirm_token([_ok(price=50000.0, amount=0.12)], exchange='bybit', testnet=True)
    b = confirm_token([_ok(price=51000.0, amount=0.20)], exchange='bybit', testnet=True)
    assert a == b is not None


def test_confirm_token_changes_with_side_and_context():
    sell = confirm_token([_ok(side=OrderSide.SELL)], exchange='bybit', testnet=True)
    buy = confirm_token([_ok(side=OrderSide.BUY)], exchange='bybit', testnet=True)
    testnet_off = confirm_token([_ok()], exchange='bybit', testnet=False)
    base = confirm_token([_ok()], exchange='bybit', testnet=True)
    assert sell != buy
    assert base != testnet_off


def test_session_notional_sums_actionable_only():
    assert session_notional([_ok(amount=0.1, price=50000.0), _hold()]) == pytest.approx(5000.0)


def test_kill_switch_active(tmp_path):
    path = tmp_path / 'STOP'
    assert kill_switch_active(path) is False
    path.write_text('', encoding='utf-8')
    assert kill_switch_active(path) is True


def test_is_ours_detects_prefix():
    assert is_ours({'clientOrderId': f'{CCB_PREFIX}1'}) is True
    assert is_ours({'clientOrderId': 'other'}) is False
    assert is_ours({}) is False


# --- execute --------------------------------------------------------------


def test_execute_places_tagged_order_and_tracks_pending_without_booking_a_fill(tmp_path, fake_exchange):
    # F-6: a resting maker order must NOT be booked as a fill on submission. It is
    # tracked pending; reconciliation books the real fill later.
    manager = _manager(tmp_path, fake_exchange)
    results = manager.execute([_ok()], now=_NOW)
    assert results[0].placed is True
    assert results[0].status == 'submitted'
    placed = fake_exchange.created[0]
    assert placed['clientOrderId'].startswith(CCB_PREFIX)
    # No fabricated fill: the ledger stays empty until a real fill is reconciled.
    assert LedgerStore(tmp_path / 'ledger.jsonl').load() == []
    # The order is tracked write-ahead for reconciliation (confirmed open, nothing booked).
    tracked = OrderStore(tmp_path / 'open_orders.json').list('BTC/USDT')
    assert len(tracked) == 1
    assert tracked[0].status is OrderStatus.OPEN
    assert tracked[0].filled_booked == 0.0
    assert tracked[0].order_id == placed['id']


def test_execute_books_fill_when_order_fills_on_placement(tmp_path):
    # A marketable order that fills immediately is captured by the post-place reconcile.
    exchange = FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
    manager = _manager(tmp_path, exchange)
    manager.execute([_ok(amount=0.12, price=50000.0)], now=_NOW)
    # Override the freshly-created order's status to a full fill, then reconcile.
    order_id = exchange.created[0]['id']
    exchange.order_status[order_id] = {'id': order_id, 'status': 'closed', 'filled': 0.12,
                                       'average': 50000.0}
    manager.reconciler.reconcile(now=_NOW)

    fills = LedgerStore(tmp_path / 'ledger.jsonl').load()
    assert len(fills) == 1 and fills[0]['qty'] == pytest.approx(0.12)
    assert OrderStore(tmp_path / 'open_orders.json').list() == []  # terminal -> dropped


def test_execute_logs_decision_for_every_pair(tmp_path, fake_exchange):
    manager = _manager(tmp_path, fake_exchange)
    manager.execute([_ok(), _hold()], now=_NOW)
    records = DecisionStore(tmp_path / 'decision_log.jsonl').load()
    assert [r['command'] for r in records] == ['rebalance', 'rebalance']


def test_execute_skips_hold_without_placing(tmp_path, fake_exchange):
    manager = _manager(tmp_path, fake_exchange)
    results = manager.execute([_hold()], now=_NOW)
    assert results[0].status == 'skipped'
    assert fake_exchange.created == []
    assert not (tmp_path / 'ledger.jsonl').exists()


def test_execute_cancels_own_stale_orders_first(tmp_path):
    exchange = FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
        open_orders=[
            {'id': 'mine', 'symbol': 'BTC/USDT', 'clientOrderId': f'{CCB_PREFIX}old'},
            {'id': 'theirs', 'symbol': 'BTC/USDT', 'clientOrderId': 'manual'},
        ],
    )
    manager = _manager(tmp_path, exchange)
    manager.execute([_ok()], now=_NOW)
    assert [c['id'] for c in exchange.cancelled] == ['mine']


def test_execute_records_failure_without_persisting(tmp_path):
    class _Rejecting(FakeExchangeStore):
        def create_order(self, *args, **kwargs):
            raise OrderRejectedError('rejected')

    exchange = _Rejecting(
        markets={'BTC/USDT': {'active': True}},
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
    manager = _manager(tmp_path, exchange)
    results = manager.execute([_ok()], now=_NOW)
    assert results[0].status == 'failed'
    assert results[0].placed is False
    assert not (tmp_path / 'state.json').exists()
    assert not (tmp_path / 'ledger.jsonl').exists()
    # A rejected order never reached the book: the write-ahead record is removed.
    assert OrderStore(tmp_path / 'open_orders.json').list() == []


def test_execute_leaves_unconfirmed_record_on_network_error(tmp_path):
    from ccbalancer.exceptions import ExchangeError

    class _Timeout(FakeExchangeStore):
        def create_order(self, *args, **kwargs):
            raise ExchangeError('timeout')

    exchange = _Timeout(
        markets={'BTC/USDT': {'active': True}},
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
    results = _manager(tmp_path, exchange).execute([_ok()], now=_NOW)

    assert results[0].status == 'unconfirmed'
    assert results[0].placed is False
    # Left tracked (write-ahead) so reconcile can resolve it by client-order-id.
    tracked = OrderStore(tmp_path / 'open_orders.json').list()
    assert len(tracked) == 1 and tracked[0].status is OrderStatus.UNCONFIRMED
    assert LedgerStore(tmp_path / 'ledger.jsonl').load() == []


def test_owned_open_orders_filters_by_symbol_and_ownership(tmp_path):
    exchange = FakeExchangeStore(open_orders=[
        {'id': 'a', 'symbol': 'BTC/USDT', 'clientOrderId': f'{CCB_PREFIX}1'},
        {'id': 'b', 'symbol': 'ETH/USDT', 'clientOrderId': f'{CCB_PREFIX}2'},
        {'id': 'c', 'symbol': 'BTC/USDT', 'clientOrderId': 'manual'},
    ])
    manager = _manager(tmp_path, exchange)
    assert [o['id'] for o in manager.owned_open_orders(['BTC/USDT'])] == ['a']
    assert {o['id'] for o in manager.owned_open_orders()} == {'a', 'b'}
