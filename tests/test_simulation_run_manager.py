'''Phase 18 tests: the `simulation run` orchestrator (read → replay → persist).

The store is real (tmp_path); candles are seeded directly. Covers ledger
persistence, the deterministic byte-identical re-run, the empty-range guard, and
the result summary.
'''

from __future__ import annotations

import pytest

from ccbalancer.constants import SIM_LEDGER_FILENAME, SIM_RUN_FILENAME, SIM_RUNS_DIRNAME
from ccbalancer.exceptions import StateError
from ccbalancer.managers.rebalance_manager import RebalanceManager
from ccbalancer.managers.simulation_run_manager import ReplayParams, SimulationRunManager
from ccbalancer.models import PairConfig
from ccbalancer.stores.simulation_store import SimulationStore

_DAY_MS = 86_400_000
_START = 1_661_990_400_000
_END = _START + 100 * _DAY_MS


def _candle(i: int, o: float, h: float, low: float, c: float) -> list[float]:
    return [_START + i * _DAY_MS, o, h, low, c, 1000.0]


def _seed(tmp_path) -> SimulationStore:
    store = SimulationStore(tmp_path)
    candles = [
        _candle(0, 100, 100, 99, 100),   # BUY @100 decided
        _candle(1, 100, 101, 98, 100),   # crosses -> fills
        _candle(2, 100, 100, 99, 100),   # within band now, no trade
    ]
    store.append('binance', 'BTC/USDT', '1d', candles)
    return store


def _manager(store) -> SimulationRunManager:
    return SimulationRunManager(store, RebalanceManager(quote_sanity_pct=15.0, limit_offset_pct=0.0, min_interval_hours=0))


def _pair() -> PairConfig:
    return PairConfig('BTC/USDT', 80.0, 20.0, band_pct=5.0, min_notional=10.0)


def _params() -> ReplayParams:
    return ReplayParams(capital=10000.0, fee_rate=0.001, amount_precision=8, min_cost=0.0)


def test_run_writes_ledger_and_run_json(tmp_path):
    store = _seed(tmp_path)
    result = _manager(store).run('binance', 'BTC/USDT', '1d', _START, _END, _pair(), _params())

    run_dir = store.root / SIM_RUNS_DIRNAME / result.run_id
    assert (run_dir / SIM_LEDGER_FILENAME).is_file()
    assert (run_dir / SIM_RUN_FILENAME).is_file()
    ledger_lines = (run_dir / SIM_LEDGER_FILENAME).read_text(encoding='utf-8').splitlines()
    assert len(ledger_lines) == result.fills == 1
    assert result.bars == 3
    assert result.final_base == pytest.approx(80.0)


def test_run_is_deterministic_byte_identical(tmp_path):
    store = _seed(tmp_path)
    manager = _manager(store)
    r1 = manager.run('binance', 'BTC/USDT', '1d', _START, _END, _pair(), _params())
    ledger = store.root / SIM_RUNS_DIRNAME / r1.run_id / SIM_LEDGER_FILENAME
    first = ledger.read_bytes()

    r2 = manager.run('binance', 'BTC/USDT', '1d', _START, _END, _pair(), _params())

    assert r2.run_id == r1.run_id  # same inputs -> same run dir
    assert ledger.read_bytes() == first  # re-run rewrites byte-identical, no duplication


def test_run_empty_range_raises_state_error(tmp_path):
    store = _seed(tmp_path)
    future = _END + _DAY_MS
    with pytest.raises(StateError):
        _manager(store).run('binance', 'BTC/USDT', '1d', future, future + _DAY_MS, _pair(), _params())


def test_run_id_changes_with_inputs(tmp_path):
    store = _seed(tmp_path)
    manager = _manager(store)
    a = manager.run('binance', 'BTC/USDT', '1d', _START, _END, _pair(), _params())
    b = manager.run('binance', 'BTC/USDT', '1d', _START, _END, _pair(),
                    ReplayParams(capital=5000.0, fee_rate=0.001, amount_precision=8, min_cost=0.0))
    assert a.run_id != b.run_id