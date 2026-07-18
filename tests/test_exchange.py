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

    def fetch_order(self, order_id, symbol=None):
        self.calls.append(('fetch_order', order_id, symbol))
        return {'id': order_id, 'status': 'closed', 'filled': 0.5, 'average': 100.0}


class _RaisingClient:
    '''Raises a preset ccxt error from every call.'''

    def __init__(self, error: Exception) -> None:
        self._error = error

    def fetch_ticker(self, symbol):
        raise self._error

    def create_order(self, *args, **kwargs):
        raise self._error


class _FlakyClient:
    '''Raises a transient error for the first ``fail_times`` calls, then succeeds.'''

    def __init__(self, error: Exception, fail_times: int) -> None:
        self._error = error
        self._remaining = fail_times
        self.calls = 0

    def fetch_ticker(self, symbol):
        self.calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise self._error
        return {'last': 42.0}

    def create_order(self, *args, **kwargs):
        self.calls += 1
        raise self._error


def _store_with(client: object, *, retries: int = 0) -> ExchangeStore:
    store = ExchangeStore('bybit', testnet=True, retries=retries)
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


def test_retries_transient_failure_then_succeeds(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr('time.sleep', lambda seconds: sleeps.append(seconds))
    client = _FlakyClient(ccxt.NetworkError('timeout'), fail_times=2)
    store = _store_with(client, retries=2)

    assert store.fetch_ticker('BTC/USDT') == {'last': 42.0}
    assert client.calls == 3  # two failures + one success
    assert sleeps == [0.5, 1.0]  # exponential backoff: base, then doubled


def test_exhausting_retries_raises_exchange_error(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr('time.sleep', lambda seconds: sleeps.append(seconds))
    client = _FlakyClient(ccxt.RequestTimeout('down'), fail_times=99)
    store = _store_with(client, retries=2)

    with pytest.raises(ExchangeError):
        store.fetch_ticker('BTC/USDT')
    assert client.calls == 3  # initial attempt + two retries
    assert len(sleeps) == 2


def test_create_order_never_retries(monkeypatch):
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    client = _FlakyClient(ccxt.NetworkError('timeout'), fail_times=99)
    store = _store_with(client, retries=5)  # generous budget, but placement is exempt

    with pytest.raises(ExchangeError):
        store.create_order('BTC/USDT', OrderSide.BUY, 0.1, 49000.0)
    assert client.calls == 1  # a timed-out placement may have landed: no blind retry


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
        http_retries=4,
        retry_backoff_ms=250,
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
        data_dir=None,
        config_path=None,
    )

    store = ExchangeStore.from_config(config)

    assert store.exchange_id == 'binance'
    assert store.testnet is False
    assert store.timeout_ms == 8000
    assert store.retries == 4
    assert store.retry_backoff_ms == 250
    assert store.api_key == 'key'
    assert store.api_secret == 'secret'


_HOUR_MS = 3_600_000


def _candles(count: int, *, start: int = 1_000_000_000_000, step: int = _HOUR_MS) -> list[list[float]]:
    '''An ascending run of synthetic hourly candles.'''
    return [[start + i * step, 10.0 + i, 12.0 + i, 9.0 + i, 11.0 + i, 100.0 + i] for i in range(count)]


class _PagingClient:
    '''ccxt stand-in serving candles from a fixed list, honoring since/limit.'''

    def __init__(self, candles: list[list[float]]) -> None:
        self._candles = candles
        self.calls: list[tuple[int, int]] = []

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self.calls.append((since, limit))
        window = [candle for candle in self._candles if int(float(candle[0])) >= since]
        return [list(candle) for candle in window[:limit]]


def test_fetch_ohlcv_range_paginates_all_pages():
    candles = _candles(2500)
    client = _PagingClient(candles)
    store = _store_with(client)
    until = candles[-1][0] + _HOUR_MS  # last candle is closed by `until`

    result = store.fetch_ohlcv_range('BTC/USDT', '1h', candles[0][0], until)

    assert [row[0] for row in result] == [candle[0] for candle in candles]
    assert len(client.calls) == 3  # 1000 + 1000 + 500
    # The cursor advances past each page's last open (no re-fetch of the boundary).
    assert client.calls[1][0] == candles[999][0] + _HOUR_MS


def test_fetch_ohlcv_range_drops_still_forming_last_candle():
    candles = _candles(5)
    client = _PagingClient(candles)
    store = _store_with(client)
    # `until` sits inside the last candle's interval: it has not closed yet.
    until = candles[-1][0] + 1

    result = store.fetch_ohlcv_range('BTC/USDT', '1h', candles[0][0], until)

    assert [row[0] for row in result] == [candle[0] for candle in candles[:-1]]


def test_fetch_ohlcv_range_excludes_below_since_and_at_or_after_until():
    candles = _candles(10)
    client = _PagingClient(candles)
    store = _store_with(client)
    since = candles[3][0]
    until = candles[7][0] + _HOUR_MS  # candles[7] closes exactly at until -> kept

    result = store.fetch_ohlcv_range('BTC/USDT', '1h', since, until)

    assert [row[0] for row in result] == [candle[0] for candle in candles[3:8]]


def test_fetch_ohlcv_range_normalizes_types():
    client = _PagingClient([['1000000000000', '10.5', '12.0', '9.0', '11.0', '100.0']])
    store = _store_with(client)

    result = store.fetch_ohlcv_range('BTC/USDT', '1h', 1_000_000_000_000, 1_000_000_000_000 + 2 * _HOUR_MS)

    assert result == [[1_000_000_000_000, 10.5, 12.0, 9.0, 11.0, 100.0]]
    assert isinstance(result[0][0], int)


def test_fetch_ohlcv_range_empty_when_nothing_in_window():
    client = _PagingClient(_candles(3))
    store = _store_with(client)
    future = 2_000_000_000_000

    assert store.fetch_ohlcv_range('BTC/USDT', '1h', future, future + _HOUR_MS) == []


def test_fetch_order_delegates_and_returns_status():
    client = _RecordingClient()
    store = _store_with(client)

    result = store.fetch_order('order-9', 'BTC/USDT')

    assert result == {'id': 'order-9', 'status': 'closed', 'filled': 0.5, 'average': 100.0}
    assert ('fetch_order', 'order-9', 'BTC/USDT') in client.calls


def test_fetch_order_is_retryable_on_transient_error(monkeypatch):
    import ccxt

    class _FlakyFetch:
        def __init__(self) -> None:
            self.calls = 0

        def fetch_order(self, order_id, symbol=None):
            self.calls += 1
            if self.calls == 1:
                raise ccxt.NetworkError('boom')
            return {'id': order_id, 'status': 'open', 'filled': 0.0}

    monkeypatch.setattr('time.sleep', lambda _s: None)
    client = _FlakyFetch()
    store = _store_with(client, retries=2)

    assert store.fetch_order('id-1', 'BTC/USDT')['status'] == 'open'
    assert client.calls == 2  # one transient failure, then success


def test_find_order_by_client_id_matches_open_order():
    store = FakeExchangeStore(open_orders=[
        {'symbol': 'BTC/USDT', 'id': 'x1', 'clientOrderId': 'ccb-a'},
        {'symbol': 'BTC/USDT', 'id': 'x2', 'clientOrderId': 'ccb-b'},
    ])
    found = store.find_order_by_client_id('ccb-b', 'BTC/USDT')
    assert found['id'] == 'x2'
    assert store.find_order_by_client_id('ccb-missing', 'BTC/USDT') is None


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
