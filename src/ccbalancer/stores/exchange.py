'''Exchange access: the only module that talks to ccxt.

A thin wrapper over a ccxt exchange client. The client is built lazily, so the
commands that never touch the network (``version``, ``pair``, ``config``) pay no
cost and tests can inject a fake. The wrapper toggles the sandbox for testnet and
translates ccxt's exception hierarchy into ccbalancer's domain errors. Managers
receive an instance by constructor injection and never import ccxt themselves.
'''

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import ccxt

from ccbalancer import constants as c
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import (
    ExchangeError,
    InsufficientBalanceError,
    OrderRejectedError,
)

if TYPE_CHECKING:
    from ccbalancer.config import AppConfig

__all__ = ['ExchangeStore']

# ccxt order type: this tool only ever places limit orders (see DESIGN.md).
_LIMIT_ORDER_TYPE = 'limit'


@dataclass(slots=True)
class ExchangeStore:
    '''Lazily-constructed ccxt client wrapper.

    Attributes:
        exchange_id: ccxt exchange id (e.g. ``'bybit'``).
        testnet: Whether to enable the exchange sandbox.
        timeout_ms: HTTP timeout passed to ccxt, in milliseconds.
        api_key: API key, or ``None`` for public-only access.
        api_secret: API secret, or ``None`` for public-only access.
    '''

    exchange_id: str
    testnet: bool
    timeout_ms: int = c.DEFAULT_HTTP_TIMEOUT_MS
    api_key: str | None = None
    api_secret: str | None = None
    _client: object | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_config(cls, config: AppConfig) -> ExchangeStore:
        '''Build a store from resolved application settings.'''
        return cls(
            exchange_id=config.exchange,
            testnet=config.testnet,
            timeout_ms=config.http_timeout_ms,
            api_key=config.api_key,
            api_secret=config.api_secret,
        )

    @property
    def client(self) -> object:
        '''The underlying ccxt client, built on first access.'''
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def load_markets(self, reload: bool = False) -> dict[str, object]:
        '''Load and return the exchange's markets keyed by symbol.'''
        with _translate('load markets'):
            return self.client.load_markets(reload)

    def fetch_balance(self) -> dict[str, object]:
        '''Return the account balance structure (free/used/total per asset).'''
        with _translate('fetch balance'):
            return self.client.fetch_balance()

    def fetch_ticker(self, symbol: str) -> dict[str, object]:
        '''Return the current ticker (last/bid/ask) for ``symbol``.'''
        with _translate(f'fetch ticker {symbol}'):
            return self.client.fetch_ticker(symbol)

    def fetch_open_orders(self, symbol: str | None = None) -> list[dict[str, object]]:
        '''Return open orders, optionally restricted to ``symbol``.'''
        with _translate('fetch open orders'):
            return self.client.fetch_open_orders(symbol)

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: float,
        price: float,
        client_order_id: str | None = None,
    ) -> dict[str, object]:
        '''Place a limit order, tagging it with ``client_order_id`` if given.'''
        params: dict[str, object] = {}
        if client_order_id is not None:
            params['clientOrderId'] = client_order_id
        with _translate(f'create order {symbol}'):
            return self.client.create_order(
                symbol, _LIMIT_ORDER_TYPE, side.value, amount, price, params
            )

    def cancel_order(self, order_id: str, symbol: str | None = None) -> dict[str, object]:
        '''Cancel the order identified by ``order_id``.'''
        with _translate(f'cancel order {order_id}'):
            return self.client.cancel_order(order_id, symbol)

    def _build_client(self) -> object:
        try:
            exchange_cls = getattr(ccxt, self.exchange_id)
        except AttributeError as exc:
            raise ExchangeError(f'Unknown ccxt exchange {self.exchange_id!r}') from exc
        client = exchange_cls(
            {
                'apiKey': self.api_key or '',
                'secret': self.api_secret or '',
                'timeout': self.timeout_ms,
                'enableRateLimit': True,
            }
        )
        client.set_sandbox_mode(self.testnet)
        return client


@contextmanager
def _translate(action: str) -> Iterator[None]:
    '''Map ccxt errors to domain errors (most specific first).'''
    try:
        yield
    except ccxt.InsufficientFunds as exc:
        raise InsufficientBalanceError(f'Cannot {action}: {exc}') from exc
    except ccxt.InvalidOrder as exc:
        raise OrderRejectedError(f'Cannot {action}: {exc}') from exc
    except ccxt.BaseError as exc:
        raise ExchangeError(f'Cannot {action}: {exc}') from exc
