'''Exchange access: the only module that talks to ccxt.

A thin wrapper over a ccxt exchange client. The client is built lazily, so the
commands that never touch the network (``version``, ``pair``, ``config``) pay no
cost and tests can inject a fake. The wrapper toggles the sandbox for testnet and
translates ccxt's exception hierarchy into ccbalancer's domain errors. Managers
receive an instance by constructor injection and never import ccxt themselves.
'''

from __future__ import annotations

import hashlib
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
from ccbalancer.utils.candles import CANDLE_TIME as _CANDLE_TIME
from ccbalancer.utils.candles import candle_to_record, record_to_candle
from ccbalancer.utils.timeutil import timeframe_to_seconds

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

    def fetch_order(self, order_id: str, symbol: str | None = None) -> dict[str, object]:
        '''Return the current status of ``order_id`` (filled/average/status/fee).

        An idempotent read, so it retries transient failures like the other reads.
        Used by reconciliation to book only fills that actually occurred.
        '''
        return self._request(
            f'fetch order {order_id}', lambda: self.client.fetch_order(order_id, symbol)
        )

    def find_order_by_client_id(
        self, client_order_id: str, symbol: str | None = None
    ) -> dict[str, object] | None:
        '''Return our open order matching ``client_order_id``, or ``None``.

        Resolves a placement whose exchange id is unknown (e.g. a ``create_order``
        timeout) by scanning open orders for the deterministic client-order-id. A
        resting order is found here; one that already closed has left the open list
        and is left for the caller to handle.
        '''
        for order in self.fetch_open_orders(symbol):
            if order.get('clientOrderId') == client_order_id:
                return order
        return None

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        '''Return up to ``limit`` ``[time, open, high, low, close, volume]`` candles.

        Public market data: no API key required. Candle times are epoch ms.
        '''
        return self._request(
            f'fetch ohlcv {symbol} {timeframe}',
            lambda: self.client.fetch_ohlcv(symbol, timeframe, None, limit),
        )

    def fetch_ohlcv_range(
        self, symbol: str, timeframe: str, since_ms: int, until_ms: int
    ) -> list[list[float]]:
        '''Return the closed ``[t,o,h,l,c,v]`` candles with open in ``[since_ms, until_ms)``.

        Pages ccxt ``fetch_ohlcv(since=cursor, limit=…)``, advancing the cursor past
        each page's last open so no candle is re-downloaded, until the venue runs
        out of data or the cursor reaches ``until_ms``. Candles are normalized to
        ccxt's uniform shape; the still-forming last candle (one whose interval has
        not closed by ``until_ms``) is dropped. Public market data — no key needed.
        '''
        interval_ms = timeframe_to_seconds(timeframe) * 1000
        collected: list[list[float]] = []
        seen: set[int] = set()
        cursor = since_ms
        while cursor < until_ms:
            page = self._fetch_ohlcv_page(symbol, timeframe, cursor)
            if not page:
                break
            self._collect_closed(page, since_ms, until_ms, interval_ms, seen, collected)
            next_cursor = int(page[-1][_CANDLE_TIME]) + interval_ms
            if len(page) < c.SIM_FETCH_PAGE_LIMIT or next_cursor <= cursor:
                break
            cursor = next_cursor
        return collected

    def _fetch_ohlcv_page(self, symbol: str, timeframe: str, since_ms: int) -> list[list[float]]:
        '''Fetch one page of candles starting at ``since_ms`` (idempotent read).'''
        return self._request(
            f'fetch ohlcv {symbol} {timeframe}',
            lambda: self.client.fetch_ohlcv(symbol, timeframe, since_ms, c.SIM_FETCH_PAGE_LIMIT),
        )

    @staticmethod
    def _collect_closed(
        page: list[list[float]],
        since_ms: int,
        until_ms: int,
        interval_ms: int,
        seen: set[int],
        out: list[list[float]],
    ) -> None:
        '''Append normalized, in-range, closed, not-yet-seen candles from ``page``.'''
        for candle in page:
            open_ms = int(candle[_CANDLE_TIME])
            if open_ms < since_ms or open_ms + interval_ms > until_ms or open_ms in seen:
                continue
            seen.add(open_ms)
            out.append(record_to_candle(candle_to_record(candle)))

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

    def account_ref(self) -> str | None:
        '''Return a best-effort stable, hashed exchange account id, or ``None``.

        Prefers ccxt's unified ``fetch_accounts()``; falls back to a per-venue
        private endpoint (Bybit ``/v5/user/query-api``, Binance ``/api/v3/account``,
        OKX ``/api/v5/account/config``). The underlying uid is an account/user id —
        stable across API-key rotation — so it recognizes the same real account
        after a re-login. The uid (namespaced by exchange id) is hashed into an
        opaque fixed-length key. Best-effort: never raises; returns ``None`` when
        no id is obtainable (unsupported venue, auth/network failure).
        '''
        uid = self._raw_account_uid()
        if uid is None:
            return None
        return hashlib.sha256(f'{self.exchange_id}:{uid}'.encode()).hexdigest()[:32]

    def _raw_account_uid(self) -> str | None:
        '''Fetch the raw exchange account uid via unified then per-venue calls.

        ``self.client`` is read inside each ``try`` so a failing lazy client build
        (raising :class:`ExchangeError`) is swallowed too, keeping the public
        :meth:`account_ref` contract ("never raises") self-enforcing.
        '''
        try:  # Tier 1: unified fetch_accounts() (implemented by OKX)
            accounts = self.client.fetch_accounts()
            if accounts and accounts[0].get('id'):
                return str(accounts[0]['id'])
        except (ccxt.BaseError, ExchangeError, AttributeError, KeyError, IndexError, TypeError):
            pass
        try:  # Tier 2: per-venue private endpoint (Bybit / Binance raise on Tier 1)
            client = self.client
            if self.exchange_id == 'bybit':
                result = client.privateGetV5UserQueryApi().get('result') or {}
                return str(result['userID']) if result.get('userID') is not None else None
            if self.exchange_id == 'binance':
                uid = client.privateGetAccount().get('uid')
                return str(uid) if uid is not None else None
            if self.exchange_id == 'okx':
                data = client.privateGetAccountConfig().get('data') or []
                return str(data[0]['uid']) if data and data[0].get('uid') is not None else None
        except (ccxt.BaseError, ExchangeError, AttributeError, KeyError, IndexError, TypeError):
            return None
        return None

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
