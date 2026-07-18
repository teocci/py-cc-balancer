'''Phase 22 (F-6) tests: order-status reconciliation.

Books only fills that actually occurred, from real exchange order status — handling
resting orders, partial-fill deltas (no double-book), timeout recovery by
client-order-id, and terminal cleanup. Real stores under tmp_path; fake exchange.
'''

from __future__ import annotations

from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.managers.reconciliation_manager import ReconciliationManager
from ccbalancer.models import OpenOrder
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.stores.order_store import OrderStore
from ccbalancer.stores.state_store import StateStore

from .conftest import FakeExchangeStore

_NOW = '2026-07-19T00:00:00Z'
_COID = 'ccb-20260719-0'


def _pending(**kw) -> OpenOrder:
    base = dict(
        client_order_id=_COID, order_id='X1', symbol='BTC/USDT', side='buy',
        amount=1.0, limit_price=100.0, status=OrderStatus.OPEN,
        filled_booked=0.0, placed_at=_NOW,
    )
    base.update(kw)
    return OpenOrder(**base)


def _setup(tmp_path, *, order_status=None, open_orders=None):
    order_store = OrderStore(tmp_path / 'open_orders.json')
    ledger = LedgerStore(tmp_path / 'ledger.jsonl')
    state = StateStore(tmp_path / 'state.json', tmp_path / 'history.jsonl')
    exchange = FakeExchangeStore(
        exchange_id='binance', order_status=order_status or {}, open_orders=open_orders or []
    )
    manager = ReconciliationManager(
        exchange=exchange, order_store=order_store, ledger_store=ledger,
        state_store=state, exchange_id='binance', testnet=False,
    )
    return manager, order_store, ledger, state, exchange


def test_resting_order_books_nothing(tmp_path):
    manager, order_store, ledger, _state, _ex = _setup(
        tmp_path, order_status={'X1': {'id': 'X1', 'status': 'open', 'filled': 0.0}}
    )
    order_store.put(_pending())

    results = manager.reconcile(now=_NOW)

    assert ledger.load() == []                       # the F-6 regression: no fabricated fill
    assert results[0].newly_filled == 0.0
    assert order_store.get(_COID).status is OrderStatus.OPEN


def test_full_fill_books_one_fill_and_removes_record(tmp_path):
    manager, order_store, ledger, state, _ex = _setup(
        tmp_path,
        order_status={'X1': {'id': 'X1', 'status': 'closed', 'filled': 1.0, 'average': 99.0}},
    )
    order_store.put(_pending())

    results = manager.reconcile(now=_NOW)

    fills = ledger.load()
    assert len(fills) == 1
    assert fills[0]['qty'] == 1.0 and fills[0]['price'] == 99.0 and fills[0]['side'] == 'buy'
    assert order_store.get(_COID) is None            # terminal -> dropped
    assert results[0].newly_filled == 1.0 and results[0].total_filled == 1.0
    assert state.last_rebalance_at('BTC/USDT') == _NOW


def test_partial_then_full_books_only_the_delta(tmp_path):
    manager, order_store, ledger, _state, exchange = _setup(
        tmp_path,
        order_status={'X1': {'id': 'X1', 'status': 'open', 'filled': 0.4, 'average': 100.0}},
    )
    order_store.put(_pending())

    manager.reconcile(now=_NOW)                        # books 0.4
    assert [f['qty'] for f in ledger.load()] == [0.4]
    assert order_store.get(_COID).status is OrderStatus.PARTIAL
    assert order_store.get(_COID).filled_booked == 0.4

    exchange.order_status['X1'] = {'id': 'X1', 'status': 'closed', 'filled': 1.0, 'average': 100.0}
    manager.reconcile(now=_NOW)                        # books only the 0.6 delta

    assert [f['qty'] for f in ledger.load()] == [0.4, 0.6]
    assert order_store.get(_COID) is None


def test_idempotent_reconcile_writes_nothing_second_pass(tmp_path):
    manager, order_store, ledger, _state, _ex = _setup(
        tmp_path,
        order_status={'X1': {'id': 'X1', 'status': 'open', 'filled': 0.5, 'average': 100.0}},
    )
    order_store.put(_pending())

    manager.reconcile(now=_NOW)
    manager.reconcile(now=_NOW)                        # same status -> delta 0

    assert [f['qty'] for f in ledger.load()] == [0.5]


def test_unconfirmed_resolved_by_client_order_id(tmp_path):
    # Placement timed out: no exchange id yet, but the order landed and rests.
    manager, order_store, ledger, _state, _ex = _setup(
        tmp_path,
        order_status={'X9': {'id': 'X9', 'status': 'closed', 'filled': 1.0, 'average': 100.0}},
        open_orders=[{'symbol': 'BTC/USDT', 'id': 'X9', 'clientOrderId': _COID}],
    )
    order_store.put(_pending(order_id=None, status=OrderStatus.UNCONFIRMED))

    manager.reconcile(now=_NOW)

    assert [f['qty'] for f in ledger.load()] == [1.0]
    assert order_store.get(_COID) is None


def test_unresolvable_unconfirmed_left_untracked_books_nothing(tmp_path):
    manager, order_store, ledger, _state, _ex = _setup(tmp_path)  # no open order, no status
    order_store.put(_pending(order_id=None, status=OrderStatus.UNCONFIRMED))

    results = manager.reconcile(now=_NOW)

    assert ledger.load() == []
    assert order_store.get(_COID).status is OrderStatus.UNCONFIRMED  # still tracked for next pass
    assert results[0].status == OrderStatus.UNCONFIRMED.value


def test_canceled_with_partial_books_partial_then_removes(tmp_path):
    manager, order_store, ledger, _state, _ex = _setup(
        tmp_path,
        order_status={'X1': {'id': 'X1', 'status': 'canceled', 'filled': 0.3, 'average': 100.0}},
    )
    order_store.put(_pending())

    manager.reconcile(now=_NOW)

    assert [f['qty'] for f in ledger.load()] == [0.3]  # partial booked before cleanup
    assert order_store.get(_COID) is None              # canceled is terminal


def test_reconcile_filters_by_symbol(tmp_path):
    manager, order_store, ledger, _state, _ex = _setup(
        tmp_path,
        order_status={
            'X1': {'id': 'X1', 'status': 'closed', 'filled': 1.0, 'average': 100.0},
            'X2': {'id': 'X2', 'status': 'closed', 'filled': 2.0, 'average': 50.0},
        },
    )
    order_store.put(_pending())
    order_store.put(_pending(client_order_id='ccb-1', order_id='X2', symbol='ETH/USDT', amount=2.0))

    manager.reconcile(['BTC/USDT'], now=_NOW)

    assert [f['symbol'] for f in ledger.load()] == ['BTC/USDT']
    assert order_store.get('ccb-1') is not None         # ETH order untouched
