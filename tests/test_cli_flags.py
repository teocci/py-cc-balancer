'''Phase 12 tests: the `flag` commands (register, evaluate, remove).'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import FLAGS_FILENAME, PORTFOLIO_FILENAME, SCHEMA_VERSION, ExitCode
from ccbalancer.models import PairConfig
from ccbalancer.stores.flags_store import FlagsStore
from ccbalancer.stores.portfolio_store import PortfolioStore

from .conftest import FakeExchangeStore


def _add_pair(appdir) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0))


def _exchange(last=65000.0) -> FakeExchangeStore:
    return FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        balance={'free': {'BTC': 1.0, 'USDT': 5000.0}, 'used': {}, 'total': {'BTC': 1.0, 'USDT': 5000.0}},
        tickers={'BTC/USDT': {'last': last, 'bid': last, 'ask': last}},
    )


def _no_network(config):
    raise AssertionError('flag command made an unexpected network call')


def _run_json(argv, capsys) -> dict:
    code = cli.main(argv)
    assert code == int(ExitCode.OK)
    return json.loads(capsys.readouterr().out)


# --- add / remove (local writes, no network) ------------------------------


def test_flag_add_registers_and_persists(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['flag', 'add', 'BTC/USDT', 'price', 'ge', '100000', '--json'], capsys)
    assert payload['command'] == 'flag add'
    assert payload['milestone']['id'] == 1
    assert payload['milestone']['expression'] == 'price >= 100000'
    stored = FlagsStore(appdir / FLAGS_FILENAME).load()
    assert len(stored) == 1 and stored[0].symbol == 'BTC/USDT'


def test_flag_add_rejects_unknown_metric(appdir):
    with pytest.raises(SystemExit):  # argparse choices reject it before dispatch
        cli.main(['flag', 'add', 'BTC/USDT', 'rsi', 'ge', '70'])


def test_flag_remove_deletes_milestone(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    cli.main(['flag', 'add', 'BTC/USDT', 'price', 'ge', '100000'])
    capsys.readouterr()
    payload = _run_json(['flag', 'remove', '1', '--json'], capsys)
    assert payload['removed']['id'] == 1
    assert FlagsStore(appdir / FLAGS_FILENAME).load() == []


def test_flag_remove_unknown_id_errors(appdir, monkeypatch):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    code = cli.main(['flag', 'remove', '7'])
    assert code == int(ExitCode.CONFIG_ERROR)


# --- list / evaluate (live, reports hits) ---------------------------------


def test_flag_list_reports_hit_against_live_price(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    cli.main(['flag', 'add', 'BTC/USDT', 'price', 'ge', '60000'])
    capsys.readouterr()
    payload = _run_json(['flag', 'list', '--json'], capsys)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'flag list'
    assert payload['count'] == 1
    flag = payload['flags'][0]
    assert flag['status'] == 'hit'
    assert flag['current_value'] == 65000.0


def test_flag_list_reports_miss(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    cli.main(['flag', 'add', 'BTC/USDT', 'price', 'ge', '100000'])
    capsys.readouterr()
    payload = _run_json(['flag', 'list', '--json'], capsys)
    assert payload['flags'][0]['status'] == 'miss'


def test_flag_list_evaluates_allocation_metric(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    # 1 BTC @ 65000 = 65000 vs 5000 USDT → ~92.86% volatile.
    cli.main(['flag', 'add', 'BTC/USDT', 'volatile_pct', 'ge', '90'])
    capsys.readouterr()
    payload = _run_json(['flag', 'list', '--json'], capsys)
    assert payload['flags'][0]['status'] == 'hit'


def test_flag_list_unconfigured_symbol_is_unknown(appdir, monkeypatch, capsys):
    # No pair configured → no snapshot → cannot evaluate; no network needed.
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    cli.main(['flag', 'add', 'ETH/USDT', 'price', 'ge', '5000'])
    capsys.readouterr()
    payload = _run_json(['flag', 'list', '--json'], capsys)
    assert payload['flags'][0]['status'] == 'unknown'
    assert payload['flags'][0]['current_value'] is None


def test_flag_list_empty_without_network(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', _no_network)
    payload = _run_json(['flag', 'list', '--json'], capsys)
    assert payload['count'] == 0
    assert payload['flags'] == []


def test_flag_list_pair_filter(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    cli.main(['flag', 'add', 'BTC/USDT', 'price', 'ge', '60000'])
    cli.main(['flag', 'add', 'ETH/USDT', 'price', 'ge', '5000'])
    capsys.readouterr()
    payload = _run_json(['flag', 'list', '--json', '--pair', 'BTC/USDT'], capsys)
    assert payload['count'] == 1
    assert payload['flags'][0]['symbol'] == 'BTC/USDT'
