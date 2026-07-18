'''Per-account open-orders store for reconciliation.

Records every outstanding order this tool has placed (or is about to place) so the
reconciler can later fetch its real status and book only fills that actually
occurred. Written *write-ahead* — the record lands before ``create_order`` — so a
placement timeout never strands an order: it is resolved later by its deterministic
client-order-id. Persisted as a single ``open_orders.json`` object keyed by
client-order-id under the account book; rewritten atomically on each mutation
(small, single-user). This store never touches the network.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.exceptions import StateError
from ccbalancer.models import OpenOrder

__all__ = ['OrderStore', 'open_order_to_dict']


def open_order_to_dict(order: OpenOrder) -> dict[str, object]:
    '''Serialize an :class:`OpenOrder` to a plain dict with a fixed key order.'''
    return {
        'client_order_id': order.client_order_id,
        'order_id': order.order_id,
        'symbol': order.symbol,
        'side': order.side,
        'amount': order.amount,
        'limit_price': order.limit_price,
        'status': order.status.value,
        'filled_booked': order.filled_booked,
        'placed_at': order.placed_at,
    }


@dataclass(slots=True)
class OrderStore:
    '''Read/write access to ``open_orders.json`` (keyed by client-order-id).

    Attributes:
        path: Location of the ``open_orders.json`` file.
    '''

    path: Path

    def get(self, client_order_id: str) -> OpenOrder | None:
        '''Return the tracked order for ``client_order_id``, or ``None``.'''
        return self._load().get(client_order_id)

    def list(self, symbol: str | None = None) -> list[OpenOrder]:
        '''Return tracked orders in insertion order, optionally filtered by symbol.'''
        orders = list(self._load().values())
        if symbol is None:
            return orders
        return [order for order in orders if order.symbol == symbol]

    def put(self, order: OpenOrder) -> None:
        '''Insert or replace ``order`` by its client-order-id (atomic rewrite).'''
        records = self._load()
        records[order.client_order_id] = order
        self._save(records)

    def remove(self, client_order_id: str) -> None:
        '''Drop the tracked order for ``client_order_id`` (no-op if absent).'''
        records = self._load()
        if records.pop(client_order_id, None) is not None:
            self._save(records)

    def _load(self) -> dict[str, OpenOrder]:
        '''Read the store into an insertion-ordered client-order-id → OpenOrder map.

        Raises:
            StateError: If the file is unreadable or malformed.
        '''
        if not self.path.is_file():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            return {key: _from_dict(value) for key, value in raw.items()}
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StateError(f'Cannot read open-orders store {self.path}: {exc}') from exc

    def _save(self, records: dict[str, OpenOrder]) -> None:
        body = {key: open_order_to_dict(order) for key, order in records.items()}
        content = json.dumps(body, indent=2) + '\n'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(content, encoding='utf-8')
        tmp.replace(self.path)


def _from_dict(record: dict[str, object]) -> OpenOrder:
    return OpenOrder(
        client_order_id=str(record['client_order_id']),
        order_id=_opt_str(record.get('order_id')),
        symbol=str(record['symbol']),
        side=str(record['side']),
        amount=float(record['amount']),
        limit_price=float(record['limit_price']),
        status=OrderStatus(record['status']),
        filled_booked=float(record['filled_booked']),
        placed_at=str(record['placed_at']),
    )


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)
