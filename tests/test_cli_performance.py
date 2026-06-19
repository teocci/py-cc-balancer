'''Phase 11 tests: the `performance` command (live read + ledger-only history).'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import (
    LEDGER_FILENAME,
    PORTFOLIO_FILENAME,
    SCHEMA_VERSION,
    ExitCode,
)
from ccbalancer.models import Fill, PairConfig
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.stores.portfolio_store import PortfolioStore

from .conftest import FakeExchangeStore


def _no_network(config):
    raise AssertionError('performance --history made a network call')


def _add_pair(appdir, **kwargs) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(
        PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0, **kwargs)
    )


def _seed_ledger(appdir, fills) -> None:
    store = LedgerStore(appdir / LEDGER_FILENAME)
    for fill in fills:
        store.append_fill(fill)


def _fill(side, price, qty, fee=0.0) -> Fill:
    return Fill(
        ts='2026-06-18T00:00:00Z', symbol='BTC/USDT', side=side, price=price,
        qty=qty, fee=fee, fee_currency='USDT', order_id=None,
    )


def _run_json(argv, capsys) -> dict:
    code = cli.main(argv)
    assert code == int(ExitCode.OK)
    return json.loads(capsys.readouterr().out)


# --- live read ------------------------------------------------------------


def test_performance_live_reports_per_pair_and_portfolio(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    _seed_ledger(appdir, [_fill('buy', 50000.0, 1.0, fee=50.0)])
    exchange = FakeExchangeStore(tickers={'BTC/USDT': {'last': 60000.0}})
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)
    payload = _run_json(['performance', '--json'], capsys)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'performance'
    pair = payload['pairs'][0]
    assert pair['symbol'] == 'BTC/USDT'
    assert pair['unrealized_pnl'] == pytest.approx(9950.0)  # 60000 - (50000 + 50)
    assert payload['portfolio']['total_pnl'] == pytest.approx(9950.0)


def test_performance_live_text_output(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    _seed_ledger(appdir, [_fill('buy', 50000.0, 1.0)])
    exchange = FakeExchangeStore(tickers={'BTC/USDT': {'last': 60000.0}})
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)
    cli.main(['performance'])
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out
    assert 'TOTAL' in out


def test_performance_live_empty_portfolio(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', lambda config: FakeExchangeStore())
    payload = _run_json(['performance', '--json'], capsys)
    assert payload['pairs'] == []
    assert payload['portfolio']['roi_pct'] is None


def test_performance_live_baseline_with_empty_ledger(appdir, monkeypatch, capsys):
    _add_pair(appdir, entry_price=40000.0, invested_capital=40000.0)
    exchange = FakeExchangeStore(tickers={'BTC/USDT': {'last': 50000.0}})
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)
    payload = _run_json(['performance', '--json'], capsys)
    pair = payload['pairs'][0]
    assert pair['from_baseline'] is True
    assert pair['roi_pct'] == pytest.approx(25.0)


# --- history (audit, no network) ------------------------------------------


def test_performance_history_replays_ledger_without_network(appdir, monkeypatch, capsys):
    _seed_ledger(appdir, [
        _fill('buy', 50000.0, 1.0, fee=50.0),
        _fill('sell', 60000.0, 1.0, fee=60.0),
    ])
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['performance', '--history', '--json'], capsys)
    assert payload['command'] == 'performance'
    assert payload['count'] == 1
    assert payload['pairs'][0]['realized_pnl'] == pytest.approx(9890.0)


def test_performance_history_empty_when_no_ledger(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['performance', '--history', '--json'], capsys)
    assert payload['count'] == 0
    assert payload['pairs'] == []


def test_performance_history_pair_filter(appdir, monkeypatch, capsys):
    _seed_ledger(appdir, [_fill('buy', 50000.0, 1.0)])
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['performance', '--history', '--json', '--pair', 'ETH/USDT'], capsys)
    assert payload['pairs'] == []
