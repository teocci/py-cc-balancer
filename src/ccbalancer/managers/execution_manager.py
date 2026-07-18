'''Order execution and the safety guardrails around it.

:class:`ExecutionManager` turns a list of :class:`RebalanceDecision` objects into
placed orders, following the cancel-and-replace flow from DESIGN.md: reconcile any
outstanding orders (book real fills), cancel our own stale ``CCB_PREFIX`` orders,
then place a tagged limit order per actionable decision. It owns no decision logic —
the decisions are computed upstream by the rebalance manager — and never imports ccxt.

Fills are **not** booked at submission (that was the F-6 bug: a resting maker order
recorded as a full fill at the limit price). Instead each placement is written
*write-ahead* to the :class:`~ccbalancer.stores.order_store.OrderStore` (keyed by its
deterministic client-order-id, so a ``create_order`` timeout is never lost), and real
fills are booked only by the :class:`~ccbalancer.managers.reconciliation_manager.ReconciliationManager`
— run at the start of each ``execute`` (before cancel-and-replace, so partials are
booked before the remainder is cancelled) and by the standalone ``reconcile`` command.

The module also exposes the three *pure* guard helpers the CLI enforces before any
order is placed: :func:`confirm_token` (the intent-level handshake issued by ``plan``
and required by ``rebalance``), :func:`session_notional` (checked against the
configured cap), and :func:`kill_switch_active`.
'''

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ccbalancer import constants as c
from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.exceptions import ExchangeError, InsufficientBalanceError, OrderRejectedError
from ccbalancer.models import (
    ExecutionResult,
    OpenOrder,
    ProposedOrder,
    RebalanceDecision,
)

if TYPE_CHECKING:
    from ccbalancer.managers.reconciliation_manager import ReconciliationManager
    from ccbalancer.stores.decision_store import DecisionStore
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.order_store import OrderStore
    from ccbalancer.stores.state_store import StateStore

__all__ = [
    'ExecutionManager',
    'confirm_token',
    'session_notional',
    'kill_switch_active',
    'is_ours',
]

_SUBMITTED = 'submitted'
_UNCONFIRMED = 'unconfirmed'
_SKIPPED = 'skipped'
_FAILED = 'failed'


def confirm_token(
    decisions: list[RebalanceDecision], *, exchange: str, testnet: bool
) -> str | None:
    '''Return the intent-level confirm-token for a plan, or ``None`` if it is a no-op.

    The token digests the *set and direction* of actionable trades (each pair's
    ``symbol:side``) plus the exchange context — not amounts or prices, which drift
    with the market between ``plan`` and ``rebalance``. It therefore stays stable
    across small market moves and only changes when the trades to place change,
    which is exactly when re-confirmation is warranted. Trade magnitude is bounded
    separately by the session notional cap.
    '''
    actions = sorted(
        f'{d.symbol}:{d.proposed_order.side.value}'
        for d in decisions
        if d.rebalance and d.proposed_order is not None
    )
    if not actions:
        return None
    canonical = f'{exchange}|{int(testnet)}|' + ','.join(actions)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[: c.CONFIRM_TOKEN_LENGTH]


def session_notional(decisions: list[RebalanceDecision]) -> float:
    '''Return the total notional that would be placed across all actionable pairs.'''
    return sum(
        d.proposed_order.notional
        for d in decisions
        if d.rebalance and d.proposed_order is not None
    )


def kill_switch_active(path: Path | None) -> bool:
    '''Return whether the kill-switch file exists (blocks order placement).'''
    return path is not None and path.exists()


def is_ours(order: dict[str, object]) -> bool:
    '''Return whether ``order`` was placed by this tool (``CCB_PREFIX`` tag).'''
    client_id = order.get('clientOrderId')
    return isinstance(client_id, str) and client_id.startswith(c.CCB_PREFIX)


