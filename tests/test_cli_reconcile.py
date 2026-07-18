'''Phase 22 (F-6) tests: the `reconcile` command end to end.

Books actual fills for outstanding orders against exchange status. The exchange is
faked; the order store is pre-seeded under the account data dir.
'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import (
    ENV_API_KEY,
    ENV_API_SECRET,
    KILL_SWITCH_FILENAME,
    LEDGER_FILENAME,
    OPEN_ORDERS_FILENAME,
    PORTFOLIO_FILENAME,
    ExitCode,
)
from ccbalancer.enums.order_status import OrderStatus
from ccbalancer.models import OpenOrder, PairConfig
from ccbalancer.stores.ledger_store import LedgerStore
from ccbalancer.stores.order_store import OrderStore
from ccbalancer.stores.portfolio_store import PortfolioStore

from .conftest import FakeExchangeStore

_NOW = '2026-07-19T00:00:00Z'


def _setup(appdir, data_dir, monkeypatch, *, order_status=None) -> FakeExchangeStore:
    exchange = FakeExchangeStore(
        markets={'BTC/USDT': {'active': True}},
        tickers={'BTC/USDT': {'last': 100.0, 'bid': 99.0, 'ask': 101.0}},
        order_status=order_status or {},
    )
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0))
    monkeypatch.setenv(ENV_API_KEY, 'trade-key-1234')
    monkeypatch.setenv(ENV_API_SECRET, 'trade-secret-5678')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)
    return exchange


def _seed_order(data_dir, **kw) -> None:
    base = dict(
        client_order_id='ccb-1', order_id='X1', symbol='BTC/USDT', side='buy',
        amount=1.0, limit_price=100.0, status=OrderStatus.OPEN, filled_booked=0.0, placed_at=_NOW,
    )
    base.update(kw)
    OrderStore(data_dir / OPEN_ORDERS_FILENAME).put(OpenOrder(**base))


def _json(argv, capsys, expect=ExitCode.OK) -> dict:
    code = cli.main(argv)
    assert code == int(expect), capsys.readouterr()
    return json.loads(capsys.readouterr().out)


def test_reconcile_books_a_real_fill(appdir, data_dir, monkeypatch, capsys):
    _setup(appdir, data_dir, monkeypatch,
           order_status={'X1': {'id': 'X1', 'status': 'closed', 'filled': 1.0, 'average': 99.0}})
    _seed_order(data_dir)

    payload = _json(['reconcile', '--json'], capsys)

    assert payload['command'] == 'reconcile'
    assert payload['reconciled'][0]['newly_filled'] == 1.0
    assert payload['reconciled'][0]['status'] == 'closed'
    fills = LedgerStore(data_dir / LEDGER_FILENAME).load()
    assert len(fills) == 1 and fills[0]['qty'] == 1.0 and fills[0]['price'] == 99.0
    assert OrderStore(data_dir / OPEN_ORDERS_FILENAME).list() == []  # terminal -> dropped


def test_reconcile_nothing_tracked_is_ok(appdir, data_dir, monkeypatch, capsys):
    _setup(appdir, data_dir, monkeypatch)
    payload = _json(['reconcile', '--json'], capsys)
    assert payload['reconciled'] == []


def test_reconcile_filters_by_pair(appdir, data_dir, monkeypatch, capsys):
    _setup(appdir, data_dir, monkeypatch, order_status={
        'X1': {'id': 'X1', 'status': 'closed', 'filled': 1.0, 'average': 99.0},
        'X2': {'id': 'X2', 'status': 'closed', 'filled': 2.0, 'average': 50.0},
    })
    _seed_order(data_dir)
    _seed_order(data_dir, client_order_id='ccb-2', order_id='X2', symbol='ETH/USDT', amount=2.0)

    payload = _json(['reconcile', '--pair', 'BTC/USDT', '--json'], capsys)

    assert [r['symbol'] for r in payload['reconciled']] == ['BTC/USDT']
    assert OrderStore(data_dir / OPEN_ORDERS_FILENAME).get('ccb-2') is not None


def test_reconcile_not_blocked_by_kill_switch(appdir, data_dir, monkeypatch, capsys):
    _setup(appdir, data_dir, monkeypatch,
           order_status={'X1': {'id': 'X1', 'status': 'closed', 'filled': 1.0, 'average': 99.0}})
    _seed_order(data_dir)
    (appdir / KILL_SWITCH_FILENAME).write_text('', encoding='utf-8')  # STOP present

    payload = _json(['reconcile', '--json'], capsys)  # must still run (books, places nothing)

    assert payload['reconciled'][0]['newly_filled'] == 1.0
