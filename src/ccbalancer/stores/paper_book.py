'''Persistent per-account book for a paper (simulated-exchange) account.

Holds one paper account's simulated balances, its resting/closed orders, and a
monotonic order-id counter, persisted as ``paper_book.json`` under the account's
data directory. Rewritten atomically on each mutation (small, single-user) and
never touches the network — the real market data a paper account reads comes from
the wrapping :class:`~ccbalancer.stores.paper_exchange.PaperExchangeStore`, not here.
'''

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ccbalancer.exceptions import StateError
from ccbalancer.utils.money import notional as quote_notional

__all__ = ['PaperOrder', 'PaperBook', 'PaperBookStore', 'ORDER_OPEN', 'ORDER_CLOSED', 'ORDER_CANCELED']

_SCHEMA_VERSION = 1
ORDER_OPEN = 'open'
ORDER_CLOSED = 'closed'
ORDER_CANCELED = 'canceled'


@dataclass(slots=True)
class PaperOrder:
    '''One simulated order in the paper book.

    Attributes:
        id: Synthetic exchange order id (``paper-<n>``).
        client_order_id: The tool's deterministic client-order-id, or ``None``.
        symbol: ``BASE/QUOTE`` pair.
        side: ``'buy'`` or ``'sell'``.
        amount: Base-asset quantity.
        price: Limit price in quote terms.
        status: ``open`` (resting), ``closed`` (filled), or ``canceled``.
        filled: Base quantity filled (``amount`` once closed, else ``0``).
        average: Average fill price (the limit price on a paper fill), or ``None``.
        fee_cost: Quote-terms fee booked on the fill.
        fee_currency: Fee asset (the quote), or ``None`` until filled.
    '''

    id: str
    client_order_id: str | None
    symbol: str
    side: str
    amount: float
    price: float
    status: str = ORDER_OPEN
    filled: float = 0.0
    average: float | None = None
    fee_cost: float = 0.0
    fee_currency: str | None = None


@dataclass(slots=True)
class PaperBook:
    '''In-memory state of a paper account: balances, orders, and an id counter.

    Attributes:
        balances: Total holdings per asset (quote + base). Free == total minus
            what open orders reserve (see :meth:`locked`).
        orders: Every order placed, resting or terminal, in insertion order.
        next_id: Next synthetic order-id sequence number.
    '''

    balances: dict[str, float] = field(default_factory=dict)
    orders: list[PaperOrder] = field(default_factory=list)
    next_id: int = 1

    def open_orders(self) -> list[PaperOrder]:
        '''Return the resting (``open``) orders.'''
        return [order for order in self.orders if order.status == ORDER_OPEN]

    def find(self, order_id: str) -> PaperOrder | None:
        '''Return the order with ``id == order_id``, or ``None``.'''
        return next((order for order in self.orders if order.id == order_id), None)

    def locked(self) -> dict[str, float]:
        '''Return the asset amounts reserved by open orders (BUY→quote, SELL→base).'''
        used: dict[str, float] = {}
        for order in self.open_orders():
            base, quote = order.symbol.split('/', 1)
            if order.side == 'buy':
                used[quote] = used.get(quote, 0.0) + quote_notional(order.amount, order.price)
            else:
                used[base] = used.get(base, 0.0) + order.amount
        return used


@dataclass(slots=True)
class PaperBookStore:
    '''Read/write access to a paper account's ``paper_book.json`` (atomic rewrite).

    Attributes:
        path: Location of the ``paper_book.json`` file.
    '''

    path: Path

    def exists(self) -> bool:
        '''Whether a book file has been seeded for this account.'''
        return self.path.is_file()

    def seed(self, quote: str, capital: float) -> PaperBook:
        '''Create (or overwrite) the book with an all-stable starting balance.'''
        book = PaperBook(balances={quote: float(capital)})
        self.save(book)
        return book

    def load(self) -> PaperBook:
        '''Read the book from disk (an empty book if unseeded).

        Raises:
            StateError: If the file exists but is unreadable or malformed.
        '''
        if not self.path.is_file():
            return PaperBook()
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            return _book_from_dict(raw)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StateError(f'Cannot read paper book {self.path}: {exc}') from exc

    def save(self, book: PaperBook) -> None:
        '''Persist ``book`` atomically.'''
        content = json.dumps(_book_to_dict(book), indent=2) + '\n'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(content, encoding='utf-8')
        tmp.replace(self.path)


def _book_to_dict(book: PaperBook) -> dict[str, object]:
    return {
        'schema_version': _SCHEMA_VERSION,
        'balances': book.balances,
        'next_id': book.next_id,
        'orders': [_order_to_dict(order) for order in book.orders],
    }


def _order_to_dict(order: PaperOrder) -> dict[str, object]:
    return {
        'id': order.id,
        'client_order_id': order.client_order_id,
        'symbol': order.symbol,
        'side': order.side,
        'amount': order.amount,
        'price': order.price,
        'status': order.status,
        'filled': order.filled,
        'average': order.average,
        'fee_cost': order.fee_cost,
        'fee_currency': order.fee_currency,
    }


def _book_from_dict(raw: dict[str, object]) -> PaperBook:
    balances = {str(asset): float(amount) for asset, amount in (raw.get('balances') or {}).items()}
    orders = [_order_from_dict(record) for record in (raw.get('orders') or [])]
    return PaperBook(balances=balances, orders=orders, next_id=int(raw.get('next_id', 1)))


def _order_from_dict(record: dict[str, object]) -> PaperOrder:
    average = record.get('average')
    return PaperOrder(
        id=str(record['id']),
        client_order_id=_opt_str(record.get('client_order_id')),
        symbol=str(record['symbol']),
        side=str(record['side']),
        amount=float(record['amount']),
        price=float(record['price']),
        status=str(record.get('status', ORDER_OPEN)),
        filled=float(record.get('filled', 0.0)),
        average=None if average is None else float(average),
        fee_cost=float(record.get('fee_cost', 0.0)),
        fee_currency=_opt_str(record.get('fee_currency')),
    )


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)