@dataclass(slots=True)
class ExecutionManager:
    '''Place and cancel orders; reconcile books the fills.

    Attributes:
        exchange: Exchange store used to load markets, cancel, and place orders.
        state_store: Persists ``state.json`` and ``history.jsonl`` (via reconcile).
        order_store: Tracks outstanding orders write-ahead for reconciliation.
        decision_store: Appends the ``rebalance`` decision-log records.
        reconciler: Books real fills from exchange status (run before placement).
        exchange_id: ccxt exchange id, stamped onto records.
        testnet: Whether the sandbox is in effect, stamped onto records.
    '''

    exchange: ExchangeStore
    state_store: StateStore
    order_store: OrderStore
    decision_store: DecisionStore
    reconciler: ReconciliationManager
    exchange_id: str
    testnet: bool

    def execute(self, decisions: list[RebalanceDecision], *, now: str) -> list[ExecutionResult]:
        '''Reconcile, cancel stale orders, then place one order per actionable decision.

        Reconciliation runs first so a partial fill on an outstanding order is booked
        before that order is cancelled and re-placed. Each placement is recorded
        write-ahead; the fill itself is booked by reconciliation, never on submission.
        Re-running is idempotent: leftover orders are reconciled then cancelled before
        re-placing.
        '''
        self.exchange.load_markets()
        self.reconciler.reconcile(now=now)
        actionable = [d for d in decisions if d.rebalance and d.proposed_order is not None]
        self.cancel_orders(self.owned_open_orders([d.symbol for d in actionable]))
        return [self._act(decision, now=now, index=index) for index, decision in enumerate(decisions)]

    def owned_open_orders(self, symbols: list[str] | None = None) -> list[dict[str, object]]:
        '''Return this tool's open orders, restricted to ``symbols`` if given.'''
        if symbols is None:
            candidates = self.exchange.fetch_open_orders(None)
        else:
            candidates = [
                order for symbol in dict.fromkeys(symbols)
                for order in self.exchange.fetch_open_orders(symbol)
            ]
        return [order for order in candidates if is_ours(order)]

    def cancel_orders(self, orders: list[dict[str, object]]) -> list[dict[str, object]]:
        '''Cancel each given order; return the orders cancelled.'''
        for order in orders:
            self.exchange.cancel_order(str(order.get('id')), order.get('symbol'))
        return orders

    def _act(self, decision: RebalanceDecision, *, now: str, index: int) -> ExecutionResult:
        self.decision_store.append_decision(
            decision, ts=now, exchange=self.exchange_id, testnet=self.testnet, command='rebalance'
        )
        order = decision.proposed_order
        if not decision.rebalance or order is None:
            return ExecutionResult(
                decision.symbol, False, None, _SKIPPED, decision.reason.value, decision.detail
            )
        return self._place(decision, order, now=now, index=index)

    def _place(
        self, decision: RebalanceDecision, order: ProposedOrder, *, now: str, index: int
    ) -> ExecutionResult:
        '''Place one order write-ahead; the fill is booked later by reconciliation.'''
        coid = self._client_order_id(now, index)
        self.order_store.put(self._pending(coid, order, OrderStatus.UNCONFIRMED, None, now))
        try:
            response = self.exchange.create_order(
                order.symbol, order.side, order.amount, order.limit_price, coid
            )
        except (OrderRejectedError, InsufficientBalanceError) as exc:
            self.order_store.remove(coid)  # never reached the book — stop tracking it
            return self._result(decision, order, None, _FAILED, str(exc))
        except ExchangeError as exc:
            # Outcome unknown (network/timeout): leave the write-ahead record so
            # reconcile can resolve it by client-order-id on a later pass.
            return self._result(decision, order, None, _UNCONFIRMED, f'{exc}; run `reconcile`')
        order_id = _opt_str(response.get('id'))
        self.order_store.put(self._pending(coid, order, OrderStatus.OPEN, order_id, now))
        # Capture an order that filled on placement (marketable); a resting order books nothing.
        self.reconciler.reconcile([order.symbol], now=now)
        return self._result(decision, order, order_id, _SUBMITTED, decision.detail)

    @staticmethod
    def _pending(
        coid: str, order: ProposedOrder, status: OrderStatus, order_id: str | None, now: str
    ) -> OpenOrder:
        return OpenOrder(
            client_order_id=coid,
            order_id=order_id,
            symbol=order.symbol,
            side=order.side.value,
            amount=order.amount,
            limit_price=order.limit_price,
            status=status,
            filled_booked=0.0,
            placed_at=now,
        )

    def _client_order_id(self, now: str, index: int) -> str:
        stamp = ''.join(ch for ch in now if ch.isalnum())
        return f'{c.CCB_PREFIX}{stamp}-{index}'

    def _result(
        self,
        decision: RebalanceDecision,
        order: ProposedOrder,
        order_id: str | None,
        status: str,
        detail: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            symbol=decision.symbol,
            placed=status == _SUBMITTED,
            order_id=order_id,
            status=status,
            reason=decision.reason.value,
            detail=detail,
            side=order.side.value,
            amount=order.amount,
            price=order.limit_price,
            notional=order.notional,
        )


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)
