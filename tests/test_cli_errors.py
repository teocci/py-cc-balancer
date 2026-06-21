'''Phase 13 tests: forced-error paths map to the documented exit codes.

These drive ``cli.main`` end to end through the ``_exchange_store`` seam and assert
the process exit codes from DESIGN.md: ``3`` exchange/network, ``4`` order rejected,
``5`` partial failure (some orders placed, some rejected).
'''

from __future__ import annotations

from ccbalancer import cli
from ccbalancer.constants import (
    CONFIG_FILENAME,
    ENV_API_KEY,
    ENV_API_SECRET,
    PORTFOLIO_FILENAME,
    ExitCode,
)
from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import OrderRejectedError
from ccbalancer.models import PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore

from .conftest import FakeExchangeStore


class _RejectingExchange(FakeExchangeStore):
    '''Places ``fail_after`` orders successfully, then rejects every further one.'''

    def __init__(self, *, fail_after: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._fail_after = fail_after

    def create_order(self, symbol, side, amount, price, client_order_id=None):
        if len(self.created) >= self._fail_after:
            raise OrderRejectedError(f'rejected {symbol}')
        return super().create_order(symbol, side, amount, price, client_order_id)


def _wire(appdir, monkeypatch, exchange: FakeExchangeStore, *, cap: float = 1_000_000.0) -> None:
    appdir.mkdir(parents=True, exist_ok=True)
    (appdir / CONFIG_FILENAME).write_text(
        f'[safety]\nmax_session_notional_usd = {cap}\n', encoding='utf-8'
    )
    monkeypatch.setenv(ENV_API_KEY, 'trade-key-1234')
    monkeypatch.setenv(ENV_API_SECRET, 'trade-secret-5678')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: exchange)


def _add_sell_pair(appdir, symbol: str) -> None:
    PortfolioStore(appdir / PORTFOLIO_FILENAME).add(PairConfig(symbol, 80.0, 20.0, 5.0, 10.0))


def _token(capsys) -> str:
    cli.main(['rebalance', '--json'])
    import json

    return json.loads(capsys.readouterr().out)['confirm_token']


# --- exit 3: an exchange/network failure on a read --------------------------


def test_offline_read_exits_exchange_error(appdir, monkeypatch, capsys):
    _add_sell_pair(appdir, 'BTC/USDT')
    monkeypatch.setattr(cli, '_exchange_store', lambda config: FakeExchangeStore(offline=True))

    code = cli.main(['status', '--json'])

    assert code == int(ExitCode.EXCHANGE_ERROR)


# --- exit 4: the sole order is rejected -------------------------------------


def test_rejected_order_exits_order_rejected(appdir, monkeypatch, capsys):
    exchange = _RejectingExchange(
        fail_after=0,
        markets={'BTC/USDT': {'active': True}},
        balance={'free': {'BTC': 1.0, 'USDT': 5000.0}, 'total': {'BTC': 1.0, 'USDT': 5000.0}},
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
    _add_sell_pair(appdir, 'BTC/USDT')
    _wire(appdir, monkeypatch, exchange)
    token = _token(capsys)

    code = cli.main(['rebalance', '--execute', '--confirm', token, '--json'])

    assert code == int(ExitCode.ORDER_REJECTED)
    assert exchange.created == []  # nothing placed


# --- exit 5: one order placed, one rejected ---------------------------------


def test_partial_failure_exits_partial(appdir, monkeypatch, capsys):
    exchange = _RejectingExchange(
        fail_after=1,  # first pair places, second is rejected
        markets={'BTC/USDT': {'active': True}, 'ETH/USDT': {'active': True}},
        balance={
            'free': {'BTC': 1.0, 'ETH': 10.0, 'USDT': 5000.0},
            'total': {'BTC': 1.0, 'ETH': 10.0, 'USDT': 5000.0},
        },
        tickers={
            'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0},
            'ETH/USDT': {'last': 3000.0, 'bid': 2999.0, 'ask': 3001.0},
        },
    )
    _add_sell_pair(appdir, 'BTC/USDT')
    _add_sell_pair(appdir, 'ETH/USDT')
    _wire(appdir, monkeypatch, exchange)
    token = _token(capsys)

    code = cli.main(['rebalance', '--execute', '--confirm', token, '--json'])

    assert code == int(ExitCode.PARTIAL_FAILURE)
    assert len(exchange.created) == 1  # exactly one placement landed
