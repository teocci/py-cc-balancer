'''Exchange access: the only module that talks to ccxt.

A thin wrapper over a ccxt exchange client. The client is built lazily, so the
commands that never touch the network (``version``, ``pair``, ``config``) pay no
cost and tests can inject a fake. The wrapper toggles the sandbox for testnet and
translates ccxt's exception hierarchy into ccbalancer's domain errors. Managers
receive an instance by constructor injection and never import ccxt themselves.
'''

from __future__ import annotations

import logging
import time
from collections.abc import Callable
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
from ccbalancer.stores.exchange_quirks import ExchangeQuirks, quirks_for

if TYPE_CHECKING:
    from ccbalancer.config import AppConfig

__all__ = ['ExchangeStore', 'requires_passphrase']

_logger = logging.getLogger(__name__)

# ccxt order type: this tool only ever places limit orders (see DESIGN.md).
_LIMIT_ORDER_TYPE = 'limit'

# Calls that may not retry: order placement is non-idempotent. A RequestTimeout on
# create_order leaves the outcome unknown — the order may already rest on the book —
# so blindly retrying risks a duplicate fill (see docs/cctx/17-error-handling.md).
_NO_RETRIES = 0


@dataclass(slots=True)
class ExchangeStore:
    '''Lazily-constructed ccxt client wrapper.

    Attributes:
        exchange_id: ccxt exchange id (e.g. ``'bybit'``).
        testnet: Whether to enable the exchange sandbox.
        timeout_ms: HTTP timeout passed to ccxt, in milliseconds.
        retries: Max retries of transient failures on idempotent calls.
        retry_backoff_ms: Base backoff between retries (doubled each attempt).
        api_key: API key, or ``None`` for public-only access.
        api_secret: API secret, or ``None`` for public-only access.
        password: Passphrase for venues that require one (e.g. OKX), else ``None``.
    '''

    exchange_id: str
    testnet: bool
    timeout_ms: int = c.DEFAULT_HTTP_TIMEOUT_MS
    retries: int = c.DEFAULT_HTTP_RETRIES
    retry_backoff_ms: int = c.DEFAULT_RETRY_BACKOFF_MS
    api_key: str | None = None
    api_secret: str | None = None
    password: str | None = None
    _client: object | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_config(cls, config: AppConfig) -> ExchangeStore:
        '''Build a store from resolved application settings.'''
        return cls(
            exchange_id=config.exchange,
            testnet=config.testnet,
            timeout_ms=config.http_timeout_ms,
            retries=config.http_retries,
            retry_backoff_ms=config.retry_backoff_ms,
            api_key=config.api_key,
            api_secret=config.api_secret,
            password=config.password,
        )

    def check_credentials(self) -> None:
        '''Verify required credentials are present (local check, no network).

        Raises:
            ExchangeError: If a required credential is missing or empty.
        '''
        self._request('check credentials', self.client.check_required_credentials)

    @property
    def client(self) -> object:
        '''The underlying ccxt client, built on first access.'''
        if self._client is None:
            self._client = self._build_client()
        return self._client

    @property
    def quirks(self) -> ExchangeQuirks:
        '''Execution quirks for this exchange (raises if not tradable).'''
        return quirks_for(self.exchange_id)

    def load_markets(self, reload: bool = False) -> dict[str, object]:
        '''Load and return the exchange's markets keyed by symbol.'''
        return self._request('load markets', lambda: self.client.load_markets(reload))

    def fetch_balance(self) -> dict[str, object]:
        '''Return the account balance structure (free/used/total per asset).'''
        return self._request('fetch balance', self.client.fetch_balance)

    def fetch_ticker(self, symbol: str) -> dict[str, object]:
        '''Return the current ticker (last/bid/ask) for ``symbol``.'''
        return self._request(f'fetch ticker {symbol}', lambda: self.client.fetch_ticker(symbol))

    def fetch_open_orders(self, symbol: str | None = None) -> list[dict[str, object]]:
        '''Return open orders, optionally restricted to ``symbol``.'''
        return self._request('fetch open orders', lambda: self.client.fetch_open_orders(symbol))

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        '''Return up to ``limit`` ``[time, open, high, low, close, volume]`` candles.

        Public market data: no API key required. Candle times are epoch ms.
        '''
        return self._request(
            f'fetch ohlcv {symbol} {timeframe}',
            lambda: self.client.fetch_ohlcv(symbol, timeframe, None, limit),
        )

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: float,
        price: float,
        client_order_id: str | None = None,
    ) -> dict[str, object]:
        '''Place a limit order, tagging it with ``client_order_id`` if given.

        The tag is carried in the params key this exchange expects (see
        :mod:`ccbalancer.stores.exchange_quirks`) and truncated to its length limit.
        '''
        params: dict[str, object] = {}
        if client_order_id is not None:
            quirks = self.quirks
            params[quirks.client_order_id_param] = client_order_id[: quirks.max_client_order_id_len]
        return self._request(
            f'create order {symbol}',
            lambda: self.client.create_order(
                symbol, _LIMIT_ORDER_TYPE, side.value, amount, price, params
            ),
            retries=_NO_RETRIES,
        )

    def cancel_order(self, order_id: str, symbol: str | None = None) -> dict[str, object]:
        '''Cancel the order identified by ``order_id``.

        Idempotent and safe to retry: a successful retry confirms the cancel, while
        a now-missing order surfaces as a domain error rather than a duplicate action.
        '''
        return self._request(
            f'cancel order {order_id}', lambda: self.client.cancel_order(order_id, symbol)
        )

    def _request(self, action: str, call: Callable[[], object], *, retries: int | None = None) -> object:
        '''Run ``call``, retrying transient failures and translating ccxt errors.

        Only :class:`ccxt.NetworkError` (timeouts, DDoS protection, venue
        unavailable) is retried, with exponential backoff; deterministic exchange
        errors are translated to domain errors immediately and never retried.
        '''
        budget = self.retries if retries is None else retries
        for attempt in range(budget + 1):
            try:
                return call()
            except ccxt.NetworkError as exc:
                if attempt >= budget:
                    raise ExchangeError(
                        f'Cannot {action} after {attempt + 1} attempt(s): {exc}'
                    ) from exc
                _logger.warning(
                    'Transient failure on %s (%s); retry %d/%d', action, exc, attempt + 1, budget
                )
                time.sleep(self.retry_backoff_ms / 1000.0 * 2 ** attempt)
            except ccxt.InsufficientFunds as exc:
                raise InsufficientBalanceError(f'Cannot {action}: {exc}') from exc
            except ccxt.InvalidOrder as exc:
                raise OrderRejectedError(f'Cannot {action}: {exc}') from exc
            except ccxt.BaseError as exc:
                raise ExchangeError(f'Cannot {action}: {exc}') from exc
        raise AssertionError('unreachable: retry loop always returns or raises')

    def _build_client(self) -> object:
        try:
            exchange_cls = getattr(ccxt, self.exchange_id)
        except AttributeError as exc:
            raise ExchangeError(f'Unknown ccxt exchange {self.exchange_id!r}') from exc
        client = exchange_cls(
            {
                'apiKey': self.api_key or '',
                'secret': self.api_secret or '',
                # Passphrase for venues that require one (e.g. OKX); harmless elsewhere.
                'password': self.password or '',
                'timeout': self.timeout_ms,
                'enableRateLimit': True,
                # Sync the signed-request timestamp to the exchange clock so a
                # drifting local clock does not trip the exchange's recv_window
                # (ccxt loads the offset during load_markets, which every unified
                # private call invokes). See docs/cctx/02-exchanges.md.
                'options': {'adjustForTimeDifference': True},
            }
        )
        client.set_sandbox_mode(self.testnet)
        return client


def requires_passphrase(exchange_id: str) -> bool:
    '''Return whether the exchange requires a passphrase credential (e.g. OKX).

    Reads ccxt's ``requiredCredentials`` map; instantiating the class is local
    (no network). Unknown ids return ``False``.
    '''
    exchange_cls = getattr(ccxt, exchange_id, None)
    if exchange_cls is None:
        return False
    return bool(exchange_cls().requiredCredentials.get('password'))
