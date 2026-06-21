'''Shared pytest fixtures.'''

from __future__ import annotations

import sys
import types

import pytest

from ccbalancer import config as config_mod
from ccbalancer.constants import (
    ENV_API_KEY,
    ENV_API_SECRET,
    ENV_AUTH_BACKEND,
    ENV_CONFIG,
    ENV_EXCHANGE,
    ENV_PROFILE,
    ENV_TESTNET,
)
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import ExchangeError


@pytest.fixture
def appdir(tmp_path, monkeypatch):
    '''Isolate the app dir and CWD; clear ccbalancer env vars.'''
    directory = tmp_path / '.ccbalancer'
    monkeypatch.setattr(config_mod, 'resolve_app_dir', lambda: directory)
    monkeypatch.chdir(tmp_path)
    for key in (ENV_API_KEY, ENV_API_SECRET, ENV_EXCHANGE, ENV_TESTNET, ENV_CONFIG,
                ENV_PROFILE, ENV_AUTH_BACKEND):
        monkeypatch.delenv(key, raising=False)
    return directory


class FakeKeyring:
    '''In-memory stand-in for the ``keyring`` module (service/username store).'''

    class errors:  # noqa: N801 - mirrors the real ``keyring.errors`` namespace
        class KeyringError(Exception):
            pass

        class PasswordDeleteError(KeyringError):
            pass

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self.store[(service, username)]
        except KeyError as exc:
            raise self.errors.PasswordDeleteError(username) from exc


@pytest.fixture
def fake_keyring(monkeypatch):
    '''Install a fake ``keyring`` module so the keyring backend works offline.'''
    fake = FakeKeyring()
    module = types.ModuleType('keyring')
    module.set_password = fake.set_password
    module.get_password = fake.get_password
    module.delete_password = fake.delete_password
    module.errors = FakeKeyring.errors
    monkeypatch.setitem(sys.modules, 'keyring', module)
    return fake


class FakeExchangeStore:
    '''In-memory stand-in for :class:`ExchangeStore` (never hits the network).

    Mirrors the public method surface of the real store so managers and tests
    can run against it. Reads return preconfigured fixtures; writes record their
    arguments on ``created`` and ``cancelled`` for assertions.

    Attributes:
        markets: Markets returned by ``load_markets``.
        balance: Balance structure returned by ``fetch_balance``.
        tickers: Symbol-keyed tickers returned by ``fetch_ticker``.
        open_orders: Open orders returned by ``fetch_open_orders``.
        ohlcv: ``(symbol, timeframe)`` -> candle list returned by ``fetch_ohlcv``.
        offline: When ``True``, every fetch raises :class:`ExchangeError`.
        created: Orders placed via ``create_order``, in call order.
        cancelled: Cancellations made via ``cancel_order``, in call order.
        markets_loaded: Number of times ``load_markets`` was called.
        ohlcv_calls: ``(symbol, timeframe, limit)`` tuples seen by ``fetch_ohlcv``.
    '''

    def __init__(
        self,
        *,
        markets: dict[str, object] | None = None,
        balance: dict[str, object] | None = None,
        tickers: dict[str, object] | None = None,
        open_orders: list[dict[str, object]] | None = None,
        ohlcv: dict[tuple[str, str], list[list[float]]] | None = None,
        offline: bool = False,
    ) -> None:
        self.markets = markets or {}
        self.balance = balance or {'free': {}, 'used': {}, 'total': {}}
        self.tickers = tickers or {}
        self.open_orders = list(open_orders or [])
        self.ohlcv = ohlcv or {}
        self.offline = offline
        self.created: list[dict[str, object]] = []
        self.cancelled: list[dict[str, object]] = []
        self.markets_loaded = 0
        self.ohlcv_calls: list[tuple[str, str, int]] = []

    def load_markets(self, reload: bool = False) -> dict[str, object]:
        self.markets_loaded += 1
        return self.markets

    def check_credentials(self) -> None:
        return None

    def fetch_balance(self) -> dict[str, object]:
        if self.offline:
            raise ExchangeError('offline: cannot fetch balance')
        return self.balance

    def fetch_ticker(self, symbol: str) -> dict[str, object]:
        try:
            return self.tickers[symbol]
        except KeyError as exc:
            raise ExchangeError(f'No ticker for {symbol}') from exc

    def fetch_open_orders(self, symbol: str | None = None) -> list[dict[str, object]]:
        if symbol is None:
            return list(self.open_orders)
        return [order for order in self.open_orders if order.get('symbol') == symbol]

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        self.ohlcv_calls.append((symbol, timeframe, limit))
        if self.offline:
            raise ExchangeError(f'offline: cannot fetch ohlcv {symbol} {timeframe}')
        return list(self.ohlcv.get((symbol, timeframe), []))

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: float,
        price: float,
        client_order_id: str | None = None,
    ) -> dict[str, object]:
        order = {
            'id': f'fake-{len(self.created) + 1}',
            'symbol': symbol,
            'type': 'limit',
            'side': side.value,
            'amount': amount,
            'price': price,
            'clientOrderId': client_order_id,
        }
        self.created.append(order)
        return order

    def cancel_order(self, order_id: str, symbol: str | None = None) -> dict[str, object]:
        result = {'id': order_id, 'symbol': symbol, 'status': 'canceled'}
        self.cancelled.append(result)
        return result


@pytest.fixture
def fake_exchange() -> FakeExchangeStore:
    '''A :class:`FakeExchangeStore` preloaded with one BTC/USDT market.'''
    return FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        balance={
            'free': {'BTC': 1.0, 'USDT': 5000.0},
            'used': {'BTC': 0.0, 'USDT': 0.0},
            'total': {'BTC': 1.0, 'USDT': 5000.0},
        },
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
