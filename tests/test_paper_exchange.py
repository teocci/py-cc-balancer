'''I-18 tests: the paper (simulated-exchange) backend and its persistent book.

The book store round-trips balances/orders to disk; the exchange store mirrors the
real ExchangeStore surface but simulates balances/orders against a live public
ticker (a FakeExchangeStore stands in for market data). Fills are reconcile-driven:
create_order rests a maker limit, fetch_order fills it once the ticker crosses,
booking the balance change exactly once.
'''

from __future__ import annotations

import pytest

from ccbalancer.enums.side import OrderSide
from ccbalancer.exceptions import ExchangeError, InsufficientBalanceError, StateError
from ccbalancer.stores.paper_book import ORDER_CLOSED, ORDER_OPEN, PaperBook, PaperBookStore, PaperOrder
from ccbalancer.stores.paper_exchange import PaperExchangeStore


def _ticker(last: float) -> dict[str, object]:
    return {'last': last, 'bid': last, 'ask': last}


class _MarketData:
    '''Minimal live-market stand-in: a programmable BTC/USDT ticker.'''

    exchange_id = 'binance'

    def __init__(self, last: float = 100.0) -> None:
        self.last = last

    def fetch_ticker(self, symbol: str) -> dict[str, object]:
        return _ticker(self.last)

    def load_markets(self, reload: bool = False) -> dict[str, object]:
        return {'BTC/USDT': {'active': True}}


def _paper(tmp_path, *, capital: float = 10000.0, last: float = 100.0, fee_rate: float = 0.0):
    store = PaperBookStore(tmp_path / 'paper_book.json')
    store.seed('USDT', capital)
    market = _MarketData(last)
    return PaperExchangeStore(store, market, fee_rate=fee_rate), store, market


# --- book store persistence ---------------------------------------------------

def test_book_seed_and_load_round_trip(tmp_path):
    store = PaperBookStore(tmp_path / 'b.json')
    assert store.exists() is False
    store.seed('USDT', 5000.0)
    assert store.exists() is True

    book = store.load()
    assert book.balances == {'USDT': 5000.0}
    assert book.orders == [] and book.next_id == 1


def test_book_persists_orders_and_balances(tmp_path):
    store = PaperBookStore(tmp_path / 'b.json')
    book = PaperBook(balances={'USDT': 100.0, 'BTC': 1.5}, next_id=3)
    book.orders.append(PaperOrder('paper-2', 'ccb-x', 'BTC/USDT', 'buy', 0.5, 100.0))
    store.save(book)

    reloaded = store.load()
    assert reloaded.balances == {'USDT': 100.0, 'BTC': 1.5}
    assert reloaded.next_id == 3
    assert reloaded.orders[0].client_order_id == 'ccb-x'
    assert reloaded.orders[0].status == ORDER_OPEN


def test_book_malformed_file_raises_state_error(tmp_path):
    path = tmp_path / 'b.json'
    path.write_text('{not json', encoding='utf-8')
    with pytest.raises(StateError, match='Cannot read paper book'):
        PaperBookStore(path).load()


def test_locked_reserves_quote_for_buy_and_base_for_sell():
    book = PaperBook(balances={'USDT': 1000.0, 'BTC': 2.0})
    book.orders.append(PaperOrder('paper-1', None, 'BTC/USDT', 'buy', 3.0, 100.0))
    book.orders.append(PaperOrder('paper-2', None, 'BTC/USDT', 'sell', 0.5, 120.0))
    assert book.locked() == {'USDT': 300.0, 'BTC': 0.5}


# --- exchange surface: balances + resting orders ------------------------------

def test_fetch_balance_reserves_open_order_funds(tmp_path):
    paper, _, _ = _paper(tmp_path, capital=10000.0)
    paper.create_order('BTC/USDT', OrderSide.BUY, 20.0, 100.0)  # reserves 2000 quote
    balance = paper.fetch_balance()
    assert balance['total']['USDT'] == 10000.0
    assert balance['used']['USDT'] == 2000.0
    assert balance['free']['USDT'] == 8000.0


