'''Cost-basis performance accounting (DESIGN.md signal #2).

:class:`PerformanceManager` answers *is the strategy working?* by walking the
append-only fill ledger with the **average-cost** method and marking the held
position to market with a live ticker. It computes realized P&L per sell, the
unrealized P&L of the open position, and ROI — per pair and across the portfolio.

Two modes:

- **read** (``performance``): needs current prices, so it fetches a ticker per
  pair and returns fully-marked :class:`PerformanceSnapshot` objects. When a pair
  has no fills yet it falls back to the pair's entry/invested baseline so
  unrealized P&L is still meaningful.
- **audit** (``performance --history``): replays realized P&L from the ledger
  only and never touches the exchange.

All money math is routed through :class:`~decimal.Decimal` so ROI is exact to the
cent; values are converted to ``float`` only at the model boundary.

Fee handling: fees are normalized to quote terms. A fee charged in the base asset
is valued at the fill price; a fee in the quote asset (or with no/other currency)
is taken as-is. This keeps accounting deterministic without extra price lookups.
'''

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from ccbalancer.models import PerformanceSnapshot

if TYPE_CHECKING:
    from ccbalancer.models import PairConfig
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.ledger_store import LedgerStore

__all__ = ['PerformanceManager', 'walk_fills', 'portfolio_totals']

_PCT = Decimal(100)
_ZERO = Decimal(0)


@dataclass(slots=True)
class _Acc:
    '''Mutable running totals while walking a pair's fills (Decimal terms).'''

    position: Decimal = _ZERO
    cost_basis: Decimal = _ZERO
    realized: Decimal = _ZERO
    total_buy_cost: Decimal = _ZERO
    fees: Decimal = _ZERO


@dataclass(slots=True)
class PerformanceManager:
    '''Compute cost-basis P&L from the fill ledger and live prices.

    Attributes:
        ledger_store: Source of executed fills (the cost-basis ledger).
        exchange: Exchange store for current tickers; unused in audit mode and
            may be ``None`` when only :meth:`realized_history` is called.
    '''

    ledger_store: LedgerStore
    exchange: ExchangeStore | None = None
    _fills: dict[str, list[dict[str, object]]] | None = field(
        default=None, repr=False, compare=False
    )

    def snapshots(self, pairs: list[PairConfig]) -> list[PerformanceSnapshot]:
        '''Build a marked-to-market snapshot for each pair (read mode).'''
        by_symbol = self._fills_by_symbol()
        return [self._snapshot(pair, by_symbol.get(pair.symbol, [])) for pair in pairs]

    def realized_history(self, symbols: set[str] | None = None) -> list[dict[str, object]]:
        '''Replay realized P&L per symbol from the ledger only (audit mode).

        Returns one record per symbol that has fills, each carrying the realized
        total, fees, residual position, and the per-fill trade timeline. No
        exchange access — unrealized P&L is omitted because it needs a live price.
        '''
        records = []
        for symbol, fills in self._fills_by_symbol().items():
            if symbols is not None and symbol not in symbols:
                continue
            records.append(_history_record(symbol, fills))
        return records

    def _snapshot(self, pair: PairConfig, fills: list[dict[str, object]]) -> PerformanceSnapshot:
        price = _dec(self.exchange.fetch_ticker(pair.symbol).get('last'))  # type: ignore[union-attr]
        if fills:
            acc, _ = walk_fills(fills, pair.base, pair.quote)
            return _build_snapshot(pair, acc, price, from_baseline=False, fill_count=len(fills))
        if _has_baseline(pair):
            return _build_snapshot(pair, _baseline_acc(pair), price, from_baseline=True, fill_count=0)
        return _build_snapshot(pair, _Acc(), price, from_baseline=False, fill_count=0)

    def _fills_by_symbol(self) -> dict[str, list[dict[str, object]]]:
        if self._fills is None:
            grouped: dict[str, list[dict[str, object]]] = {}
            for fill in self.ledger_store.load():
                grouped.setdefault(str(fill.get('symbol')), []).append(fill)
            self._fills = grouped
        return self._fills


def walk_fills(
    fills: list[dict[str, object]], base: str, quote: str
) -> tuple[_Acc, list[dict[str, object]]]:
    '''Apply fills in order via average-cost; return totals and the trade timeline.'''
    acc = _Acc()
    trades = [_apply_fill(acc, fill, base, quote) for fill in fills]
    return acc, trades


def portfolio_totals(snapshots: list[PerformanceSnapshot]) -> dict[str, object]:
    '''Aggregate per-pair money fields into portfolio totals (exact ROI).'''
    realized = sum((_dec(s.realized_pnl) for s in snapshots), _ZERO)
    unrealized = sum((_dec(s.unrealized_pnl) for s in snapshots), _ZERO)
    cost_basis = sum((_dec(s.cost_basis) for s in snapshots), _ZERO)
    market_value = sum((_dec(s.market_value) for s in snapshots), _ZERO)
    fees = sum((_dec(s.fees_paid) for s in snapshots), _ZERO)
    invested = sum((_dec(s.invested) for s in snapshots), _ZERO)
    total = realized + unrealized
    return {
        'realized_pnl': float(realized),
        'unrealized_pnl': float(unrealized),
        'total_pnl': float(total),
        'cost_basis': float(cost_basis),
        'market_value': float(market_value),
        'fees_paid': float(fees),
        'invested': float(invested),
        'roi_pct': float(total / invested * _PCT) if invested > 0 else None,
    }


