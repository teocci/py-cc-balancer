'''Phase 11 tests: PerformanceManager cost-basis P&L and portfolio totals.'''

from __future__ import annotations

import pytest

from ccbalancer.managers.performance_manager import (
    PerformanceManager,
    portfolio_totals,
    walk_fills,
)
from ccbalancer.models import Fill, PairConfig
from ccbalancer.stores.ledger_store import LedgerStore

from .conftest import FakeExchangeStore


def _pair(symbol='BTC/USDT', **kwargs) -> PairConfig:
    return PairConfig(symbol, 80.0, 20.0, 5.0, 10.0, **kwargs)


def _fill(side, price, qty, fee=0.0, fee_currency='USDT', symbol='BTC/USDT') -> Fill:
    return Fill(
        ts='2026-06-18T00:00:00Z', symbol=symbol, side=side, price=price,
        qty=qty, fee=fee, fee_currency=fee_currency, order_id=None,
    )


def _ledger(tmp_path, fills) -> LedgerStore:
    store = LedgerStore(tmp_path / 'ledger.jsonl')
    for fill in fills:
        store.append_fill(fill)
    return store


def _exchange(last=55000.0) -> FakeExchangeStore:
    return FakeExchangeStore(tickers={'BTC/USDT': {'last': last}})


# --- scripted reconciliation (DoD) ----------------------------------------


def test_pnl_reconciles_on_scripted_fill_sequence(tmp_path):
    ledger = _ledger(tmp_path, [
        _fill('buy', 50000.0, 1.0, fee=50.0),
        _fill('buy', 30000.0, 1.0, fee=30.0),
        _fill('sell', 60000.0, 1.0, fee=60.0),
    ])
    manager = PerformanceManager(ledger, _exchange(last=55000.0))
    snap = manager.snapshots([_pair()])[0]
    assert snap.position_qty == pytest.approx(1.0)
    assert snap.avg_cost == pytest.approx(40040.0)
    assert snap.cost_basis == pytest.approx(40040.0)
    assert snap.realized_pnl == pytest.approx(19900.0)
    assert snap.unrealized_pnl == pytest.approx(14960.0)
    assert snap.total_pnl == pytest.approx(34860.0)
    assert snap.fees_paid == pytest.approx(140.0)
    assert snap.invested == pytest.approx(80080.0)
    assert snap.roi_pct == pytest.approx(34860.0 / 80080.0 * 100)
    assert snap.fill_count == 3
    assert snap.from_baseline is False


def test_roi_uses_invested_capital_baseline_when_set(tmp_path):
    ledger = _ledger(tmp_path, [_fill('buy', 50000.0, 1.0)])
    manager = PerformanceManager(ledger, _exchange(last=60000.0))
    snap = manager.snapshots([_pair(invested_capital=50000.0)])[0]
    # unrealized = 60000 - 50000 = 10000; roi on pinned 50000 capital = 20%.
    assert snap.unrealized_pnl == pytest.approx(10000.0)
    assert snap.invested == pytest.approx(50000.0)
    assert snap.roi_pct == pytest.approx(20.0)


# --- baselines ------------------------------------------------------------


def test_unrealized_from_baseline_with_empty_ledger(tmp_path):
    ledger = _ledger(tmp_path, [])
    manager = PerformanceManager(ledger, _exchange(last=50000.0))
    pair = _pair(entry_price=40000.0, invested_capital=40000.0)
    snap = manager.snapshots([pair])[0]
    assert snap.from_baseline is True
    assert snap.position_qty == pytest.approx(1.0)
    assert snap.cost_basis == pytest.approx(40000.0)
    assert snap.unrealized_pnl == pytest.approx(10000.0)
    assert snap.realized_pnl == pytest.approx(0.0)
    assert snap.roi_pct == pytest.approx(25.0)
    assert snap.fill_count == 0


