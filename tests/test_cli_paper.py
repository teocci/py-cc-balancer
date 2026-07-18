'''I-19 tests: the paper account run end to end through `cli.main`.

`auth login --paper` creates a credential-free simulated account and seeds its
book; every live command then runs against it unchanged. The paper store's market
data is faked (a shared FakeExchangeStore) so prices are controllable, while the
book persists to the real per-account data dir. Covers login/seed, the simulated
balance, the full plan → rebalance → reconcile rehearsal, and `paper reset`.
'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer import config as config_mod
from ccbalancer.constants import AUTH_FILENAME, ENV_AUTH_BACKEND, PAPER_BOOK_FILENAME, ExitCode
from ccbalancer.stores.auth_store import AuthStore, FileSecretBackend
from ccbalancer.stores.paper_book import PaperBookStore
from ccbalancer.stores.paper_exchange import PaperExchangeStore

from .conftest import FakeExchangeStore


@pytest.fixture
def paper_env(appdir, monkeypatch):
    '''Isolated app dir (file backend) with a shared, controllable paper market.'''
    monkeypatch.setenv(ENV_AUTH_BACKEND, 'file')
    market = FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        tickers={'BTC/USDT': {'last': 100.0, 'bid': 99.0, 'ask': 101.0}},
    )
    monkeypatch.setattr(
        cli, '_paper_exchange_store',
        lambda data_exchange, testnet, data_dir: PaperExchangeStore(
            PaperBookStore(data_dir / PAPER_BOOK_FILENAME), market, fee_rate=0.0),
    )
    return appdir, market


def _run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _book(appdir):
    account = AuthStore(appdir / AUTH_FILENAME, FileSecretBackend()).get('paper')
    data_dir = config_mod.account_data_dir(appdir, account)
    return PaperBookStore(data_dir / PAPER_BOOK_FILENAME).load()


def _login_paper(capsys, *extra):
    return _run(capsys, 'auth', 'login', '--paper', '--exchange', 'binance', '--no-testnet', *extra)


# --- login + seeding ----------------------------------------------------------

def test_login_paper_creates_credential_free_account_and_seeds_book(paper_env, capsys):
    appdir, _ = paper_env
    code, out = _login_paper(capsys, '--paper-capital', '5000')
    assert code == int(ExitCode.OK)
    assert 'paper' in out

    account = AuthStore(appdir / AUTH_FILENAME, FileSecretBackend()).get('paper')
    assert account.paper is True
    assert account.api_key is None and account.api_secret is None
    assert _book(appdir).balances == {'USDT': 5000.0}


def test_paper_status_reports_simulated_balance(paper_env, capsys):
    appdir, _ = paper_env
    _login_paper(capsys, '--paper-capital', '500')
    _run(capsys, 'pair', 'add', 'BTC/USDT', '--account', 'paper', '--target', '80/20',
         '--band', '5', '--min-notional', '10')
    code, out = _run(capsys, 'status', '--account', 'paper', '--json')
    assert code == int(ExitCode.OK)
    payload = json.loads(out)
    # Simulated all-stable book: 500 USDT, no BTC yet.
    pair = payload['pairs'][0]
    assert pair['current_volatile_pct'] == 0.0


# --- full rehearsal: plan -> rebalance -> orders -> reconcile ------------------

def test_paper_rehearsal_books_a_fill_once_price_crosses(paper_env, capsys):
    appdir, market = paper_env
    _login_paper(capsys, '--paper-capital', '500')
    _run(capsys, 'pair', 'add', 'BTC/USDT', '--account', 'paper', '--target', '80/20',
         '--band', '5', '--min-notional', '10')

    # plan -> a BUY toward 80% volatile + a confirm token.
    _, plan_out = _run(capsys, 'plan', '--account', 'paper', '--json')
    plan = json.loads(plan_out)
    token = plan['confirm_token']
    assert token and plan['pairs'][0]['proposed_order']['side'] == 'buy'

    # rebalance places the maker limit (@ bid 99); market last is 100 -> it rests.
    code, _ = _run(capsys, 'rebalance', '--account', 'paper', '--execute', '--confirm', token)
    assert code == int(ExitCode.OK)
    _, orders_out = _run(capsys, 'orders', '--account', 'paper', '--json')
    assert len(json.loads(orders_out)['orders']) == 1        # resting, not yet filled
    assert _book(appdir).balances.get('BTC', 0.0) == 0.0     # nothing booked on submission

    # Price drops to the limit -> reconcile books the fill exactly once.
    market.tickers['BTC/USDT'] = {'last': 98.0, 'bid': 97.0, 'ask': 99.0}
    _run(capsys, 'reconcile', '--account', 'paper')
    book = _book(appdir)
    assert book.balances['BTC'] == pytest.approx(4.0)         # 400 quote / 100 price
    assert book.balances['USDT'] == pytest.approx(500.0 - 4.0 * 99.0)  # filled at the 99 limit
    assert _run(capsys, 'orders', '--account', 'paper', '--json')[1]  # order now terminal


# --- reset --------------------------------------------------------------------

def test_paper_reset_reseeds_the_book(paper_env, capsys):
    appdir, _ = paper_env
    _login_paper(capsys, '--paper-capital', '500')
    code, out = _run(capsys, 'paper', 'reset', '--account', 'paper', '--paper-capital', '20000')
    assert code == int(ExitCode.OK)
    assert _book(appdir).balances == {'USDT': 20000.0}


def test_paper_reset_on_non_paper_account_errors(auth_env, capsys, monkeypatch):
    monkeypatch.setenv(ENV_AUTH_BACKEND, 'file')
    _run(capsys, 'auth', 'login', '--no-verify', '--account', 'real', '--exchange', 'bybit',
         '--key', 'K', '--secret', 'S')
    code, _ = _run(capsys, 'paper', 'reset', '--account', 'real')
    assert code == int(ExitCode.CONFIG_ERROR)


@pytest.fixture
def auth_env(appdir, monkeypatch):
    monkeypatch.setenv(ENV_AUTH_BACKEND, 'file')
    return appdir
