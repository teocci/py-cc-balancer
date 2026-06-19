'''Phase 10 tests: the per-exchange quirks matrix.

Both v1 trading exchanges must resolve quirks and route order placement/cancel and
precision/min-notional handling identically through them.
'''

from __future__ import annotations

import pytest

from ccbalancer.constants import CCB_PREFIX, SUPPORTED_EXCHANGES
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import ExchangeError
from ccbalancer.stores.exchange import ExchangeStore
from ccbalancer.stores.exchange_quirks import quirks_for


class _RecordingClient:
    '''Minimal ccxt stand-in that records the params it was handed.'''

    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.cancelled: list[tuple[str, str | None]] = []

    def create_order(self, symbol, order_type, side, amount, price, params):
        self.created.append({'symbol': symbol, 'amount': amount, 'price': price, 'params': params})
        return {'id': '1', 'symbol': symbol}

    def cancel_order(self, order_id, symbol=None):
        self.cancelled.append((order_id, symbol))
        return {'id': order_id, 'status': 'canceled'}


def _store(exchange_id: str) -> tuple[ExchangeStore, _RecordingClient]:
    store = ExchangeStore(exchange_id=exchange_id, testnet=True)
    client = _RecordingClient()
    store._client = client
    return store, client


def test_every_supported_exchange_has_quirks():
    for exchange_id in SUPPORTED_EXCHANGES:
        assert quirks_for(exchange_id).exchange_id == exchange_id


def test_unsupported_exchange_raises():
    with pytest.raises(ExchangeError):
        quirks_for('kraken')


@pytest.mark.parametrize('exchange_id', SUPPORTED_EXCHANGES)
def test_create_order_tags_with_quirk_param(exchange_id):
    store, client = _store(exchange_id)
    quirks = quirks_for(exchange_id)
    store.create_order('BTC/USDT', OrderSide.SELL, 0.1, 50000.0, f'{CCB_PREFIX}abc')
    params = client.created[0]['params']
    assert params[quirks.client_order_id_param] == f'{CCB_PREFIX}abc'


@pytest.mark.parametrize('exchange_id', SUPPORTED_EXCHANGES)
def test_client_order_id_truncated_to_quirk_length(exchange_id):
    store, client = _store(exchange_id)
    quirks = quirks_for(exchange_id)
    long_tag = CCB_PREFIX + 'x' * 100
    store.create_order('BTC/USDT', OrderSide.BUY, 0.1, 50000.0, long_tag)
    tag = client.created[0]['params'][quirks.client_order_id_param]
    assert len(tag) == quirks.max_client_order_id_len


@pytest.mark.parametrize('exchange_id', SUPPORTED_EXCHANGES)
def test_cancel_passes_symbol(exchange_id):
    store, client = _store(exchange_id)
    assert quirks_for(exchange_id).cancel_requires_symbol is True
    store.cancel_order('order-1', 'BTC/USDT')
    assert client.cancelled == [('order-1', 'BTC/USDT')]
