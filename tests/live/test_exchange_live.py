'''Live, read-only smoke tests against Bybit mainnet.

Unlike the mocked suite in ``tests/test_exchange.py``, these exercise the real
ccxt network code in :mod:`ccbalancer.stores.exchange` end-to-end. They are gated
behind the ``live`` marker (deselected by default) and run with ``pytest -m live``.

Public reads (markets, ticker) need no credentials. Credentialed reads (balance,
open orders) read mainnet keys from the environment and skip when absent. Nothing
here ever places or cancels an order.
'''

from __future__ import annotations

import os

import pytest

from ccbalancer.constants import ENV_API_KEY, ENV_API_SECRET
from ccbalancer.stores.exchange import ExchangeStore

pytestmark = pytest.mark.live

# Standard Bybit spot symbol; present on mainnet with deep, stable liquidity.
SYMBOL = 'BTC/USDT'
EXCHANGE = 'bybit'


@pytest.fixture(scope='module')
def public_store() -> ExchangeStore:
    '''A keyless mainnet store; the lazy client and markets cache across tests.'''
    return ExchangeStore(EXCHANGE, testnet=False)


@pytest.fixture(scope='module')
def credentialed_store() -> ExchangeStore:
    '''A mainnet store built from env credentials; skips when keys are absent.'''
    api_key = os.getenv(ENV_API_KEY)
    api_secret = os.getenv(ENV_API_SECRET)
    if not api_key or not api_secret:
        pytest.skip(f'set {ENV_API_KEY} and {ENV_API_SECRET} to run credentialed live tests')
    return ExchangeStore(EXCHANGE, testnet=False, api_key=api_key, api_secret=api_secret)


def test_load_markets_returns_known_symbol(public_store: ExchangeStore):
    markets = public_store.load_markets()

    assert isinstance(markets, dict) and markets
    assert SYMBOL in markets


def test_fetch_ticker_returns_positive_price(public_store: ExchangeStore):
    ticker = public_store.fetch_ticker(SYMBOL)

    assert ticker['last'] is not None and float(ticker['last']) > 0
    bid, ask = ticker.get('bid'), ticker.get('ask')
    if bid is not None and ask is not None:
        assert float(bid) <= float(ask)


def test_fetch_balance_has_total_structure(credentialed_store: ExchangeStore):
    balance = credentialed_store.fetch_balance()

    assert isinstance(balance, dict)
    assert isinstance(balance.get('total'), dict)


def test_fetch_open_orders_returns_list(credentialed_store: ExchangeStore):
    orders = credentialed_store.fetch_open_orders(SYMBOL)

    assert isinstance(orders, list)
