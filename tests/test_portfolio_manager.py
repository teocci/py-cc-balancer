'''Phase 5 tests: per-pair snapshot assembly from balances, tickers, and state.'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import ExchangeError
from ccbalancer.managers.portfolio_manager import PortfolioManager
from ccbalancer.models import PairConfig, RebalanceState
from ccbalancer.stores.state_store import StateStore

from .conftest import FakeExchangeStore


@pytest.fixture
def state_store(tmp_path):
    return StateStore(tmp_path / 'state.json', tmp_path / 'history.jsonl')


def _pair(symbol: str = 'BTC/USDT') -> PairConfig:
    return PairConfig(symbol, 80.0, 20.0, 5.0, 10.0)


def _state(symbol: str = 'BTC/USDT', at: str = '2026-06-18T12:00:00Z') -> RebalanceState:
    return RebalanceState(symbol, at, 'sell', 0.5, 50000.0, 3.2, 'OK')


def test_snapshot_carries_balances_and_prices(fake_exchange, state_store):
    manager = PortfolioManager(fake_exchange, state_store)
    snap = manager.snapshot(_pair())
    assert snap.base_total == 1.0
    assert snap.base_free == 1.0
    assert snap.stable_total == 5000.0
    assert snap.price == 50000.0
    assert snap.bid == 49990.0
    assert snap.ask == 50010.0


def test_snapshot_injects_last_rebalance_at(fake_exchange, state_store):
    state_store.save(_state())
    manager = PortfolioManager(fake_exchange, state_store)
    snap = manager.snapshot(_pair())
    assert snap.last_rebalance_at == '2026-06-18T12:00:00Z'


def test_snapshot_last_rebalance_at_none_when_unset(fake_exchange, state_store):
    manager = PortfolioManager(fake_exchange, state_store)
    assert manager.snapshot(_pair()).last_rebalance_at is None


def test_snapshot_missing_asset_defaults_to_zero(state_store):
    exchange = FakeExchangeStore(
        balance={'free': {}, 'used': {}, 'total': {}},
        tickers={'BTC/USDT': {'last': 50000.0, 'bid': 49990.0, 'ask': 50010.0}},
    )
    snap = PortfolioManager(exchange, state_store).snapshot(_pair())
    assert snap.base_total == 0.0
    assert snap.stable_free == 0.0


def test_snapshot_bid_ask_fall_back_to_last(state_store):
    exchange = FakeExchangeStore(tickers={'BTC/USDT': {'last': 50000.0}})
    snap = PortfolioManager(exchange, state_store).snapshot(_pair())
    assert snap.bid == 50000.0
    assert snap.ask == 50000.0


def test_snapshot_amount_precision_from_decimal_places(state_store):
    exchange = FakeExchangeStore(tickers={'BTC/USDT': {'last': 50000.0}})
    market = {'active': True, 'precision': {'amount': 3}}
    snap = PortfolioManager(exchange, state_store).snapshot(_pair(), market=market)
    assert snap.amount_precision == 3
    assert snap.market_active is True


def test_snapshot_amount_precision_from_tick_size(state_store):
    exchange = FakeExchangeStore(tickers={'BTC/USDT': {'last': 50000.0}})
    market = {'active': False, 'precision': {'amount': 0.001}}
    snap = PortfolioManager(exchange, state_store).snapshot(_pair(), market=market)
    assert snap.amount_precision == 3
    assert snap.market_active is False


def test_snapshot_defaults_when_market_unknown(fake_exchange, state_store):
    snap = PortfolioManager(fake_exchange, state_store).snapshot(_pair())
    assert snap.amount_precision is None
    assert snap.market_active is True


def test_snapshot_unknown_ticker_raises(fake_exchange, state_store):
    manager = PortfolioManager(fake_exchange, state_store)
    with pytest.raises(ExchangeError):
        manager.snapshot(_pair('ETH/USDT'))


def test_snapshots_batches_balance_and_markets(state_store):
    exchange = FakeExchangeStore(
        markets={'BTC/USDT': {'active': True, 'precision': {'amount': 2}}},
        balance={'free': {'BTC': 2.0}, 'used': {}, 'total': {'BTC': 2.0}},
        tickers={'BTC/USDT': {'last': 50000.0}},
    )
    snaps = PortfolioManager(exchange, state_store).snapshots([_pair()])
    assert len(snaps) == 1
    assert snaps[0].amount_precision == 2
    assert exchange.markets_loaded == 1
