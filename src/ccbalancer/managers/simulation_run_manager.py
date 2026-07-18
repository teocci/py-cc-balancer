'''Deterministic backtest replay engine and the `simulation run` orchestrator.

The engine iterates a candle series, decides on each *closed* candle via the pure
:meth:`RebalanceManager.decide` (reused unchanged), and resolves the resulting
limit order against the **next** bar with a bar-crosses-limit fill model — a BUY
fills when a later low reaches the limit, a SELL when a later high does; otherwise
the order rests and is re-quoted at the next decision (mirroring live
cancel-and-replace). Fills mutate a virtual balance seeded all-stable from the
starting capital and are written to an isolated per-run ledger.

Two properties are load-bearing: **no look-ahead** (an order never resolves on its
own decision bar) and **determinism** (identical inputs → byte-identical ledger).
Network and clock never enter here; candles come from the offline simulation store.
'''

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer import constants as c
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import OrderRejectedError, StateError
from ccbalancer.models import Fill, PairConfig, ProposedOrder, SimRunResult
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.utils.candles import CANDLE_TIME
from ccbalancer.utils.money import notional as quote_notional
from ccbalancer.utils.timeutil import ms_to_iso

if TYPE_CHECKING:
    from ccbalancer.managers.rebalance_manager import RebalanceManager
    from ccbalancer.stores.simulation_store import SimulationStore

__all__ = ['ReplayParams', 'ReplayOutcome', 'SimulationRunManager', 'replay', 'validate_order']

# ccxt candle field indices ([t, o, h, l, c, v]).
_HIGH = 2
_LOW = 3
_CLOSE = 4


@dataclass(frozen=True, slots=True)
class ReplayParams:
    '''Inputs that shape a replay independent of the candle series.

    Attributes:
        capital: Starting capital in quote terms (seeded entirely as stable).
        fee_rate: Maker fee applied to each fill's notional (e.g. ``0.001``).
        amount_precision: Decimal places the order amount is floored to.
        min_cost: Exchange min-notional floor; an order below it is rejected
            (``0`` disables the floor).
    '''

    capital: float
    fee_rate: float
    amount_precision: int
    min_cost: float


@dataclass(frozen=True, slots=True)
class ReplayOutcome:
    '''The result of a pure replay over a candle series.

    Attributes:
        fills: Fills produced, in chronological order.
        final_base: Base asset held after the last candle.
        final_stable: Quote asset held after the last candle.
        orders_placed: Actionable orders that entered the resting book.
        rejects: Orders rejected below ``min_cost``.
    '''

    fills: list[Fill]
    final_base: float
    final_stable: float
    orders_placed: int
    rejects: int


@dataclass(slots=True)
class _Balance:
    '''Mutable virtual balance. Free == total: each bar cancels-and-replaces, so
    no funds are ever locked in a resting order at a decision point.'''

    base: float
    stable: float


def validate_order(order: ProposedOrder, min_cost: float) -> ProposedOrder:
    '''Return ``order`` unchanged, or raise if it violates the exchange floor.

    Mirrors a live venue rejecting a sub-minimum order, so the "never converges"
    failure (perpetually sub-minimum legs) stays visible rather than silently
    filling.

    Raises:
        OrderRejectedError: If the order notional is below ``min_cost``.
    '''
    if min_cost > 0 and order.notional < min_cost:
        raise OrderRejectedError(
            f'{order.symbol}: notional {order.notional:.2f} below min-cost {min_cost}'
        )
    return order


def replay(
    candles: list[list[float]],
    pair: PairConfig,
    rebalancer: RebalanceManager,
    params: ReplayParams,
) -> ReplayOutcome:
    '''Replay ``candles`` for ``pair`` and return the fills and final balance.'''
    balance = _Balance(base=0.0, stable=params.capital)
    resting: ProposedOrder | None = None
    last_rebalance_at: str | None = None
    fills: list[Fill] = []
    orders_placed = 0
    rejects = 0
    for candle in candles:
        # 1. Resolve the order decided on the *previous* bar against this one
        #    (next-bar resolution — never the decision bar → no look-ahead).
        if resting is not None:
            if _crosses(resting, candle):
                fills.append(_apply_fill(balance, resting, candle, params, pair, len(fills)))
                last_rebalance_at = fills[-1].ts
            resting = None  # filled, or cancelled for re-quote
        # 2. Decide on this closed candle, then place/validate the new order.
        decision = rebalancer.decide(
            pair, _snapshot(pair, balance, candle, params, last_rebalance_at),
            now=ms_to_iso(int(candle[CANDLE_TIME])),
        )
        order = decision.proposed_order if decision.rebalance else None
        if order is None:
            continue
        orders_placed += 1
        try:
            resting = validate_order(order, params.min_cost)
        except OrderRejectedError:
            rejects += 1
            resting = None
    return ReplayOutcome(fills, balance.base, balance.stable, orders_placed, rejects)


def _snapshot(pair, balance, candle, params, last_rebalance_at):
    '''Build a point-in-time snapshot from a closed candle (no order book: the
    close stands in for price/bid/ask).'''
    from ccbalancer.models import PairSnapshot

    close = float(candle[_CLOSE])
    return PairSnapshot(
        symbol=pair.symbol,
        base_total=balance.base,
        base_free=balance.base,
        stable_total=balance.stable,
        stable_free=balance.stable,
        price=close,
        bid=close,
        ask=close,
        amount_precision=params.amount_precision,
        market_active=True,
        last_rebalance_at=last_rebalance_at,
    )


