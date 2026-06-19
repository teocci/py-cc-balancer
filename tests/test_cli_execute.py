'''Phase 10 tests: the `rebalance`, `orders`, and `cancel` commands end to end.

The exchange seam is wired to an in-memory fake; these tests assert the safety
guardrails (dry-run default, confirm-token, session cap, kill-switch) and that an
executed rebalance places exactly the planned order and writes state/history/ledger.
'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import (
    CCB_PREFIX,
    CONFIG_FILENAME,
    ENV_API_KEY,
    ENV_API_SECRET,
    HISTORY_FILENAME,
    KILL_SWITCH_FILENAME,
    LEDGER_FILENAME,
    PORTFOLIO_FILENAME,
    STATE_FILENAME,
    ExitCode,
)
from ccbalancer.models import PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore

from .conftest import FakeExchangeStore


def _setup(appdir, monkeypatch, *, cap: float | None = None, creds: bool = True) -> FakeExchangeStore:
    # 1 BTC @ 50k vs 5000 USDT on an 80/20 target -> a SELL of ~$5995 notional.
    exchange = FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        balance={
            'free': {'BTC': 1.0, 'USDT': 5000.0},
            'used': {'BTC': 0.0, 'USDT': 0.0},
            'total': {'BTC': 1.0, 'USDT': 5000.0},
        },
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0))
    if cap is not None:
        appdir.mkdir(parents=True, exist_ok=True)
        (appdir / CONFIG_FILENAME).write_text(f'[safety]\nmax_session_notional_usd = {cap}\n', encoding='utf-8')
    if creds:
        monkeypatch.setenv(ENV_API_KEY, 'trade-key-1234')
        monkeypatch.setenv(ENV_API_SECRET, 'trade-secret-5678')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)
    return exchange


def _json(argv: list[str], capsys, expect: ExitCode = ExitCode.OK) -> dict:
    code = cli.main(argv)
    assert code == int(expect), capsys.readouterr()
    return json.loads(capsys.readouterr().out)


def _token(appdir, monkeypatch, capsys) -> str:
    payload = _json(['rebalance', '--json'], capsys)
    return payload['confirm_token']


# --- dry-run is the default and writes nothing ----------------------------


def test_rebalance_dry_run_is_default_and_writes_nothing(appdir, monkeypatch, capsys):
    _setup(appdir, monkeypatch, cap=100000.0)
    payload = _json(['rebalance', '--json'], capsys)
    assert payload['dry_run'] is True
    assert payload['confirm_token']
    assert payload['pairs'][0]['proposed_order']['side'] == 'sell'
    assert not (appdir / STATE_FILENAME).exists()
    assert not (appdir / HISTORY_FILENAME).exists()
    assert not (appdir / LEDGER_FILENAME).exists()


def test_plan_issues_confirm_token(appdir, monkeypatch, capsys):
    _setup(appdir, monkeypatch, cap=100000.0)
    payload = _json(['plan', '--json'], capsys)
    assert payload['confirm_token']


# --- execution refuses without a valid confirm-token ----------------------


def test_execute_without_confirm_is_blocked(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    code = cli.main(['rebalance', '--execute', '--json'])
    assert code == int(ExitCode.SAFETY_BLOCKED)
    assert exchange.created == []


def test_execute_with_stale_confirm_is_blocked(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    code = cli.main(['rebalance', '--execute', '--confirm', 'deadbeef', '--json'])
    assert code == int(ExitCode.SAFETY_BLOCKED)
    assert exchange.created == []


# --- a valid confirm-token places exactly the planned order ---------------


def test_execute_with_valid_confirm_places_and_persists(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    token = _token(appdir, monkeypatch, capsys)
    payload = _json(['rebalance', '--execute', '--confirm', token, '--json'], capsys)
    assert payload['dry_run'] is False
    assert payload['results'][0]['status'] == 'submitted'
    assert len(exchange.created) == 1
    assert exchange.created[0]['clientOrderId'].startswith(CCB_PREFIX)
    assert (appdir / STATE_FILENAME).is_file()
    assert (appdir / HISTORY_FILENAME).is_file()
    assert (appdir / LEDGER_FILENAME).is_file()


def test_execute_re_run_is_idempotent(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    token = _token(appdir, monkeypatch, capsys)
    cli.main(['rebalance', '--execute', '--confirm', token, '--json'])
    capsys.readouterr()
    # The first placement now rests as our open order; a re-run must cancel it first.
    exchange.open_orders = [
        {'id': 'rest-1', 'symbol': 'BTC/USDT', 'clientOrderId': exchange.created[0]['clientOrderId']}
    ]
    cli.main(['rebalance', '--execute', '--confirm', token, '--json'])
    assert [c['id'] for c in exchange.cancelled] == ['rest-1']


# --- session cap and kill-switch both block -------------------------------


def test_session_cap_blocks_oversized_run(appdir, monkeypatch, capsys):
    # Default cap (1000) is below the ~5995 notional of the planned SELL.
    exchange = _setup(appdir, monkeypatch)
    token = _token(appdir, monkeypatch, capsys)
    code = cli.main(['rebalance', '--execute', '--confirm', token, '--json'])
    assert code == int(ExitCode.SAFETY_BLOCKED)
    assert exchange.created == []


def test_kill_switch_blocks_execution(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    token = _token(appdir, monkeypatch, capsys)
    (appdir / KILL_SWITCH_FILENAME).write_text('', encoding='utf-8')
    code = cli.main(['rebalance', '--execute', '--confirm', token, '--json'])
    assert code == int(ExitCode.SAFETY_BLOCKED)
    assert exchange.created == []


def test_execute_without_credentials_is_blocked(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0, creds=False)
    token = _token(appdir, monkeypatch, capsys)
    code = cli.main(['rebalance', '--execute', '--confirm', token, '--json'])
    assert code == int(ExitCode.CONFIG_ERROR)
    assert exchange.created == []


# --- orders / cancel ------------------------------------------------------


def test_orders_lists_and_flags_ours(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    exchange.open_orders = [
        {'id': 'a', 'symbol': 'BTC/USDT', 'side': 'sell', 'amount': 0.1, 'price': 50010.0,
         'clientOrderId': f'{CCB_PREFIX}1'},
        {'id': 'b', 'symbol': 'BTC/USDT', 'side': 'buy', 'amount': 0.1, 'price': 49990.0,
         'clientOrderId': 'manual'},
    ]
    payload = _json(['orders', '--json'], capsys)
    flags = {o['id']: o['ours'] for o in payload['orders']}
    assert flags == {'a': True, 'b': False}


def test_cancel_dry_run_then_execute(appdir, monkeypatch, capsys):
    exchange = _setup(appdir, monkeypatch, cap=100000.0)
    exchange.open_orders = [
        {'id': 'a', 'symbol': 'BTC/USDT', 'clientOrderId': f'{CCB_PREFIX}1'},
        {'id': 'b', 'symbol': 'BTC/USDT', 'clientOrderId': 'manual'},
    ]
    dry = _json(['cancel', '--json'], capsys)
    assert dry['dry_run'] is True
    assert [o['id'] for o in dry['cancelled']] == ['a']
    assert exchange.cancelled == []
    done = _json(['cancel', '--execute', '--json'], capsys)
    assert done['dry_run'] is False
    assert [c['id'] for c in exchange.cancelled] == ['a']
