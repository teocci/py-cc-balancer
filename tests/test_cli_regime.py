'''Phase 12 tests: the `regime` command (live price-variance signal).'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import PORTFOLIO_FILENAME, SCHEMA_VERSION, ExitCode
from ccbalancer.models import PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore

from .conftest import FakeExchangeStore


def _add_pair(appdir, **kwargs) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(
        PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0, **kwargs)
    )


def _exchange(last=65000.0) -> FakeExchangeStore:
    return FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        balance={'free': {'BTC': 1.0, 'USDT': 5000.0}, 'used': {}, 'total': {'BTC': 1.0, 'USDT': 5000.0}},
        tickers={'BTC/USDT': {'last': last, 'bid': last, 'ask': last}},
    )


def _run_json(argv, capsys) -> dict:
    code = cli.main(argv)
    assert code == int(ExitCode.OK)
    return json.loads(capsys.readouterr().out)


def test_regime_flags_review_after_run_up(appdir, monkeypatch, capsys):
    _add_pair(appdir, target_set_price=50000.0, target_set_ts='2026-06-01T00:00:00Z')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    payload = _run_json(['regime', '--json'], capsys)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'regime'
    pair = payload['pairs'][0]
    assert pair['flag'] is True
    assert pair['direction'] == 'up'
    assert pair['price_change_pct'] == pytest.approx(30.0)
    assert pair['suggested_ratio'] == {'volatile_pct': 50.0, 'stable_pct': 50.0}


def test_regime_holds_within_review_band(appdir, monkeypatch, capsys):
    _add_pair(appdir, target_set_price=50000.0, target_set_ts='2026-06-01T00:00:00Z')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(55000.0))
    payload = _run_json(['regime', '--json'], capsys)
    pair = payload['pairs'][0]
    assert pair['flag'] is False
    assert pair['suggested_ratio'] == {'volatile_pct': 80.0, 'stable_pct': 20.0}


def test_regime_without_baseline_reports_no_signal(appdir, monkeypatch, capsys):
    _add_pair(appdir)
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    payload = _run_json(['regime', '--json'], capsys)
    pair = payload['pairs'][0]
    assert pair['flag'] is False
    assert pair['direction'] == 'none'
    assert pair['price_change_pct'] is None
    assert pair['suggested_ratio'] is None


def test_regime_text_output_marks_review(appdir, monkeypatch, capsys):
    _add_pair(appdir, target_set_price=50000.0, target_set_ts='2026-06-01T00:00:00Z')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: _exchange(65000.0))
    cli.main(['regime'])
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out
    assert 'REVIEW' in out


def test_regime_empty_portfolio(appdir, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_exchange_store', lambda config: FakeExchangeStore())
    payload = _run_json(['regime', '--json'], capsys)
    assert payload['pairs'] == []
