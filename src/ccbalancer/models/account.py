'''Auth account: one named exchange-account credential set.

An account bundles the credentials and target venue for a single exchange account
(`gh`-style). Accounts are stored in ``auth.json`` and managed via the ``auth``
CLI commands. The account name is a slug, normalized and validated by the auth
store (see :func:`ccbalancer.stores.auth_store.normalize_account_name`).
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['Account']


@dataclass(slots=True)
class Account:
    '''Credentials and venue for one exchange account.

    Attributes:
        name: Lowercase slug identifying the account (e.g. ``'bybit-main'``).
        exchange: ccxt exchange id the credentials belong to.
        testnet: Whether this account targets the exchange sandbox.
        api_key: API key, or ``None`` until hydrated from the keyring.
        api_secret: API secret, or ``None`` until hydrated from the keyring.
        password: Passphrase for venues that require one (e.g. OKX), else ``None``.
        id: Opaque immutable local handle minted once at first save; keys the
            account's per-account data directory. Stable across rename and
            credential rotation. ``None`` until assigned by the store.
        account_ref: Best-effort hashed exchange account id captured online at
            login; used to recognize the same real account across logout/re-login
            and to guard credential rotation. ``None`` when uncaptured.
        paper: Whether this is a paper (simulated-exchange) account. A paper
            account needs no credentials; ``exchange`` names the real venue whose
            public market data drives its simulated book.
    '''

    name: str
    exchange: str
    testnet: bool
    api_key: str | None = None
    api_secret: str | None = None
    password: str | None = None
    id: str | None = None
    account_ref: str | None = None
    paper: bool = False