def test_create_order_rests_open_and_is_findable(tmp_path):
    paper, _, _ = _paper(tmp_path)
    order = paper.create_order('BTC/USDT', OrderSide.BUY, 10.0, 100.0, client_order_id='ccb-1')
    assert order['status'] == ORDER_OPEN and order['filled'] == 0.0
    assert paper.fetch_open_orders('BTC/USDT')[0]['id'] == order['id']
    assert paper.find_order_by_client_id('ccb-1')['id'] == order['id']


def test_create_order_insufficient_funds_raises(tmp_path):
    paper, _, _ = _paper(tmp_path, capital=100.0)
    with pytest.raises(InsufficientBalanceError):
        paper.create_order('BTC/USDT', OrderSide.BUY, 10.0, 100.0)  # needs 1000, have 100


# --- reconcile-driven fills ---------------------------------------------------

def test_buy_fills_when_price_crosses_and_books_once(tmp_path):
    paper, store, market = _paper(tmp_path, capital=10000.0, last=100.0, fee_rate=0.001)
    order = paper.create_order('BTC/USDT', OrderSide.BUY, 20.0, 100.0)

    # Price still at 100 (== limit) -> a BUY at 100 crosses (price <= limit).
    filled = paper.fetch_order(order['id'])
    assert filled['status'] == ORDER_CLOSED
    assert filled['filled'] == 20.0 and filled['average'] == 100.0
    assert filled['fee'] == {'cost': pytest.approx(2.0), 'currency': 'USDT'}

    book = store.load()
    assert book.balances['BTC'] == pytest.approx(20.0)
    assert book.balances['USDT'] == pytest.approx(10000.0 - 2000.0 - 2.0)

    # Idempotent: a second fetch does not re-apply the fill.
    again = paper.fetch_order(order['id'])
    assert again['status'] == ORDER_CLOSED
    assert store.load().balances['BTC'] == pytest.approx(20.0)


def test_buy_rests_until_price_drops_to_limit(tmp_path):
    paper, _, market = _paper(tmp_path, last=105.0)
    order = paper.create_order('BTC/USDT', OrderSide.BUY, 10.0, 100.0)
    # Market above the BUY limit -> rests.
    assert paper.fetch_order(order['id'])['status'] == ORDER_OPEN
    # Price drops to the limit -> fills.
    market.last = 99.0
    assert paper.fetch_order(order['id'])['status'] == ORDER_CLOSED


def test_sell_fills_when_price_rises_to_limit(tmp_path):
    paper, store, market = _paper(tmp_path, capital=0.0, last=100.0, fee_rate=0.0)
    # Seed some base to sell.
    book = store.load(); book.balances['BTC'] = 5.0; store.save(book)
    order = paper.create_order('BTC/USDT', OrderSide.SELL, 5.0, 110.0)
    assert paper.fetch_order(order['id'])['status'] == ORDER_OPEN  # 100 < 110, rests
    market.last = 111.0
    filled = paper.fetch_order(order['id'])
    assert filled['status'] == ORDER_CLOSED
    assert store.load().balances['USDT'] == pytest.approx(550.0)   # 5 * 110
    assert store.load().balances['BTC'] == pytest.approx(0.0)


def test_cancel_frees_reserved_funds(tmp_path):
    paper, _, _ = _paper(tmp_path, capital=10000.0)
    order = paper.create_order('BTC/USDT', OrderSide.BUY, 20.0, 100.0)
    assert paper.fetch_balance()['free']['USDT'] == 8000.0
    result = paper.cancel_order(order['id'], 'BTC/USDT')
    assert result['status'] == 'canceled'
    assert paper.fetch_open_orders() == []
    assert paper.fetch_balance()['free']['USDT'] == 10000.0


def test_fetch_unknown_order_raises(tmp_path):
    paper, _, _ = _paper(tmp_path)
    with pytest.raises(ExchangeError, match='No paper order'):
        paper.fetch_order('paper-999')


def test_market_data_is_delegated(tmp_path):
    paper, _, _ = _paper(tmp_path)
    assert paper.exchange_id == 'binance'
    assert paper.load_markets() == {'BTC/USDT': {'active': True}}
    assert paper.check_credentials() is None
    assert paper.account_ref() is None
