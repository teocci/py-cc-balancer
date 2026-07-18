'''Backtest P&L report over a stored run's simulated ledger.

Reads a completed run (``simulation/runs/{run_id}/`` — ``run.json`` + the isolated
``ledger.jsonl``) and reports realized / unrealized / total P&L, ROI, fees, the
per-trade timeline, and a per-year breakdown. It marks the residual position to
the run's **final candle close** (recorded in ``run.json``) in place of a live
ticker, and reuses the average-cost :func:`walk_fills` from the performance
manager — no accounting is rebuilt here.

Offline and pure: no exchange, no candle re-read, no clock. The per-year breakdown
exists to keep a single headline ROI from hiding cycle dependence (a 2017→now
window is BTC-bull-dominated).
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer import constants as c
from ccbalancer.exceptions import StateError
from ccbalancer.managers.performance_manager import walk_fills
from ccbalancer.stores.ledger_store import LedgerStore

if TYPE_CHECKING:
    from ccbalancer.stores.simulation_store import SimulationStore

__all__ = ['SimulationReportManager', 'build_report']


@dataclass(slots=True)
class SimulationReportManager:
    '''Load a stored run and build its P&L report.

    Attributes:
        store: Simulation store whose ``runs/`` subtree holds the run directories.
    '''

    store: SimulationStore

    def report(self, run_id: str) -> dict[str, object]:
        '''Return the P&L report for ``run_id``.

        Raises:
            StateError: If no run with that id has been recorded.
        '''
        run_dir = self.store.root / c.SIM_RUNS_DIRNAME / run_id
        meta_path = run_dir / c.SIM_RUN_FILENAME
        if not meta_path.is_file():
            raise StateError(f'Run {run_id!r} not found; run `simulation run` first')
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f'Cannot read run metadata {meta_path}: {exc}') from exc
        fills = LedgerStore(run_dir / c.SIM_LEDGER_FILENAME).load()
        return build_report(meta, fills)


def build_report(meta: dict[str, object], fills: list[dict[str, object]]) -> dict[str, object]:
    '''Compute the P&L report from a run's metadata and its ledger fills.'''
    symbol = str(meta['symbol'])
    base, quote = _split(symbol)
    capital = float(meta['capital'])
    final_close = float(meta['final_close'])
    final_value = float(meta['final_base']) * final_close + float(meta['final_stable'])

    acc, trades = walk_fills(fills, base, quote)
    position = float(acc.position)
    cost_basis = float(acc.cost_basis)
    realized = float(acc.realized)
    market_value = position * final_close
    unrealized = market_value - cost_basis
    total = realized + unrealized
    return {
        'run_id': meta.get('run_id'),
        'symbol': symbol,
        'capital': capital,
        'final_close': final_close,
        'position_qty': position,
        'avg_cost': cost_basis / position if position > 0 else None,
        'cost_basis': cost_basis,
        'market_value': market_value,
        'realized_pnl': realized,
        'unrealized_pnl': unrealized,
        'total_pnl': total,
        'fees_paid': float(acc.fees),
        'roi_pct': total / capital * 100.0 if capital > 0 else None,
        'final_value': final_value,
        'trades': trades,
        'by_year': _by_year(trades),
    }


def _by_year(trades: list[dict[str, object]]) -> list[dict[str, object]]:
    '''Bucket the trade timeline by calendar year (realized + fees sum to totals).'''
    buckets: dict[str, dict[str, object]] = {}
    for trade in trades:
        year = str(trade.get('ts'))[:4]
        bucket = buckets.setdefault(year, {'year': year, 'realized_pnl': 0.0, 'fees': 0.0, 'trades': 0})
        bucket['realized_pnl'] += trade.get('realized_pnl') or 0.0
        bucket['fees'] += trade.get('fee') or 0.0
        bucket['trades'] += 1
    return [buckets[year] for year in sorted(buckets)]


def _split(symbol: str) -> tuple[str, str]:
    parts = symbol.split('/')
    if len(parts) != 2:
        return symbol, ''
    return parts[0], parts[1]
