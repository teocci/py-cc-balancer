'''Phase 22 (F-6) tests: the per-account open-orders store.

Persists outstanding orders (write-ahead by client-order-id) so reconciliation can
book only real, not-yet-booked fills. Real file under tmp_path; no network.
'''

from __future__ import annotations

import pytest

from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.exceptions import StateError
from ccbalancer.models import OpenOrder
from ccbalancer.stores.order_store import OrderStore

_COID = 'ccb-20260719-0'


def _order(**kw) -> OpenOrder:
    base = dict(
        client_order_id=_COID, order_id=None, symbol='BTC/USDT', side='buy',
        amount=0.5, limit_price=100.0, status=OrderStatus.UNCONFIRMED,
        filled_booked=0.0, placed_at='2026-07-19T00:00:00Z',
    )
    base.update(kw)
    return OpenOrder(**base)


def test_load_empty_when_no_file(tmp_path):
    store = OrderStore(tmp_path / 'open_orders.json')
    assert store.list() == []
    assert store.get(_COID) is None


def test_put_then_get_round_trips(tmp_path):
    store = OrderStore(tmp_path / 'open_orders.json')
    store.put(_order())
    got = store.get(_COID)
    assert got == _order()
    assert got.order_id is None
    assert got.status is OrderStatus.UNCONFIRMED


def test_put_is_upsert_by_client_order_id(tmp_path):
    store = OrderStore(tmp_path / 'open_orders.json')
    store.put(_order())
    store.put(_order(order_id='X1', status=OrderStatus.PARTIAL, filled_booked=0.2))
    assert store.list() == [_order(order_id='X1', status=OrderStatus.PARTIAL, filled_booked=0.2)]


def test_list_filters_by_symbol(tmp_path):
    store = OrderStore(tmp_path / 'open_orders.json')
    store.put(_order())
    store.put(_order(client_order_id='ccb-20260719-1', symbol='ETH/USDT'))
    assert [o.symbol for o in store.list('BTC/USDT')] == ['BTC/USDT']
    assert len(store.list()) == 2


def test_remove_drops_the_record(tmp_path):
    store = OrderStore(tmp_path / 'open_orders.json')
    store.put(_order())
    store.remove(_COID)
    assert store.get(_COID) is None
    assert store.list() == []


def test_remove_missing_is_noop(tmp_path):
    store = OrderStore(tmp_path / 'open_orders.json')
    store.remove('nope')  # must not raise
    assert store.list() == []


def test_persists_across_instances(tmp_path):
    path = tmp_path / 'open_orders.json'
    OrderStore(path).put(_order(order_id='X1', status=OrderStatus.OPEN))
    reopened = OrderStore(path).get(_COID)
    assert reopened.order_id == 'X1'
    assert reopened.status is OrderStatus.OPEN


def test_corrupt_file_raises_state_error(tmp_path):
    path = tmp_path / 'open_orders.json'
    path.write_text('{not json', encoding='utf-8')
    with pytest.raises(StateError):
        OrderStore(path).list()
