'''Phase 19 tests: the `simulation report` command wired end to end.

The report manager is faked via the ``_simulation_report_manager`` seam, backed by
a real store holding a hand-written run (run.json + ledger.jsonl).
'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import SCHEMA_VERSION, SIM_RUN_FILENAME, SIM_RUNS_DIRNAME, ExitCode
from ccbalancer.managers.simulation_report_manager import SimulationReportManager
from ccbalancer.models import Fill
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.stores.simulation_store import SimulationStore

_META = {
    'run_id': 'toy123', 'symbol': 'BTC/USDT', 'capital': 1000.0,
    'final_base': 3.0, 'final_stable': 719.28, 'final_close': 120.0,
}
_FILLS = [
    Fill('2022-06-01T00:00:00Z', 'BTC/USDT', 'buy', 100.0, 5.0, 0.5, 'USDT', 'sim-0'),
    Fill('2023-06-01T00:00:00Z', 'BTC/USDT', 'sell', 110.0, 2.0, 0.22, 'USDT', 'sim-1'),
]


def _inject(monkeypatch, tmp_path) -> None:
    store = SimulationStore(tmp_path / 'simulation')
    run_dir = store.root / SIM_RUNS_DIRNAME / 'toy123'
    run_dir.mkdir(parents=True)
    (run_dir / SIM_RUN_FILENAME).write_text(json.dumps(_META), encoding='utf-8')
    ledger = LedgerStore(run_dir / 'ledger.jsonl')
    for fill in _FILLS:
        ledger.append_fill(fill)
    monkeypatch.setattr(cli, '_simulation_report_manager', lambda config: SimulationReportManager(store))


def test_report_json_emits_stable_contract(appdir, monkeypatch, tmp_path, capsys):
    _inject(monkeypatch, tmp_path)

    code = cli.main(['simulation', 'report', 'toy123', '--json'])
    assert code == int(ExitCode.OK)
    payload = json.loads(capsys.readouterr().out)

    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'simulation report'
    assert payload['run_id'] == 'toy123'
    assert round(payload['total_pnl'], 2) == 79.28
    assert round(payload['roi_pct'], 3) == 7.928
    assert [row['year'] for row in payload['by_year']] == ['2022', '2023']


def test_report_unknown_run_exits_config_error(appdir, monkeypatch, tmp_path, capsys):
    _inject(monkeypatch, tmp_path)

    code = cli.main(['simulation', 'report', 'missing', '--json'])
    assert code == int(ExitCode.CONFIG_ERROR)  # StateError -> exit 2


def test_report_text_output(appdir, monkeypatch, tmp_path, capsys):
    _inject(monkeypatch, tmp_path)

    cli.main(['simulation', 'report', 'toy123'])
    out = capsys.readouterr().out
    assert 'backtest report' in out and 'ROI' in out and 'by year' in out
