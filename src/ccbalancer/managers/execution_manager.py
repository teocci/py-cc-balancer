'''Order execution and the safety guardrails around it.

:class:`ExecutionManager` turns a list of :class:`RebalanceDecision` objects into
placed orders, following the cancel-and-replace flow from DESIGN.md: cancel our own
stale ``CCB_PREFIX`` orders, place a tagged limit order per actionable decision, and
persist the outcome to ``state.json`` + ``history.jsonl`` + ``ledger.jsonl`` (plus a
``rebalance`` decision-log record). It owns no decision logic — the decisions are
computed upstream by the rebalance manager — and never imports ccxt.

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
from ccbalancer.exceptions import InsufficientBalanceError, OrderRejectedError
from ccbalancer.models import (
    ExecutionResult,
    Fill,
    HistoryEvent,
    ProposedOrder,
    RebalanceDecision,
    RebalanceState,
)

if TYPE_CHECKING:
    from ccbalancer.stores.decision_store import DecisionStore
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.ledger_store import LedgerStore
    from ccbalancer.stores.state_store import StateStore

__all__ = [
    'ExecutionManager',
    'confirm_token',
    'session_notional',
    'kill_switch_active',
    'is_ours',
]

_SUBMITTED = 'submitted'
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
    '''Place and cancel orders, persisting state, history, and fills.

    Attributes:
        exchange: Exchange store used to load markets, cancel, and place orders.
        state_store: Persists ``state.json`` and ``history.jsonl``.
        ledger_store: Appends executed fills to ``ledger.jsonl``.
        decision_store: Appends the ``rebalance`` decision-log records.
        exchange_id: ccxt exchange id, stamped onto records.
        testnet: Whether the sandbox is in effect, stamped onto records.
    '''

    exchange: ExchangeStore
    state_store: StateStore
    ledger_store: LedgerStore
    decision_store: DecisionStore
    exchange_id: str
    testnet: bool

    def execute(self, decisions: list[RebalanceDecision], *, now: str) -> list[ExecutionResult]:
        '''Cancel stale orders, then place one order per actionable decision.

        Persists a decision-log record for every decision and, for each placed
        order, the resulting state, history event, and ledger fill. Re-running is
        idempotent: our own leftover orders are cancelled before re-placing.
        '''
        self.exchange.load_markets()
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
        coid = self._client_order_id(now, index)
        try:
            response = self.exchange.create_order(
                order.symbol, order.side, order.amount, order.limit_price, coid
            )
        except (OrderRejectedError, InsufficientBalanceError) as exc:
            return self._result(decision, order, None, _FAILED, str(exc))
        order_id = _opt_str(response.get('id'))
        self._persist(decision, order, response, order_id, now)
        return self._result(decision, order, order_id, _SUBMITTED, decision.detail)

    def _persist(
        self,
        decision: RebalanceDecision,
        order: ProposedOrder,
        response: dict[str, object],
        order_id: str | None,
        now: str,
    ) -> None:
        self.ledger_store.append_fill(_fill(order, response, order_id, now))
        self.state_store.record(
            _state(decision, order, now), _event(decision, order, order_id, now, self.exchange_id, self.testnet)
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


def _fill(order: ProposedOrder, response: dict[str, object], order_id: str | None, now: str) -> Fill:
    fee = response.get('fee') if isinstance(response.get('fee'), dict) else {}
    return Fill(
        ts=now,
        symbol=order.symbol,
        side=order.side.value,
        price=_num(response.get('average'), order.limit_price) or order.limit_price,
        qty=_num(response.get('filled'), order.amount) or order.amount,
        fee=_num(fee.get('cost')),
        fee_currency=_opt_str(fee.get('currency')),
        order_id=order_id,
    )


def _state(decision: RebalanceDecision, order: ProposedOrder, now: str) -> RebalanceState:
    return RebalanceState(
        symbol=order.symbol,
        last_rebalance_at=now,
        last_side=order.side.value,
        last_amount=order.amount,
        last_price=order.limit_price,
        last_drift_pct=decision.drift_pct,
        last_reason=decision.reason.value,
    )


def _event(
    decision: RebalanceDecision,
    order: ProposedOrder,
    order_id: str | None,
    now: str,
    exchange_id: str,
    testnet: bool,
) -> HistoryEvent:
    return HistoryEvent(
        ts=now,
        symbol=order.symbol,
        side=order.side.value,
        amount=order.amount,
        price=order.limit_price,
        notional=order.notional,
        drift_pct=decision.drift_pct,
        reason=decision.reason.value,
        exchange=exchange_id,
        testnet=testnet,
        order_id=order_id,
        status=_SUBMITTED,
    )


def _num(value: object, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)
