'''Auth profile: one named exchange-account credential set.

A profile bundles the credentials and target venue for a single exchange account
(`gh`-style). Profiles are stored in ``auth.json`` and managed via the ``auth``
CLI commands. The profile name is a slug, normalized and validated by the auth
store (see :func:`ccbalancer.stores.auth_store.normalize_profile_name`).
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['AuthProfile']


@dataclass(slots=True)
class AuthProfile:
    '''Credentials and venue for one exchange account.

    Attributes:
        name: Lowercase slug identifying the profile (e.g. ``'bybit-main'``).
        exchange: ccxt exchange id the credentials belong to.
        testnet: Whether this account targets the exchange sandbox.
        api_key: API key, or ``None`` until hydrated from the keyring.
        api_secret: API secret, or ``None`` until hydrated from the keyring.
        password: Passphrase for venues that require one (e.g. OKX), else ``None``.
    '''

    name: str
    exchange: str
    testnet: bool
    api_key: str | None = None
    api_secret: str | None = None
    password: str | None = None
