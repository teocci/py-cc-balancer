'''Simulated-exchange backend for a paper account.

:class:`PaperExchangeStore` mirrors the public surface of
:class:`~ccbalancer.stores.exchange.ExchangeStore` so every live command runs
against a paper account unchanged, but no order ever reaches a real venue and no
real balance is touched. It composes two collaborators:

- a **real, public** :class:`ExchangeStore` (``market_data``) for prices, markets,
  and OHLCV — public endpoints need no key, so a paper account still rebalances
  against the live market; and
- a persistent :class:`~ccbalancer.stores.paper_book.PaperBookStore` holding the
  simulated balances and orders.

Fills are **reconcile-driven**: :meth:`create_order` rests a maker limit, and
:meth:`fetch_order` reports it filled once the live ticker crosses the limit —
booking the balance change exactly once. That is the same contract the real venue
gives the :class:`~ccbalancer.managers.reconciliation_manager.ReconciliationManager`,
so the paper account exercises the real write-ahead + reconcile plumbing without a
single manager change. Only this store touches the network (via ``market_data``).
'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer import constants as c
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import ExchangeError, InsufficientBalanceError
from ccbalancer.stores.paper_book import ORDER_CANCELED, ORDER_CLOSED, ORDER_OPEN, PaperBook, PaperOrder
from ccbalancer.utils.money import notional as quote_notional

if TYPE_CHECKING:
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.exchange_quirks import ExchangeQuirks
    from ccbalancer.stores.paper_book import PaperBookStore

__all__ = ['PaperExchangeStore']

_LIMIT_ORDER_TYPE = 'limit'
_BALANCE_EPS = 1e-9


@dataclass(slots=True)
class PaperExchangeStore:
    '''A drop-in exchange store backed by a simulated book and live public prices.

    Attributes:
        book_store: Persistent simulated balances + orders for this account.
        market_data: Real public exchange store supplying prices/markets/OHLCV.
        fee_rate: Maker fee applied to each simulated fill's notional.
    '''

    book_store: PaperBookStore
    market_data: ExchangeStore
    fee_rate: float = c.DEFAULT_PAPER_FEE_RATE

    # --- market data (delegated to the real public client) --------------------

    @property
    def exchange_id(self) -> str:
        '''The underlying public venue id supplying market data.'''
        return self.market_data.exchange_id

    @property
    def quirks(self) -> ExchangeQuirks:
        '''Execution quirks of the underlying venue (surface parity; unused here).'''
        return self.market_data.quirks

    def load_markets(self, reload: bool = False) -> dict[str, object]:
        '''Load markets from the real public venue.'''
        return self.market_data.load_markets(reload)

    def fetch_ticker(self, symbol: str) -> dict[str, object]:
        '''Return the live public ticker for ``symbol``.'''
        return self.market_data.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        '''Return live public candles for ``symbol``.'''
        return self.market_data.fetch_ohlcv(symbol, timeframe, limit)

    def fetch_ohlcv_range(
        self, symbol: str, timeframe: str, since_ms: int, until_ms: int
    ) -> list[list[float]]:
        '''Return live public candles for ``symbol`` in ``[since_ms, until_ms)``.'''
        return self.market_data.fetch_ohlcv_range(symbol, timeframe, since_ms, until_ms)

    def check_credentials(self) -> None:
        '''No-op: a paper account has no credentials to verify.'''

    def account_ref(self) -> str | None:
        '''No exchange account backs a paper book, so there is no ref to capture.'''
        return None

    # --- simulated account (backed by the persistent book) --------------------

    def fetch_balance(self) -> dict[str, object]:
        '''Return the simulated balance, with open orders reserving ``used`` funds.'''
        book = self.book_store.load()
        locked = book.locked()
        assets = set(book.balances) | set(locked)
        total = {asset: book.balances.get(asset, 0.0) for asset in assets}
        used = {asset: locked.get(asset, 0.0) for asset in assets}
        free = {asset: total[asset] - used[asset] for asset in assets}
        return {'free': free, 'used': used, 'total': total}

    def fetch_open_orders(self, symbol: str | None = None) -> list[dict[str, object]]:
        '''Return the resting simulated orders, optionally filtered by ``symbol``.'''
        book = self.book_store.load()
        return [
            _to_ccxt(order) for order in book.open_orders()
            if symbol is None or order.symbol == symbol
        ]

    def find_order_by_client_id(
        self, client_order_id: str, symbol: str | None = None
    ) -> dict[str, object] | None:
        '''Return the resting order matching ``client_order_id``, or ``None``.'''
        for order in self.fetch_open_orders(symbol):
            if order.get('clientOrderId') == client_order_id:
                return order
        return None

    def fetch_order(self, order_id: str, symbol: str | None = None) -> dict[str, object]:
        '''Return ``order_id``'s status, filling it if the live ticker now crosses it.

        A resting order fills at its limit price once the market reaches it; the
        balance change is applied exactly once (the order then reads ``closed`` on
        every later call), so the reconciler books the fill without double-counting.

        Raises:
            ExchangeError: If ``order_id`` is unknown.
        '''
        book = self.book_store.load()
        order = book.find(order_id)
        if order is None:
            raise ExchangeError(f'No paper order {order_id}')
        if order.status == ORDER_OPEN and self._crosses(order):
            self._fill(book, order)
            self.book_store.save(book)
        return _to_ccxt(order)

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: float,
        price: float,
        client_order_id: str | None = None,
    ) -> dict[str, object]:
        '''Rest a simulated maker limit order and return its ccxt-shaped record.

        Raises:
            InsufficientBalanceError: If free balance cannot cover the order.
        '''
        book = self.book_store.load()
        self._check_funds(book, symbol, side, amount, price)
        order = PaperOrder(
            id=f'paper-{book.next_id}', client_order_id=client_order_id, symbol=symbol,
            side=side.value, amount=amount, price=price,
        )
        book.next_id += 1
        book.orders.append(order)
        self.book_store.save(book)
        return _to_ccxt(order)

    def cancel_order(self, order_id: str, symbol: str | None = None) -> dict[str, object]:
        '''Cancel a resting simulated order (idempotent), freeing its reserved funds.'''
        book = self.book_store.load()
        order = book.find(order_id)
        if order is not None and order.status == ORDER_OPEN:
            order.status = ORDER_CANCELED
            self.book_store.save(book)
        return {'id': order_id, 'symbol': symbol, 'status': ORDER_CANCELED}

    # --- fill mechanics -------------------------------------------------------

    def _market_price(self, symbol: str) -> float:
        '''Return a single live reference price for ``symbol`` (last, else mid).'''
        ticker = self.market_data.fetch_ticker(symbol)
        for key in ('last', 'close'):
            value = ticker.get(key)
            if value:
                return float(value)
        bid, ask = ticker.get('bid'), ticker.get('ask')
        if bid and ask:
            return (float(bid) + float(ask)) / 2
        raise ExchangeError(f'No usable price in ticker for {symbol}')

    def _crosses(self, order: PaperOrder) -> bool:
        '''Whether the live price has reached the resting limit (BUY↓, SELL↑).'''
        price = self._market_price(order.symbol)
        if order.side == OrderSide.BUY.value:
            return price <= order.price
        return price >= order.price

    def _fill(self, book: PaperBook, order: PaperOrder) -> None:
        '''Apply a fill at the limit price to the book and mark the order closed.'''
        base, quote = order.symbol.split('/', 1)
        value = quote_notional(order.amount, order.price)
        fee = value * self.fee_rate
        if order.side == OrderSide.BUY.value:
            book.balances[base] = book.balances.get(base, 0.0) + order.amount
            book.balances[quote] = book.balances.get(quote, 0.0) - value - fee
        else:
            book.balances[base] = book.balances.get(base, 0.0) - order.amount
            book.balances[quote] = book.balances.get(quote, 0.0) + value - fee
        order.status = ORDER_CLOSED
        order.filled = order.amount
        order.average = order.price
        order.fee_cost = fee
        order.fee_currency = quote

    def _check_funds(
        self, book: PaperBook, symbol: str, side: OrderSide, amount: float, price: float
    ) -> None:
        '''Raise if free balance (total minus what open orders reserve) is short.'''
        base, quote = symbol.split('/', 1)
        locked = book.locked()
        if side is OrderSide.BUY:
            need = quote_notional(amount, price)
            free = book.balances.get(quote, 0.0) - locked.get(quote, 0.0)
            if free + _BALANCE_EPS < need:
                raise InsufficientBalanceError(
                    f'paper: need {need:.2f} {quote}, have {free:.2f} free'
                )
            return
        free = book.balances.get(base, 0.0) - locked.get(base, 0.0)
        if free + _BALANCE_EPS < amount:
            raise InsufficientBalanceError(f'paper: need {amount} {base}, have {free} free')


def _to_ccxt(order: PaperOrder) -> dict[str, object]:
    '''Render a :class:`PaperOrder` as the ccxt order dict the managers expect.'''
    return {
        'id': order.id,
        'clientOrderId': order.client_order_id,
        'symbol': order.symbol,
        'type': _LIMIT_ORDER_TYPE,
        'side': order.side,
        'amount': order.amount,
        'price': order.price,
        'status': order.status,
        'filled': order.filled,
        'average': order.average,
        'fee': {'cost': order.fee_cost, 'currency': order.fee_currency},
    }
