'''Phase 9 tests: the audit command group (decisions, history, export).

These commands read only local logs; they must never touch the exchange, so the
exchange seam is wired to raise — a call would fail the test.
'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import (
    DECISION_LOG_FILENAME,
    HISTORY_FILENAME,
    PORTFOLIO_FILENAME,
    SCHEMA_VERSION,
    STATE_FILENAME,
    ExitCode,
)
from ccbalancer.models import HistoryEvent, PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore
from ccbalancer.stores.state_store import StateStore

from .conftest import FakeExchangeStore


def _no_network(config):
    raise AssertionError('audit command made a network call')


def _add_pair(appdir) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0))


def _run_json(argv: list[str], capsys) -> dict:
    code = cli.main(argv)
    assert code == int(ExitCode.OK)
    return json.loads(capsys.readouterr().out)


def _seed_history(appdir) -> None:
    store = StateStore(appdir / STATE_FILENAME, appdir / HISTORY_FILENAME)
    store.append_event(
        HistoryEvent(
            ts='2026-06-18T12:00:00Z', symbol='BTC/USDT', side='sell', amount=0.12,
            price=50010.0, notional=6001.2, drift_pct=10.9, reason='OK',
            exchange='bybit', testnet=True, order_id='order-1', status='submitted',
        )
    )


# --- plan writes the decision memory --------------------------------------


def test_plan_appends_one_decision_record_per_pair(appdir, monkeypatch, fake_exchange, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: fake_exchange)
    cli.main(['plan', '--json'])
    lines = (appdir / DECISION_LOG_FILENAME).read_text(encoding='utf-8').splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record['symbol'] == 'BTC/USDT'
    assert record['command'] == 'plan'
    assert record['reason'] == 'ok'


def test_plan_run_twice_appends_each_time(appdir, monkeypatch, fake_exchange):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: fake_exchange)
    cli.main(['plan', '--json'])
    cli.main(['plan', '--json'])
    lines = (appdir / DECISION_LOG_FILENAME).read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2


def test_status_does_not_write_decision_log(appdir, monkeypatch):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _balanced_exchange())
    cli.main(['status', '--json'])
    assert not (appdir / DECISION_LOG_FILENAME).exists()


def _balanced_exchange() -> FakeExchangeStore:
    return FakeExchangeStore(
        markets={'BTC/USDT': {'active': True, 'precision': {'amount': 3}}},
        balance={
            'free': {'BTC': 0.8, 'USDT': 10000.0},
            'used': {'BTC': 0.0, 'USDT': 0.0},
            'total': {'BTC': 0.8, 'USDT': 10000.0},
        },
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )


# --- decisions ------------------------------------------------------------


def test_decisions_replays_logged_records(appdir, monkeypatch, fake_exchange, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: fake_exchange)
    cli.main(['plan', '--json'])
    capsys.readouterr()
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['decisions', '--json'], capsys)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'decisions'
    assert payload['count'] == 1
    assert payload['decisions'][0]['symbol'] == 'BTC/USDT'


def test_decisions_empty_when_no_log(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['decisions', '--json'], capsys)
    assert payload['count'] == 0
    assert payload['decisions'] == []


def test_decisions_pair_filter_restricts(appdir, monkeypatch, capsys):
    store = cli.DecisionStore(appdir / DECISION_LOG_FILENAME)
    store.append({'symbol': 'BTC/USDT', 'reason': 'ok'})
    store.append({'symbol': 'ETH/USDT', 'reason': 'within_band'})
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['decisions', '--json', '--pair', 'ETH/USDT'], capsys)
    assert [d['symbol'] for d in payload['decisions']] == ['ETH/USDT']


def test_decisions_text_output(appdir, monkeypatch, fake_exchange, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: fake_exchange)
    cli.main(['plan', '--json'])
    capsys.readouterr()
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    cli.main(['decisions'])
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out
    assert '[ok]' in out


# --- history --------------------------------------------------------------


def test_history_replays_logged_events(appdir, monkeypatch, capsys):
    _seed_history(appdir)
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['history', '--json'], capsys)
    assert payload['command'] == 'history'
    assert payload['count'] == 1
    assert payload['history'][0]['order_id'] == 'order-1'


def test_history_empty_when_no_log(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['history', '--json'], capsys)
    assert payload['count'] == 0


# --- export ---------------------------------------------------------------


def test_export_bundles_logs_as_json_without_flag(appdir, monkeypatch, capsys):
    _seed_history(appdir)
    cli.DecisionStore(appdir / DECISION_LOG_FILENAME).append({'symbol': 'BTC/USDT', 'reason': 'ok'})
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    code = cli.main(['export'])
    assert code == int(ExitCode.OK)
    payload = json.loads(capsys.readouterr().out)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'export'
    assert len(payload['decisions']) == 1
    assert len(payload['history']) == 1
