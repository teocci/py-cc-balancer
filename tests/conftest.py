'''Shared pytest fixtures.'''

from __future__ import annotations

import pytest

from ccbalancer import config as config_mod
from ccbalancer.constants import (
    ENV_API_KEY,
    ENV_API_SECRET,
    ENV_CONFIG,
    ENV_EXCHANGE,
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
    for key in (ENV_API_KEY, ENV_API_SECRET, ENV_EXCHANGE, ENV_TESTNET, ENV_CONFIG):
        monkeypatch.delenv(key, raising=False)
    return directory


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
        created: Orders placed via ``create_order``, in call order.
        cancelled: Cancellations made via ``cancel_order``, in call order.
        markets_loaded: Number of times ``load_markets`` was called.
    '''

    def __init__(
        self,
        *,
        markets: dict[str, object] | None = None,
        balance: dict[str, object] | None = None,
        tickers: dict[str, object] | None = None,
        open_orders: list[dict[str, object]] | None = None,
    ) -> None:
        self.markets = markets or {}
        self.balance = balance or {'free': {}, 'used': {}, 'total': {}}
        self.tickers = tickers or {}
        self.open_orders = list(open_orders or [])
        self.created: list[dict[str, object]] = []
        self.cancelled: list[dict[str, object]] = []
        self.markets_loaded = 0

    def load_markets(self, reload: bool = False) -> dict[str, object]:
        self.markets_loaded += 1
        return self.markets

    def fetch_balance(self) -> dict[str, object]:
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
