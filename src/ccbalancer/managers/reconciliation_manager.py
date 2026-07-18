'''Order-status reconciliation — book only fills that actually occurred.

Live placement records an order as *pending* in the :class:`OrderStore` without
booking any fill (see :class:`~ccbalancer.managers.execution_manager.ExecutionManager`).
This manager closes the loop: for each tracked order it reads the real exchange
status, books the *delta* since the last reconciled fill (so partial fills are not
double-booked), advances or drops the store record, and updates state/history. It is
the fix for F-6 (fills fabricated on submission).

An unconfirmed placement (e.g. a ``create_order`` timeout) is resolved by its
deterministic client-order-id before its status is read; if it cannot be resolved
yet, it is left tracked for a later pass. Reconciliation places no orders and is
safe to re-run: with no new fills every delta is zero and nothing is written.
'''

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.models import Fill, HistoryEvent, OpenOrder, RebalanceState, ReconcileResult

if TYPE_CHECKING:
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.ledger_store import LedgerStore
    from ccbalancer.stores.order_store import OrderStore
    from ccbalancer.stores.state_store import StateStore

__all__ = ['ReconciliationManager']

# Smallest fill delta worth booking (guards float noise around zero).
_EPS = 1e-12
# Reason stamped on reconciled fills (the decision reason is not available here).
_RECONCILED = 'reconciled'
_TERMINAL = frozenset({OrderStatus.CLOSED, OrderStatus.CANCELED})


@dataclass(slots=True)
class ReconciliationManager:
    '''Reconcile tracked orders against exchange status, booking real fills.

    Attributes:
        exchange: Exchange store read for order status (never places orders here).
        order_store: The pending open-orders store to advance/drop.
        ledger_store: Appends the booked fills.
        state_store: Persists state + history for each booked fill.
        exchange_id: ccxt exchange id, stamped onto records.
        testnet: Whether the sandbox is in effect, stamped onto records.
    '''

    exchange: ExchangeStore
    order_store: OrderStore
    ledger_store: LedgerStore
    state_store: StateStore
    exchange_id: str
    testnet: bool

    def reconcile(self, symbols: list[str] | None = None, *, now: str) -> list[ReconcileResult]:
        '''Reconcile every tracked order (optionally restricted to ``symbols``).'''
        orders = self.order_store.list()
        if symbols is not None:
            wanted = set(symbols)
            orders = [order for order in orders if order.symbol in wanted]
        return [self._reconcile_one(order, now=now) for order in orders]

    def _reconcile_one(self, order: OpenOrder, *, now: str) -> ReconcileResult:
        resolved = self._resolve(order)
        if resolved is None:  # unconfirmed and not yet findable — keep for a later pass
            return _result(order, order.status.value, newly=0.0, total=order.filled_booked)
        order, fetched = resolved
        return self._book(order, fetched, now=now)

    def _resolve(self, order: OpenOrder) -> tuple[OpenOrder, dict[str, object]] | None:
        '''Return ``(order_with_id, status)`` or ``None`` if the id is unresolvable.'''
        if order.order_id is not None:
            return order, self.exchange.fetch_order(order.order_id, order.symbol)
        found = self.exchange.find_order_by_client_id(order.client_order_id, order.symbol)
        if found is None or found.get('id') is None:
            return None
        order = replace(order, order_id=str(found['id']))
        return order, self.exchange.fetch_order(order.order_id, order.symbol)

    def _book(self, order: OpenOrder, fetched: dict[str, object], *, now: str) -> ReconcileResult:
        filled = _num(fetched.get('filled'))
        average = _num(fetched.get('average'), order.limit_price) or order.limit_price
        status = _map_status(fetched.get('status'), filled)
        delta = filled - order.filled_booked
        if delta > _EPS:
            self._write_fill(order, delta, average, fetched, status, now)
        if status in _TERMINAL:
            self.order_store.remove(order.client_order_id)
        else:
            self.order_store.put(replace(order, status=status, filled_booked=filled))
        return _result(order, status.value, newly=max(delta, 0.0), total=filled)

    def _write_fill(
        self, order: OpenOrder, delta: float, average: float,
        fetched: dict[str, object], status: OrderStatus, now: str,
    ) -> None:
        '''Append the delta fill and record state/history for it.

        Fee is best-effort: the venue's cumulative order fee is booked once, on the
        terminal fill, so partials do not double-count it (documented limitation).
        '''
        fee, fee_ccy = _fee(fetched) if status in _TERMINAL else (0.0, None)
        self.ledger_store.append_fill(Fill(
            ts=now, symbol=order.symbol, side=order.side, price=average, qty=delta,
            fee=fee, fee_currency=fee_ccy, order_id=order.order_id,
        ))
        self.state_store.record(
            RebalanceState(order.symbol, now, order.side, delta, average, 0.0, _RECONCILED),
            HistoryEvent(now, order.symbol, order.side, delta, average, delta * average,
                         0.0, _RECONCILED, self.exchange_id, self.testnet, order.order_id,
                         status.value),
        )


def _result(order: OpenOrder, status: str, *, newly: float, total: float) -> ReconcileResult:
    return ReconcileResult(
        symbol=order.symbol,
        client_order_id=order.client_order_id,
        order_id=order.order_id,
        status=status,
        newly_filled=newly,
        total_filled=total,
        remaining=max(order.amount - total, 0.0),
    )


def _map_status(ccxt_status: object, filled: float) -> OrderStatus:
    '''Map a ccxt order status (+ filled qty) to the store lifecycle status.'''
    status = str(ccxt_status or '').lower()
    if status == 'closed':
        return OrderStatus.CLOSED
    if status in ('canceled', 'cancelled', 'expired', 'rejected'):
        return OrderStatus.CANCELED
    return OrderStatus.PARTIAL if filled > _EPS else OrderStatus.OPEN


def _fee(fetched: dict[str, object]) -> tuple[float, str | None]:
    fee = fetched.get('fee') if isinstance(fetched.get('fee'), dict) else {}
    return _num(fee.get('cost')), (str(fee['currency']) if fee.get('currency') else None)


def _num(value: object, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
