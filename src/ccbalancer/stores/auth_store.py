'''Auth account store: `gh`-style multi-account credentials.

Persists account metadata and the active-account pointer to ``auth.json`` and
keeps secrets either inline in that file (the ``file`` backend, best-effort 0600)
or in the OS keyring (the ``keyring`` backend, metadata-only JSON). The store is
the only writer of ``auth.json`` and the single place account-name slugs are
validated. It never imports :mod:`ccbalancer.config` so the dependency stays a
DAG (config depends on this module, not the other way around).
'''

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from ccbalancer import constants as c
from ccbalancer.exceptions import AuthError
from ccbalancer.models.account import Account

__all__ = [
    'AuthStore',
    'SecretBackend',
    'FileSecretBackend',
    'KeyringSecretBackend',
    'make_secret_backend',
    'backend_for',
    'normalize_account_name',
]

_AUTH_SCHEMA_VERSION = 1
# Alphanumeric segments joined by single hyphens: no leading/trailing/double hyphen.
_SLUG_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
_SECRET_SUFFIXES = ('key', 'secret', 'password')


def normalize_account_name(raw: str) -> str:
    '''Normalize and validate an account name to a lowercase slug.

    Args:
        raw: The user-supplied name (any case).

    Returns:
        The normalized lowercase slug.

    Raises:
        AuthError: If the name is empty or not a valid slug.
    '''
    name = (raw or '').strip().lower()
    if not _SLUG_PATTERN.fullmatch(name):
        raise AuthError(
            f'Invalid account name {raw!r}; use a slug: lowercase letters, digits, '
            'and single hyphens (e.g. bybit-main)'
        )
    return name


class SecretBackend(Protocol):
    '''Maps between an account and its persisted ``auth.json`` entry.

    The backend owns where secrets live: ``persist`` writes any side-stored
    secrets and returns the JSON entry; ``hydrate`` rebuilds a full account from
    an entry; ``forget`` drops side-stored secrets when an account is removed.
    '''

    name: str

    def persist(self, account: Account) -> dict[str, object]: ...

    def hydrate(self, entry: dict[str, object]) -> Account: ...

    def forget(self, name: str) -> None: ...


@dataclass(slots=True)
class FileSecretBackend:
    '''Stores credentials inline in ``auth.json`` (best-effort 0600 perms).'''

    name: str = 'file'

    def persist(self, account: Account) -> dict[str, object]:
        '''Return a JSON entry carrying the secrets inline.'''
        return {
            'name': account.name,
            'id': account.id,
            'account_ref': account.account_ref,
            'exchange': account.exchange,
            'testnet': account.testnet,
            'api_key': account.api_key,
            'api_secret': account.api_secret,
            'password': account.password,
        }

    def hydrate(self, entry: dict[str, object]) -> Account:
        '''Rebuild an account, reading the secrets back from the entry.'''
        return _account_from_meta(
            entry,
            api_key=entry.get('api_key'),
            api_secret=entry.get('api_secret'),
            password=entry.get('password'),
        )

    def forget(self, name: str) -> None:
        '''No-op: inline secrets vanish when the entry is dropped.'''


@dataclass(slots=True)
class KeyringSecretBackend:
    '''Stores credentials in the OS keyring; ``auth.json`` holds metadata only.'''

    name: str = 'keyring'
    service: str = c.AUTH_KEYRING_SERVICE

    def persist(self, account: Account) -> dict[str, object]:
        '''Write the secrets to the keyring and return a metadata-only entry.'''
        keyring = _require_keyring()
        creds = (account.api_key, account.api_secret, account.password)
        for suffix, value in zip(_SECRET_SUFFIXES, creds):
            self._store_secret(keyring, account.name, suffix, value)
        return {
            'name': account.name,
            'id': account.id,
            'account_ref': account.account_ref,
            'exchange': account.exchange,
            'testnet': account.testnet,
        }

    def hydrate(self, entry: dict[str, object]) -> Account:
        '''Rebuild an account, reading the secrets back from the keyring.'''
        keyring = _require_keyring()
        name = str(entry['name'])
        creds = [keyring.get_password(self.service, f'{name}:{s}') or None for s in _SECRET_SUFFIXES]
        return _account_from_meta(entry, api_key=creds[0], api_secret=creds[1], password=creds[2])

    def forget(self, name: str) -> None:
        '''Delete every keyring entry for the account (absent entries are ignored).'''
        keyring = _require_keyring()
        for suffix in _SECRET_SUFFIXES:
            try:
                keyring.delete_password(self.service, f'{name}:{suffix}')
            except keyring.errors.PasswordDeleteError:
                pass

    def _store_secret(self, keyring: object, name: str, suffix: str, value: str | None) -> None:
        if value:
            keyring.set_password(self.service, f'{name}:{suffix}', value)
        else:
            try:
                keyring.delete_password(self.service, f'{name}:{suffix}')
            except keyring.errors.PasswordDeleteError:
                pass