def test_empty_ledger_without_baseline_is_flat(tmp_path):
    manager = PerformanceManager(_ledger(tmp_path, []), _exchange())
    snap = manager.snapshots([_pair()])[0]
    assert snap.position_qty == pytest.approx(0.0)
    assert snap.avg_cost is None
    assert snap.total_pnl == pytest.approx(0.0)
    assert snap.roi_pct is None
    assert snap.from_baseline is False


# --- fee normalization ----------------------------------------------------


def test_base_denominated_fee_valued_at_fill_price(tmp_path):
    acc_quote, _ = walk_fills([{'side': 'buy', 'price': 50000.0, 'qty': 1.0, 'fee': 50.0,
                                'fee_currency': 'USDT'}], 'BTC', 'USDT')
    acc_base, _ = walk_fills([{'side': 'buy', 'price': 50000.0, 'qty': 1.0, 'fee': 0.001,
                               'fee_currency': 'BTC'}], 'BTC', 'USDT')
    assert float(acc_quote.fees) == pytest.approx(50.0)
    assert float(acc_base.fees) == pytest.approx(50.0)
    assert float(acc_quote.cost_basis) == pytest.approx(float(acc_base.cost_basis))


# --- realized history (audit) ---------------------------------------------


def test_realized_history_replays_per_symbol_without_network(tmp_path):
    ledger = _ledger(tmp_path, [
        _fill('buy', 50000.0, 1.0, fee=50.0),
        _fill('sell', 60000.0, 1.0, fee=60.0),
    ])
    manager = PerformanceManager(ledger)  # no exchange injected
    records = manager.realized_history()
    assert len(records) == 1
    record = records[0]
    assert record['symbol'] == 'BTC/USDT'
    # realized = (60000 - 60) - (50000 + 50) = -50050 cost vs 59940 proceeds = 9890.
    assert record['realized_pnl'] == pytest.approx(9890.0)
    assert record['fees_paid'] == pytest.approx(110.0)
    assert record['position_qty'] == pytest.approx(0.0)
    assert record['fill_count'] == 2
    assert [t['side'] for t in record['trades']] == ['buy', 'sell']
    assert record['trades'][0]['realized_pnl'] is None
    assert record['trades'][1]['realized_pnl'] == pytest.approx(9890.0)


def test_realized_history_filters_by_symbol(tmp_path):
    ledger = _ledger(tmp_path, [
        _fill('buy', 50000.0, 1.0, symbol='BTC/USDT'),
        _fill('buy', 3000.0, 1.0, symbol='ETH/USDT'),
    ])
    manager = PerformanceManager(ledger)
    records = manager.realized_history({'ETH/USDT'})
    assert [r['symbol'] for r in records] == ['ETH/USDT']


# --- portfolio totals -----------------------------------------------------


def test_portfolio_totals_aggregate_money_and_roi(tmp_path):
    ledger = _ledger(tmp_path, [
        _fill('buy', 50000.0, 1.0, symbol='BTC/USDT'),
        _fill('buy', 2000.0, 1.0, symbol='ETH/USDT'),
    ])
    exchange = FakeExchangeStore(
        tickers={'BTC/USDT': {'last': 60000.0}, 'ETH/USDT': {'last': 2500.0}}
    )
    manager = PerformanceManager(ledger, exchange)
    snaps = manager.snapshots([_pair('BTC/USDT'), _pair('ETH/USDT')])
    totals = portfolio_totals(snaps)
    assert totals['unrealized_pnl'] == pytest.approx(10500.0)  # 10000 + 500
    assert totals['market_value'] == pytest.approx(62500.0)
    assert totals['invested'] == pytest.approx(52000.0)
    assert totals['roi_pct'] == pytest.approx(10500.0 / 52000.0 * 100)


def test_portfolio_totals_empty_is_none_roi():
    totals = portfolio_totals([])
    assert totals['total_pnl'] == pytest.approx(0.0)
    assert totals['roi_pct'] is None