def _crosses(order: ProposedOrder, candle: list[float]) -> bool:
    '''Whether ``candle`` crosses the resting limit (BUY: low<=limit; SELL: high>=limit).'''
    if order.side is OrderSide.BUY:
        return float(candle[_LOW]) <= order.limit_price
    return float(candle[_HIGH]) >= order.limit_price


def _apply_fill(
    balance: _Balance,
    order: ProposedOrder,
    candle: list[float],
    params: ReplayParams,
    pair: PairConfig,
    seq: int,
) -> Fill:
    '''Mutate ``balance`` for a fill at the limit price and return the Fill record.'''
    fee = order.notional * params.fee_rate
    if order.side is OrderSide.BUY:
        balance.base += order.amount
        balance.stable -= order.notional + fee
    else:
        balance.base -= order.amount
        balance.stable += order.notional - fee
    return Fill(
        ts=ms_to_iso(int(candle[CANDLE_TIME])),
        symbol=order.symbol,
        side=order.side.value,
        price=order.limit_price,
        qty=order.amount,
        fee=fee,
        fee_currency=pair.quote,
        order_id=f'sim-{seq}',
    )


@dataclass(slots=True)
class SimulationRunManager:
    '''Read candles, replay, and persist the isolated run artifacts.

    Attributes:
        store: Simulation store supplying the candle series and run directory root.
        rebalancer: Pure decision engine reused per closed candle.
    '''

    store: SimulationStore
    rebalancer: RebalanceManager

    def run(
        self,
        exchange_id: str,
        symbol: str,
        timeframe: str,
        start_ms: int,
        end_ms: int,
        pair: PairConfig,
        params: ReplayParams,
    ) -> SimRunResult:
        '''Replay the stored candles in ``[start_ms, end_ms)`` and write the run.

        Raises:
            StateError: If no candles are stored for the range (fetch them first).
        '''
        candles = [
            candle for candle in self.store.read(exchange_id, symbol, timeframe)
            if start_ms <= int(candle[CANDLE_TIME]) < end_ms
        ]
        if not candles:
            raise StateError(
                f'No stored {timeframe} candles for {symbol} in range; run `simulation fetch` first'
            )
        outcome = replay(candles, pair, self.rebalancer, params)
        run_id = _run_id(symbol, timeframe, start_ms, end_ms, pair, params)
        ledger_path = self._write_run(run_id, exchange_id, symbol, timeframe, start_ms, end_ms,
                                      pair, params, outcome, candles)
        last_close = float(candles[-1][_CLOSE])
        return SimRunResult(
            symbol=symbol,
            timeframe=timeframe,
            run_id=run_id,
            start_ms=start_ms,
            end_ms=end_ms,
            capital=params.capital,
            fee_rate=params.fee_rate,
            bars=len(candles),
            orders_placed=outcome.orders_placed,
            fills=len(outcome.fills),
            rejects=outcome.rejects,
            final_base=outcome.final_base,
            final_stable=outcome.final_stable,
            final_value=quote_notional(outcome.final_base, last_close) + outcome.final_stable,
            ledger_path=str(ledger_path),
        )

    def _write_run(self, run_id, exchange_id, symbol, timeframe, start_ms, end_ms,
                   pair, params, outcome, candles):
        '''Write a fresh sim ledger + params file; return the ledger path.'''
        run_dir = self.store.root / c.SIM_RUNS_DIRNAME / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = run_dir / c.SIM_LEDGER_FILENAME
        if ledger_path.exists():
            ledger_path.unlink()  # rewrite from scratch so a re-run is byte-identical
        ledger = LedgerStore(ledger_path)
        for fill in outcome.fills:
            ledger.append_fill(fill)
        run_meta = {
            'run_id': run_id,
            'exchange': exchange_id,
            'symbol': symbol,
            'timeframe': timeframe,
            'start_ms': start_ms,
            'end_ms': end_ms,
            'capital': params.capital,
            'fee_rate': params.fee_rate,
            'amount_precision': params.amount_precision,
            'min_cost': params.min_cost,
            'target_volatile_pct': pair.target_volatile_pct,
            'band_pct': pair.band_pct,
            'min_notional': pair.min_notional,
            'bars': len(candles),
            'fills': len(outcome.fills),
            # Final marks — let `simulation report` mark to market offline (no candle re-read).
            'final_base': outcome.final_base,
            'final_stable': outcome.final_stable,
            'final_close': float(candles[-1][_CLOSE]),
        }
        (run_dir / c.SIM_RUN_FILENAME).write_text(
            json.dumps(run_meta, indent=2) + '\n', encoding='utf-8'
        )
        return ledger_path


def _run_id(
    symbol: str, timeframe: str, start_ms: int, end_ms: int, pair: PairConfig, params: ReplayParams
) -> str:
    '''Deterministic run id: a short digest of every input that shapes the ledger.'''
    canonical = '|'.join(str(part) for part in (
        symbol, timeframe, start_ms, end_ms,
        params.capital, params.fee_rate, params.amount_precision, params.min_cost,
        pair.target_volatile_pct, pair.band_pct, pair.min_notional, pair.max_trade_notional,
    ))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]