@dataclass(slots=True)
class AuthStore:
    '''Reads and writes auth accounts, delegating secret storage to a backend.

    Attributes:
        path: Location of ``auth.json``.
        backend: Secret-storage strategy (file or keyring).
    '''

    path: Path
    backend: SecretBackend

    def load(self) -> list[Account]:
        '''Return all stored accounts (secrets hydrated from the backend).'''
        return [self.backend.hydrate(entry) for entry in self._read()['accounts']]

    def save(self, accounts: list[Account]) -> None:
        '''Persist the given accounts, preserving the current active pointer.'''
        self._write(accounts, self._read().get('active'))

    def get(self, name: str) -> Account | None:
        '''Return the named account, or ``None`` if it does not exist.'''
        target = normalize_account_name(name)
        return next((p for p in self.load() if p.name == target), None)

    def add_or_update(self, account: Account) -> None:
        '''Insert or replace an account; the first account added becomes active.

        A new account is assigned a stable id; replacing an existing account by
        name preserves its id (and thus its data dir) when the caller passes none.
        '''
        data = self._read()
        existing = next((e for e in data['accounts'] if e['name'] == account.name), None)
        if account.id is None:
            account = replace(account, id=(existing.get('id') if existing else None) or _mint_id())
        kept = [self.backend.hydrate(e) for e in data['accounts'] if e['name'] != account.name]
        kept.append(account)
        self._write(kept, data.get('active') or account.name)

    def remove(self, name: str) -> None:
        '''Delete an account, re-pointing active to the first remaining one.

        Raises:
            AuthError: If the account does not exist.
        '''
        target = normalize_account_name(name)
        data = self._read()
        if target not in {e['name'] for e in data['accounts']}:
            raise AuthError(f'Account {target!r} not found')
        kept = [self.backend.hydrate(e) for e in data['accounts'] if e['name'] != target]
        self.backend.forget(target)
        active = data.get('active')
        if active == target:
            active = kept[0].name if kept else None
        self._write(kept, active)

    def active_name(self) -> str | None:
        '''Return the active account name, or ``None`` if none is set.'''
        return self._read().get('active')

    def set_active(self, name: str) -> None:
        '''Make the named account active.

        Raises:
            AuthError: If the account does not exist.
        '''
        target = normalize_account_name(name)
        data = self._read()
        if target not in {e['name'] for e in data['accounts']}:
            raise AuthError(f'Account {target!r} not found; run `ccbalancer auth list`')
        self._write([self.backend.hydrate(e) for e in data['accounts']], target)

    def rename(self, old: str, new: str) -> str:
        '''Rename an account, keeping its id and moving its secrets to the new name.

        The account's stable id (and thus its data directory) is unchanged, so the
        rename never strands the account's book.

        Raises:
            AuthError: If ``old`` does not exist or ``new`` already exists.
        '''
        old_name = normalize_account_name(old)
        new_name = normalize_account_name(new)
        data = self._read()
        names = {e['name'] for e in data['accounts']}
        if old_name not in names:
            raise AuthError(f'Account {old_name!r} not found; run `ccbalancer auth list`')
        if new_name != old_name and new_name in names:
            raise AuthError(f'Account {new_name!r} already exists')
        accounts = [self.backend.hydrate(e) for e in data['accounts']]
        renamed = [replace(a, name=new_name) if a.name == old_name else a for a in accounts]
        active = data.get('active')
        self._write(renamed, new_name if active == old_name else active)
        if new_name != old_name:
            self.backend.forget(old_name)  # drop stale secrets under the old name (file: no-op)
        return new_name

    def ensure_ids(self) -> bool:
        '''Assign a stable id to any account lacking one (one-time id migration).

        Metadata-only: secrets are re-persisted under their unchanged name, so the
        OS keyring is not disturbed. Returns ``True`` if any id was assigned.
        '''
        data = self._read()
        entries = data['accounts']
        if not entries or all(entry.get('id') for entry in entries):
            return False
        accounts = [self.backend.hydrate(entry) for entry in entries]
        migrated = [account if account.id else replace(account, id=_mint_id()) for account in accounts]
        self._write(migrated, data.get('active'))
        return True

    def _read(self) -> dict[str, object]:
        if not self.path.is_file():
            return {'schema_version': _AUTH_SCHEMA_VERSION, 'backend': self.backend.name,
                    'active': None, 'accounts': []}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthError(f'Cannot read auth file {self.path}: {exc}') from exc
        if not isinstance(data, dict):
            raise AuthError(f'Malformed auth file {self.path}')
        # Back-compat: pre-0.2.0 files keyed the list under 'profiles'.
        if 'accounts' not in data and isinstance(data.get('profiles'), list):
            data['accounts'] = data.pop('profiles')
        if not isinstance(data.get('accounts'), list):
            raise AuthError(f'Malformed auth file {self.path}')
        return data

    def _write(self, accounts: list[Account], active: str | None) -> None:
        payload = {
            'schema_version': _AUTH_SCHEMA_VERSION,
            'backend': self.backend.name,
            'active': active,
            'accounts': [self.backend.persist(account) for account in accounts],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        tmp.replace(self.path)
        _restrict_permissions(self.path)


def make_secret_backend(prefer: str | None = None) -> SecretBackend:
    '''Resolve the secret backend from ``prefer``, env, or the default.

    A ``keyring`` choice falls back to the file backend when no usable keyring is
    available (e.g. headless CI), so credentials still persist.

    Raises:
        AuthError: If the requested backend name is unknown.
    '''
    choice = (prefer or os.getenv(c.ENV_AUTH_BACKEND) or c.DEFAULT_AUTH_BACKEND).lower()
    if choice == 'file':
        return FileSecretBackend()
    if choice == 'keyring':
        return KeyringSecretBackend() if _keyring_available() else FileSecretBackend()
    raise AuthError(f'Unknown auth backend {choice!r}; choose file or keyring')


def backend_for(path: Path, prefer: str | None = None) -> SecretBackend:
    '''Pick the backend for ``path``, honoring the one recorded in an existing file.

    A account must be read with the backend it was written with, so an existing
    ``auth.json`` records its backend and that choice wins over ``prefer``/default.
    For a fresh file, ``prefer`` (then env, then default) decides.
    '''
    return make_secret_backend(_recorded_backend(path) or prefer)


def _recorded_backend(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    backend = data.get('backend') if isinstance(data, dict) else None
    return backend if backend in ('file', 'keyring') else None


def _account_from_meta(
    entry: dict[str, object],
    api_key: object,
    api_secret: object,
    password: object,
) -> Account:
    return Account(
        name=str(entry['name']),
        exchange=str(entry['exchange']),
        testnet=bool(entry['testnet']),
        api_key=api_key if api_key is None else str(api_key),
        api_secret=api_secret if api_secret is None else str(api_secret),
        password=password if password is None else str(password),
        id=str(entry['id']) if entry.get('id') else None,
        account_ref=str(entry['account_ref']) if entry.get('account_ref') else None,
    )


def _mint_id() -> str:
    '''Return a fresh opaque account id (an immutable local handle).'''
    return secrets.token_hex(6)


def _require_keyring() -> object:
    try:
        import keyring
    except ImportError as exc:
        raise AuthError('keyring backend requested but the keyring package is not installed') from exc
    return keyring


def _keyring_available() -> bool:
    try:
        import keyring
        from keyring.backends import fail
    except ImportError:
        return False
    try:
        return not isinstance(keyring.get_keyring(), fail.Keyring)
    except keyring.errors.KeyringError:
        return False


def _restrict_permissions(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        # Best-effort on platforms without POSIX permissions (e.g. Windows).
        pass
