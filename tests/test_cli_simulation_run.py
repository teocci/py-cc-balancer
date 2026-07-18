'''Phase 18 tests: the `simulation run` command wired end to end.

The run manager is faked via the ``_simulation_run_manager`` seam (real store
under tmp_path, pre-seeded candles); the pair is a real configured entry.
'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import PORTFOLIO_FILENAME, SCHEMA_VERSION, ExitCode
from ccbalancer.managers.rebalance_manager import RebalanceManager
from ccbalancer.managers.simulation_run_manager import SimulationRunManager
from ccbalancer.models import PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore
from ccbalancer.stores.simulation_store import SimulationStore

_DAY_MS = 86_400_000
_START = 1_661_990_400_000


def _candle(i: int, o: float, h: float, low: float, c: float) -> list[float]:
    return [_START + i * _DAY_MS, o, h, low, c, 1000.0]


def _configure_pair(appdir) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0))


def _inject(monkeypatch, tmp_path) -> SimulationStore:
    store = SimulationStore(tmp_path / 'simulation')
    store.append('binance', 'BTC/USDT', '1d', [
        _candle(0, 100, 100, 99, 100),
        _candle(1, 100, 101, 98, 100),  # crosses -> a BUY fills
        _candle(2, 100, 100, 99, 100),
    ])
    manager = SimulationRunManager(store, RebalanceManager(quote_sanity_pct=15.0, limit_offset_pct=0.0, min_interval_hours=0))
    monkeypatch.setattr(cli, '_simulation_run_manager', lambda config: manager)
    return store


def test_run_json_emits_stable_contract(appdir, monkeypatch, tmp_path, capsys):
    _configure_pair(appdir)
    _inject(monkeypatch, tmp_path)

    code = cli.main(['simulation', 'run', 'BTC/USDT', '--timeframe', '1d',
                     '--start', '2022-09-01', '--end', '2022-12-01', '--exchange', 'binance', '--json'])
    assert code == int(ExitCode.OK)
    payload = json.loads(capsys.readouterr().out)

    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'simulation run'
    assert payload['symbol'] == 'BTC/USDT'
    assert payload['bars'] == 3
    assert payload['fills'] == 1
    assert 'run_id' in payload and 'final_value' in payload
    assert payload['ledger_path'].endswith('ledger.jsonl')


def test_run_unconfigured_pair_exits_config_error(appdir, monkeypatch, tmp_path, capsys):
    _inject(monkeypatch, tmp_path)  # no pair configured

    code = cli.main(['simulation', 'run', 'ETH/USDT', '--start', '2022-09-01', '--exchange', 'binance', '--json'])
    assert code == int(ExitCode.CONFIG_ERROR)


def test_run_lowercase_symbol_normalized(appdir, monkeypatch, tmp_path, capsys):
    _configure_pair(appdir)
    _inject(monkeypatch, tmp_path)

    cli.main(['simulation', 'run', 'btc/usdt', '--timeframe', '1d',
              '--start', '2022-09-01', '--end', '2022-12-01', '--exchange', 'binance', '--json'])
    assert json.loads(capsys.readouterr().out)['symbol'] == 'BTC/USDT'


def test_run_text_output(appdir, monkeypatch, tmp_path, capsys):
    _configure_pair(appdir)
    _inject(monkeypatch, tmp_path)

    cli.main(['simulation', 'run', 'BTC/USDT', '--timeframe', '1d',
              '--start', '2022-09-01', '--end', '2022-12-01', '--exchange', 'binance'])
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out and 'backtest' in out and 'ledger:' in out
