'''Phase 7 tests: the `status` and `plan` read commands wired end to end.'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import (
    HISTORY_FILENAME,
    PORTFOLIO_FILENAME,
    STATE_FILENAME,
    SCHEMA_VERSION,
    ExitCode,
)
from ccbalancer.models import PairConfig, RebalanceState
from ccbalancer.stores.portfolio_store import PortfolioStore
from ccbalancer.stores.state_store import StateStore

from .conftest import FakeExchangeStore


def _balanced_exchange() -> FakeExchangeStore:
    '''Holdings exactly on an 80/20 target: 0.8 BTC @ 50k vs 10k USDT.'''
    return FakeExchangeStore(
        markets={'BTC/USDT': {'active': True, 'precision': {'amount': 3}}},
        balance={
            'free': {'BTC': 0.8, 'USDT': 10000.0},
            'used': {'BTC': 0.0, 'USDT': 0.0},
            'total': {'BTC': 0.8, 'USDT': 10000.0},
        },
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )


def _setup(appdir, monkeypatch, exchange, *, state: RebalanceState | None = None) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0))
    if state is not None:
        StateStore(appdir / STATE_FILENAME, appdir / HISTORY_FILENAME).save(state)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)


def _run_json(argv: list[str], capsys) -> dict:
    code = cli.main(argv)
    assert code == int(ExitCode.OK)
    return json.loads(capsys.readouterr().out)


def test_plan_json_emits_stable_contract(appdir, monkeypatch, fake_exchange, capsys):
    _setup(appdir, monkeypatch, fake_exchange)
    payload = _run_json(['plan', '--json'], capsys)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'plan'
    pair = payload['pairs'][0]
    assert pair['symbol'] == 'BTC/USDT'
    assert 'days_since_last' in pair
    assert isinstance(pair['reason'], str)


def test_plan_rebalances_when_drifted(appdir, monkeypatch, fake_exchange, capsys):
    # fake_exchange holds 1 BTC (~90.9%) vs an 80% target -> SELL.
    _setup(appdir, monkeypatch, fake_exchange)
    pair = _run_json(['plan', '--json'], capsys)['pairs'][0]
    assert pair['rebalance'] is True
    assert pair['reason'] == 'ok'
    assert pair['proposed_order']['side'] == 'sell'


def test_plan_within_band_when_balanced_exits_zero(appdir, monkeypatch, capsys):
    _setup(appdir, monkeypatch, _balanced_exchange())
    code = cli.main(['plan', '--json'])
    assert code == int(ExitCode.OK)
    pair = json.loads(capsys.readouterr().out)['pairs'][0]
    assert pair['rebalance'] is False
    assert pair['reason'] == 'within_band'
    assert pair['proposed_order'] is None


def test_status_shows_current_target_and_last_rebalance(appdir, monkeypatch, capsys):
    state = RebalanceState('BTC/USDT', '2026-06-01T00:00:00Z', 'sell', 0.5, 50000.0, 3.2, 'OK')
    _setup(appdir, monkeypatch, _balanced_exchange(), state=state)
    pair = _run_json(['status', '--json'], capsys)['pairs'][0]
    assert pair['target_volatile_pct'] == 80.0
    assert pair['current_volatile_pct'] == pytest.approx(80.0)
    assert pair['last_rebalance_at'] == '2026-06-01T00:00:00Z'
    assert isinstance(pair['days_since_last'], float)


def test_status_no_pairs_emits_empty(appdir, monkeypatch, fake_exchange, capsys):
    monkeypatch.setattr(cli, '_exchange_store', lambda config: fake_exchange)
    payload = _run_json(['status', '--json'], capsys)
    assert payload['pairs'] == []


def test_status_text_output(appdir, monkeypatch, capsys):
    _setup(appdir, monkeypatch, _balanced_exchange())
    code = cli.main(['status'])
    assert code == int(ExitCode.OK)
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out
    assert 'target 80.00%' in out


def test_plan_unknown_pair_filter_errors(appdir, monkeypatch, fake_exchange):
    _setup(appdir, monkeypatch, fake_exchange)
    code = cli.main(['plan', '--pair', 'ETH/USDT'])
    assert code == int(ExitCode.CONFIG_ERROR)


def test_plan_pair_filter_restricts(appdir, monkeypatch, fake_exchange, capsys):
    _setup(appdir, monkeypatch, fake_exchange)
    payload = _run_json(['plan', '--json', '--pair', 'BTC/USDT'], capsys)
    assert [p['symbol'] for p in payload['pairs']] == ['BTC/USDT']
