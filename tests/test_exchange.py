'''Phase 4 tests: the ccxt exchange-store wrapper and its fake.

The real :class:`ExchangeStore` never reaches the network here: delegation tests
inject a recording client via ``_client``, error-translation tests inject a client
that raises ccxt errors, and the client-construction test registers a stub class
on the ``ccxt`` module so ``set_sandbox_mode`` and options can be asserted.
'''

from __future__ import annotations

from pathlib import Path

import ccxt
import pytest

from ccbalancer.config import AppConfig, Defaults, SafetyConfig
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import (
    ExchangeError,
    InsufficientBalanceError,
    OrderRejectedError,
)
from ccbalancer.stores.exchange import ExchangeStore

from .conftest import FakeExchangeStore


class _RecordingClient:
    '''Captures call arguments and returns canned values.'''

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def load_markets(self, reload=False):
        self.calls.append(('load_markets', reload))
        return {'BTC/USDT': {}}

    def fetch_balance(self):
        self.calls.append(('fetch_balance',))
        return {'total': {}}

    def fetch_ticker(self, symbol):
        self.calls.append(('fetch_ticker', symbol))
        return {'last': 100.0}

    def fetch_open_orders(self, symbol=None):
        self.calls.append(('fetch_open_orders', symbol))
        return []

    def create_order(self, symbol, type, side, amount, price, params):
        self.calls.append(('create_order', symbol, type, side, amount, price, params))
        return {'id': 'order-1'}

    def cancel_order(self, order_id, symbol=None):
        self.calls.append(('cancel_order', order_id, symbol))
        return {'id': order_id, 'status': 'canceled'}


class _RaisingClient:
    '''Raises a preset ccxt error from every call.'''

    def __init__(self, error: Exception) -> None:
        self._error = error

    def fetch_ticker(self, symbol):
        raise self._error

    def create_order(self, *args, **kwargs):
        raise self._error


def _store_with(client: object) -> ExchangeStore:
    store = ExchangeStore('bybit', testnet=True)
    store._client = client
    return store


def test_delegates_read_methods_to_client():
    client = _RecordingClient()
    store = _store_with(client)

    assert store.load_markets(reload=True) == {'BTC/USDT': {}}
    assert store.fetch_balance() == {'total': {}}
    assert store.fetch_ticker('BTC/USDT') == {'last': 100.0}
    assert store.fetch_open_orders('BTC/USDT') == []

    assert ('load_markets', True) in client.calls
    assert ('fetch_ticker', 'BTC/USDT') in client.calls
    assert ('fetch_open_orders', 'BTC/USDT') in client.calls


def test_create_order_uses_limit_type_side_value_and_client_id():
    client = _RecordingClient()
    store = _store_with(client)

    store.create_order('BTC/USDT', OrderSide.SELL, 0.5, 51000.0, client_order_id='ccb-abc')

    call = client.calls[-1]
    assert call == ('create_order', 'BTC/USDT', 'limit', 'sell', 0.5, 51000.0, {'clientOrderId': 'ccb-abc'})


def test_create_order_omits_client_id_when_absent():
    client = _RecordingClient()
    store = _store_with(client)

    store.create_order('BTC/USDT', OrderSide.BUY, 0.1, 49000.0)

    assert client.calls[-1][-1] == {}


def test_cancel_order_delegates():
    client = _RecordingClient()
    store = _store_with(client)

    assert store.cancel_order('order-1', 'BTC/USDT')['status'] == 'canceled'
    assert ('cancel_order', 'order-1', 'BTC/USDT') in client.calls


@pytest.mark.parametrize(
    'error, expected',
    [
        (ccxt.InsufficientFunds('low'), InsufficientBalanceError),
        (ccxt.InvalidOrder('bad'), OrderRejectedError),
        (ccxt.NetworkError('down'), ExchangeError),
        (ccxt.AuthenticationError('nope'), ExchangeError),
    ],
)
def test_translates_ccxt_errors(error, expected):
    store = _store_with(_RaisingClient(error))
    with pytest.raises(expected):
        store.fetch_ticker('BTC/USDT')


def test_build_client_unknown_exchange_raises_exchange_error():
    store = ExchangeStore('definitely_not_an_exchange', testnet=False)
    with pytest.raises(ExchangeError):
        _ = store.client


def test_build_client_applies_sandbox_and_options(monkeypatch):
    captured: dict[str, object] = {}

    class _StubExchange:
        def __init__(self, options):
            captured['options'] = options
            self.sandbox = None

        def set_sandbox_mode(self, value):
            self.sandbox = value

    monkeypatch.setattr(ccxt, 'stubex', _StubExchange, raising=False)
    store = ExchangeStore('stubex', testnet=True, timeout_ms=7000, api_key='k', api_secret='s')

    client = store.client

    assert client is store.client  # lazily built once, then cached
    assert client.sandbox is True
    assert captured['options']['timeout'] == 7000
    assert captured['options']['apiKey'] == 'k'
    assert captured['options']['secret'] == 's'
    assert captured['options']['enableRateLimit'] is True
    assert captured['options']['options']['adjustForTimeDifference'] is True


def test_from_config_maps_fields():
    config = AppConfig(
        exchange='binance',
        testnet=False,
        quote_sanity_pct=15.0,
        limit_offset_pct=0.0,
        min_interval_hours=0,
        http_timeout_ms=8000,
        target_review_band_pct=20.0,
        data_exchange='binance',
        decision_timeframes=('1m', '5m', '15m'),
        analysis_timeframes=('1h', '4h', '1d', '1w'),
        ohlcv_limit=500,
        defaults=Defaults(80.0, 20.0, 5.0, 10.0, 0.0),
        safety=SafetyConfig(1000.0, Path('STOP')),
        api_key='key',
        api_secret='secret',
        app_dir=None,
        config_path=None,
    )

    store = ExchangeStore.from_config(config)

    assert store.exchange_id == 'binance'
    assert store.testnet is False
    assert store.timeout_ms == 8000
    assert store.api_key == 'key'
    assert store.api_secret == 'secret'


def test_fake_exchange_records_orders(fake_exchange: FakeExchangeStore):
    fake_exchange.create_order('BTC/USDT', OrderSide.BUY, 0.2, 49000.0, client_order_id='ccb-1')
    fake_exchange.cancel_order('fake-1', 'BTC/USDT')

    assert fake_exchange.created[0]['side'] == 'buy'
    assert fake_exchange.created[0]['type'] == 'limit'
    assert fake_exchange.created[0]['clientOrderId'] == 'ccb-1'
    assert fake_exchange.cancelled[0]['id'] == 'fake-1'


def test_fake_exchange_unknown_ticker_raises(fake_exchange: FakeExchangeStore):
    with pytest.raises(ExchangeError):
        fake_exchange.fetch_ticker('ETH/USDT')


def test_fake_exchange_filters_open_orders_by_symbol():
    store = FakeExchangeStore(
        open_orders=[{'symbol': 'BTC/USDT', 'id': '1'}, {'symbol': 'ETH/USDT', 'id': '2'}]
    )
    assert len(store.fetch_open_orders()) == 2
    assert [o['id'] for o in store.fetch_open_orders('ETH/USDT')] == ['2']
