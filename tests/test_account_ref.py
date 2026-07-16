'''ExchangeStore.account_ref(): tiered exchange-account-id capture (I-8).'''

from __future__ import annotations

import hashlib

import ccxt

from ccbalancer.stores.exchange import ExchangeStore


class _RefClient:
    '''Minimal ccxt-client stand-in for the account-ref lookup.'''

    def __init__(self, *, accounts=None, bybit_uid=None):
        self._accounts = accounts
        self._bybit_uid = bybit_uid

    def fetch_accounts(self):
        if self._accounts is None:
            raise ccxt.NotSupported('fetch_accounts unsupported')
        return self._accounts

    def privateGetV5UserQueryApi(self):  # noqa: N802 - mirrors ccxt's implicit method
        if self._bybit_uid is None:
            raise ccxt.BaseError('no uid')
        return {'result': {'userID': self._bybit_uid}}


def _hashed(material: str) -> str:
    return hashlib.sha256(material.encode()).hexdigest()[:32]


def _store(exchange_id: str, client: object) -> ExchangeStore:
    store = ExchangeStore(exchange_id, testnet=False)
    store._client = client
    return store


def test_account_ref_okx_via_unified_fetch_accounts():
    store = _store('okx', _RefClient(accounts=[{'id': '12345'}]))
    assert store.account_ref() == _hashed('okx:12345')


def test_account_ref_bybit_via_tier2_endpoint():
    # fetch_accounts is unsupported on Bybit → falls through to the private endpoint.
    store = _store('bybit', _RefClient(accounts=None, bybit_uid='99887766'))
    assert store.account_ref() == _hashed('bybit:99887766')


def test_account_ref_none_when_unobtainable():
    store = _store('bybit', _RefClient(accounts=None, bybit_uid=None))
    assert store.account_ref() is None


def test_account_ref_namespaced_by_exchange():
    # Same raw uid on two venues must not collide.
    okx = _store('okx', _RefClient(accounts=[{'id': '1'}])).account_ref()
    binance_like = _hashed('binance:1')
    assert okx != binance_like
