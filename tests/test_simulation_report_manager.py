'''Phase 19 tests: the backtest P&L report over a run's sim ledger.

Reuses the average-cost `walk_fills` and marks the residual position to the run's
final close. A hand-checked toy ledger pins realized/unrealized/ROI, and the
per-year breakdown must sum back to the totals.
'''

from __future__ import annotations

import json

import pytest

from ccbalancer.constants import SIM_LEDGER_FILENAME, SIM_RUN_FILENAME, SIM_RUNS_DIRNAME
from ccbalancer.exceptions import StateError
from ccbalancer.managers.simulation_report_manager import SimulationReportManager, build_report
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.models import Fill
from ccbalancer.stores.simulation_store import SimulationStore

# Toy run: BUY 5 @100 (fee 0.5) in 2022, SELL 2 @110 (fee 0.22) in 2023; final close 120.
_META = {
    'run_id': 'toy123', 'symbol': 'BTC/USDT', 'capital': 1000.0,
    'final_base': 3.0, 'final_stable': 719.28, 'final_close': 120.0,
}
_FILLS = [
    {'ts': '2022-06-01T00:00:00Z', 'symbol': 'BTC/USDT', 'side': 'buy', 'price': 100.0, 'qty': 5.0,
     'fee': 0.5, 'fee_currency': 'USDT', 'order_id': 'sim-0'},
    {'ts': '2023-06-01T00:00:00Z', 'symbol': 'BTC/USDT', 'side': 'sell', 'price': 110.0, 'qty': 2.0,
     'fee': 0.22, 'fee_currency': 'USDT', 'order_id': 'sim-1'},
]


def test_build_report_pnl_and_roi_hand_checked():
    report = build_report(_META, _FILLS)
    assert report['position_qty'] == pytest.approx(3.0)
    assert report['avg_cost'] == pytest.approx(100.1)
    assert report['cost_basis'] == pytest.approx(300.3)
    assert report['realized_pnl'] == pytest.approx(19.58)
    assert report['unrealized_pnl'] == pytest.approx(59.7)   # 3*120 - 300.3
    assert report['total_pnl'] == pytest.approx(79.28)
    assert report['fees_paid'] == pytest.approx(0.72)
    assert report['roi_pct'] == pytest.approx(7.928)          # 79.28 / 1000
    assert report['final_value'] == pytest.approx(1079.28)    # 3*120 + 719.28


def test_build_report_per_year_sums_to_total():
    report = build_report(_META, _FILLS)
    by_year = {row['year']: row for row in report['by_year']}
    assert set(by_year) == {'2022', '2023'}
    assert by_year['2022']['realized_pnl'] == pytest.approx(0.0)   # buy year
    assert by_year['2023']['realized_pnl'] == pytest.approx(19.58)
    total_realized = sum(row['realized_pnl'] for row in report['by_year'])
    assert total_realized == pytest.approx(report['realized_pnl'])
    total_fees = sum(row['fees'] for row in report['by_year'])
    assert total_fees == pytest.approx(report['fees_paid'])


def test_build_report_includes_trade_timeline():
    report = build_report(_META, _FILLS)
    assert len(report['trades']) == 2
    assert report['trades'][0]['side'] == 'buy'
    assert report['trades'][1]['realized_pnl'] == pytest.approx(19.58)


def test_report_manager_reads_run_from_disk(tmp_path):
    store = SimulationStore(tmp_path)
    run_dir = store.root / SIM_RUNS_DIRNAME / 'toy123'
    run_dir.mkdir(parents=True)
    (run_dir / SIM_RUN_FILENAME).write_text(json.dumps(_META), encoding='utf-8')
    ledger = LedgerStore(run_dir / SIM_LEDGER_FILENAME)
    for f in _FILLS:
        ledger.append_fill(Fill(**{k: f[k] for k in ('ts', 'symbol', 'side', 'price', 'qty', 'fee', 'fee_currency', 'order_id')}))

    report = SimulationReportManager(store).report('toy123')
    assert report['run_id'] == 'toy123'
    assert report['total_pnl'] == pytest.approx(79.28)


def test_report_manager_unknown_run_raises_state_error(tmp_path):
    with pytest.raises(StateError):
        SimulationReportManager(SimulationStore(tmp_path)).report('nope')


def test_build_report_no_fills_is_flat():
    meta = {'run_id': 'r', 'symbol': 'BTC/USDT', 'capital': 1000.0,
            'final_base': 0.0, 'final_stable': 1000.0, 'final_close': 120.0}
    report = build_report(meta, [])
    assert report['realized_pnl'] == 0.0
    assert report['unrealized_pnl'] == 0.0
    assert report['total_pnl'] == 0.0
    assert report['roi_pct'] == pytest.approx(0.0)
    assert report['by_year'] == []
