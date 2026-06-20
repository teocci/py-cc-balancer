'''Auth profile store: `gh`-style multi-account credentials.

Persists profile metadata and the active-profile pointer to ``auth.json`` and
keeps secrets either inline in that file (the ``file`` backend, best-effort 0600)
or in the OS keyring (the ``keyring`` backend, metadata-only JSON). The store is
the only writer of ``auth.json`` and the single place profile-name slugs are
validated. It never imports :mod:`ccbalancer.config` so the dependency stays a
DAG (config depends on this module, not the other way around).
'''

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ccbalancer import constants as c
from ccbalancer.exceptions import AuthError
from ccbalancer.models.auth_profile import AuthProfile

__all__ = [
    'AuthStore',
    'SecretBackend',
    'FileSecretBackend',
    'KeyringSecretBackend',
    'make_secret_backend',
    'backend_for',
    'normalize_profile_name',
]

_AUTH_SCHEMA_VERSION = 1
# Alphanumeric segments joined by single hyphens: no leading/trailing/double hyphen.
_SLUG_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
_SECRET_SUFFIXES = ('key', 'secret', 'password')


def normalize_profile_name(raw: str) -> str:
    '''Normalize and validate a profile name to a lowercase slug.

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
            f'Invalid profile name {raw!r}; use a slug: lowercase letters, digits, '
            'and single hyphens (e.g. bybit-main)'
        )
    return name


class SecretBackend(Protocol):
    '''Maps between a profile and its persisted ``auth.json`` entry.

    The backend owns where secrets live: ``persist`` writes any side-stored
    secrets and returns the JSON entry; ``hydrate`` rebuilds a full profile from
    an entry; ``forget`` drops side-stored secrets when a profile is removed.
    '''

    name: str

    def persist(self, profile: AuthProfile) -> dict[str, object]: ...

    def hydrate(self, entry: dict[str, object]) -> AuthProfile: ...

    def forget(self, name: str) -> None: ...


@dataclass(slots=True)
class FileSecretBackend:
    '''Stores credentials inline in ``auth.json`` (best-effort 0600 perms).'''

    name: str = 'file'

    def persist(self, profile: AuthProfile) -> dict[str, object]:
        '''Return a JSON entry carrying the secrets inline.'''
        return {
            'name': profile.name,
            'exchange': profile.exchange,
            'testnet': profile.testnet,
            'api_key': profile.api_key,
            'api_secret': profile.api_secret,
            'password': profile.password,
        }

    def hydrate(self, entry: dict[str, object]) -> AuthProfile:
        '''Rebuild a profile, reading the secrets back from the entry.'''
        return _profile_from_meta(
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

    def persist(self, profile: AuthProfile) -> dict[str, object]:
        '''Write the secrets to the keyring and return a metadata-only entry.'''
        keyring = _require_keyring()
        secrets = (profile.api_key, profile.api_secret, profile.password)
        for suffix, value in zip(_SECRET_SUFFIXES, secrets):
            self._store_secret(keyring, profile.name, suffix, value)
        return {'name': profile.name, 'exchange': profile.exchange, 'testnet': profile.testnet}

    def hydrate(self, entry: dict[str, object]) -> AuthProfile:
        '''Rebuild a profile, reading the secrets back from the keyring.'''
        keyring = _require_keyring()
        name = str(entry['name'])
        secrets = [keyring.get_password(self.service, f'{name}:{s}') or None for s in _SECRET_SUFFIXES]
        return _profile_from_meta(entry, api_key=secrets[0], api_secret=secrets[1], password=secrets[2])

    def forget(self, name: str) -> None:
        '''Delete every keyring entry for the profile (absent entries are ignored).'''
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
    '''Reads and writes auth profiles, delegating secret storage to a backend.

    Attributes:
        path: Location of ``auth.json``.
        backend: Secret-storage strategy (file or keyring).
    '''

    path: Path
    backend: SecretBackend

    def load(self) -> list[AuthProfile]:
        '''Return all stored profiles (secrets hydrated from the backend).'''
        return [self.backend.hydrate(entry) for entry in self._read()['profiles']]

    def save(self, profiles: list[AuthProfile]) -> None:
        '''Persist the given profiles, preserving the current active pointer.'''
        self._write(profiles, self._read().get('active'))

    def get(self, name: str) -> AuthProfile | None:
        '''Return the named profile, or ``None`` if it does not exist.'''
        target = normalize_profile_name(name)
        return next((p for p in self.load() if p.name == target), None)

    def add_or_update(self, profile: AuthProfile) -> None:
        '''Insert or replace a profile; the first profile added becomes active.'''
        data = self._read()
        kept = [self.backend.hydrate(e) for e in data['profiles'] if e['name'] != profile.name]
        kept.append(profile)
        self._write(kept, data.get('active') or profile.name)

    def remove(self, name: str) -> None:
        '''Delete a profile, re-pointing active to the first remaining one.

        Raises:
            AuthError: If the profile does not exist.
        '''
        target = normalize_profile_name(name)
        data = self._read()
        if target not in {e['name'] for e in data['profiles']}:
            raise AuthError(f'Profile {target!r} not found')
        kept = [self.backend.hydrate(e) for e in data['profiles'] if e['name'] != target]
        self.backend.forget(target)
        active = data.get('active')
        if active == target:
            active = kept[0].name if kept else None
        self._write(kept, active)

    def active_name(self) -> str | None:
        '''Return the active profile name, or ``None`` if none is set.'''
        return self._read().get('active')

    def set_active(self, name: str) -> None:
        '''Make the named profile active.

        Raises:
            AuthError: If the profile does not exist.
        '''
        target = normalize_profile_name(name)
        data = self._read()
        if target not in {e['name'] for e in data['profiles']}:
            raise AuthError(f'Profile {target!r} not found; run `ccbalancer auth list`')
        self._write([self.backend.hydrate(e) for e in data['profiles']], target)

    def _read(self) -> dict[str, object]:
        if not self.path.is_file():
            return {'schema_version': _AUTH_SCHEMA_VERSION, 'backend': self.backend.name,
                    'active': None, 'profiles': []}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthError(f'Cannot read auth file {self.path}: {exc}') from exc
        if not isinstance(data, dict) or not isinstance(data.get('profiles'), list):
            raise AuthError(f'Malformed auth file {self.path}')
        return data

    def _write(self, profiles: list[AuthProfile], active: str | None) -> None:
        payload = {
            'schema_version': _AUTH_SCHEMA_VERSION,
            'backend': self.backend.name,
            'active': active,
            'profiles': [self.backend.persist(profile) for profile in profiles],
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

    A profile must be read with the backend it was written with, so an existing
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


def _profile_from_meta(
    entry: dict[str, object],
    api_key: object,
    api_secret: object,
    password: object,
) -> AuthProfile:
    return AuthProfile(
        name=str(entry['name']),
        exchange=str(entry['exchange']),
        testnet=bool(entry['testnet']),
        api_key=api_key if api_key is None else str(api_key),
        api_secret=api_secret if api_secret is None else str(api_secret),
        password=password if password is None else str(password),
    )


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