def _apply_fill(
    acc: _Acc, fill: dict[str, object], base: str, quote: str
) -> dict[str, object]:
    price = _dec(fill.get('price'))
    qty = _dec(fill.get('qty'))
    fee_q = _fee_in_quote(_dec(fill.get('fee')), fill.get('fee_currency'), base, price)
    acc.fees += fee_q
    if fill.get('side') == 'buy':
        realized = _apply_buy(acc, qty, price, fee_q)
    else:
        realized = _apply_sell(acc, qty, price, fee_q)
    return _trade(fill, qty, price, fee_q, realized)


def _apply_buy(acc: _Acc, qty: Decimal, price: Decimal, fee_q: Decimal) -> Decimal | None:
    cost = qty * price + fee_q
    acc.position += qty
    acc.cost_basis += cost
    acc.total_buy_cost += cost
    return None


def _apply_sell(acc: _Acc, qty: Decimal, price: Decimal, fee_q: Decimal) -> Decimal:
    avg = acc.cost_basis / acc.position if acc.position > 0 else _ZERO
    basis_out = avg * qty
    realized = qty * price - fee_q - basis_out
    acc.realized += realized
    acc.position -= qty
    acc.cost_basis -= basis_out
    if acc.position <= 0:  # flat (or bad-data oversell): reset basis to avoid drift
        acc.position = _ZERO
        acc.cost_basis = _ZERO
    return realized


def _build_snapshot(
    pair: PairConfig, acc: _Acc, price: Decimal, *, from_baseline: bool, fill_count: int
) -> PerformanceSnapshot:
    market_value = acc.position * price
    unrealized = market_value - acc.cost_basis
    total = acc.realized + unrealized
    invested = _invested(pair, acc)
    avg_cost = acc.cost_basis / acc.position if acc.position > 0 else None
    roi = total / invested * _PCT if invested > 0 else None
    return PerformanceSnapshot(
        symbol=pair.symbol,
        position_qty=float(acc.position),
        avg_cost=float(avg_cost) if avg_cost is not None else None,
        cost_basis=float(acc.cost_basis),
        current_price=float(price),
        market_value=float(market_value),
        realized_pnl=float(acc.realized),
        unrealized_pnl=float(unrealized),
        total_pnl=float(total),
        fees_paid=float(acc.fees),
        invested=float(invested),
        roi_pct=float(roi) if roi is not None else None,
        from_baseline=from_baseline,
        fill_count=fill_count,
    )


def _history_record(symbol: str, fills: list[dict[str, object]]) -> dict[str, object]:
    base, quote = _split(symbol)
    acc, trades = walk_fills(fills, base, quote)
    avg = acc.cost_basis / acc.position if acc.position > 0 else None
    return {
        'symbol': symbol,
        'realized_pnl': float(acc.realized),
        'fees_paid': float(acc.fees),
        'position_qty': float(acc.position),
        'cost_basis': float(acc.cost_basis),
        'avg_cost': float(avg) if avg is not None else None,
        'fill_count': len(fills),
        'trades': trades,
    }


def _trade(
    fill: dict[str, object], qty: Decimal, price: Decimal, fee_q: Decimal, realized: Decimal | None
) -> dict[str, object]:
    return {
        'ts': fill.get('ts'),
        'side': fill.get('side'),
        'qty': float(qty),
        'price': float(price),
        'fee': float(fee_q),
        'fee_currency': fill.get('fee_currency'),
        'realized_pnl': float(realized) if realized is not None else None,
    }


def _invested(pair: PairConfig, acc: _Acc) -> Decimal:
    '''ROI denominator: the pinned baseline capital if set, else gross buy cost.'''
    if pair.invested_capital is not None:
        return _dec(pair.invested_capital)
    return acc.total_buy_cost


def _baseline_acc(pair: PairConfig) -> _Acc:
    '''Synthesize a position from the pair's entry/invested baseline (no fills).'''
    invested = _dec(pair.invested_capital)
    entry = _dec(pair.entry_price)
    return _Acc(
        position=invested / entry if entry > 0 else _ZERO,
        cost_basis=invested,
        total_buy_cost=invested,
    )


def _has_baseline(pair: PairConfig) -> bool:
    return (
        pair.invested_capital is not None
        and pair.entry_price is not None
        and pair.entry_price > 0
    )


def _fee_in_quote(fee: Decimal, fee_currency: object, base: str, price: Decimal) -> Decimal:
    '''Value a fee in quote terms (base-denominated fees converted at fill price).'''
    if fee == 0:
        return _ZERO
    if fee_currency == base:
        return fee * price
    return fee


def _split(symbol: str) -> tuple[str, str]:
    parts = symbol.split('/')
    if len(parts) != 2:
        return symbol, ''
    return parts[0], parts[1]


def _dec(value: object) -> Decimal:
    if value is None:
        return _ZERO
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return _ZERO
