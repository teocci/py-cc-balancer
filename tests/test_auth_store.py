'''Tests for the auth profile store, secret backends, and slug validation.'''

from __future__ import annotations

import json

import pytest

from ccbalancer.exceptions import AuthError
from ccbalancer.models.auth_profile import AuthProfile
from ccbalancer.stores.auth_store import (
    AuthStore,
    FileSecretBackend,
    KeyringSecretBackend,
    make_secret_backend,
    normalize_profile_name,
)


def _profile(name: str = 'bybit-main', exchange: str = 'bybit', **kw) -> AuthProfile:
    base = {'api_key': 'k' + name, 'api_secret': 's' + name, 'password': None}
    base.update(kw)
    return AuthProfile(name=name, exchange=exchange, testnet=True, **base)


def _file_store(tmp_path) -> AuthStore:
    return AuthStore(tmp_path / 'auth.json', FileSecretBackend())


# --- slug normalization -------------------------------------------------------

@pytest.mark.parametrize('raw,expected', [
    ('OKX', 'okx'),
    ('okx', 'okx'),
    ('  Bybit-Main  ', 'bybit-main'),
    ('binance2', 'binance2'),
])
def test_normalize_profile_name_valid(raw, expected):
    assert normalize_profile_name(raw) == expected


@pytest.mark.parametrize('raw', ['my profile', 'OKX!', '-okx', 'okx-', 'a--b', '', 'présent'])
def test_normalize_profile_name_invalid(raw):
    with pytest.raises(AuthError):
        normalize_profile_name(raw)


# --- file backend round-trip --------------------------------------------------

def test_load_empty_when_absent(tmp_path):
    assert _file_store(tmp_path).load() == []


def test_add_then_get_round_trip(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile())
    loaded = store.get('BYBIT-MAIN')
    assert loaded is not None
    assert loaded.api_key == 'kbybit-main'
    assert loaded.api_secret == 'sbybit-main'


def test_first_profile_becomes_active(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile('bybit-main'))
    store.add_or_update(_profile('okx', exchange='okx', password='pass'))
    assert store.active_name() == 'bybit-main'


def test_add_or_update_replaces_existing(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile('okx', exchange='okx'))
    store.add_or_update(_profile('okx', exchange='okx', api_key='rotated'))
    profiles = store.load()
    assert len(profiles) == 1
    assert profiles[0].api_key == 'rotated'


def test_set_active_unknown_raises(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile('okx', exchange='okx'))
    with pytest.raises(AuthError):
        store.set_active('does-not-exist')


def test_remove_repoints_active(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile('bybit-main'))
    store.add_or_update(_profile('okx', exchange='okx'))
    assert store.active_name() == 'bybit-main'
    store.remove('bybit-main')
    assert store.active_name() == 'okx'


def test_remove_last_clears_active(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile('okx', exchange='okx'))
    store.remove('okx')
    assert store.active_name() is None
    assert store.load() == []


def test_remove_unknown_raises(tmp_path):
    with pytest.raises(AuthError):
        _file_store(tmp_path).remove('ghost')


def test_atomic_write_leaves_no_tmp(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile())
    assert not (tmp_path / 'auth.json.tmp').exists()
    assert (tmp_path / 'auth.json').is_file()


def test_malformed_file_raises(tmp_path):
    path = tmp_path / 'auth.json'
    path.write_text('not json', encoding='utf-8')
    with pytest.raises(AuthError):
        AuthStore(path, FileSecretBackend()).load()


def test_file_backend_persists_secrets_inline(tmp_path):
    store = _file_store(tmp_path)
    store.add_or_update(_profile('okx', exchange='okx', password='phrase'))
    raw = json.loads((tmp_path / 'auth.json').read_text(encoding='utf-8'))
    entry = raw['profiles'][0]
    assert entry['api_secret'] == 'sokx'
    assert entry['password'] == 'phrase'


# --- keyring backend ----------------------------------------------------------

def test_keyring_backend_keeps_secrets_out_of_json(tmp_path, fake_keyring):
    store = AuthStore(tmp_path / 'auth.json', KeyringSecretBackend())
    store.add_or_update(_profile('okx', exchange='okx', password='phrase'))
    raw = (tmp_path / 'auth.json').read_text(encoding='utf-8')
    assert 'sokx' not in raw
    assert 'phrase' not in raw
    assert fake_keyring.get_password('ccbalancer', 'okx:secret') == 'sokx'
    assert fake_keyring.get_password('ccbalancer', 'okx:password') == 'phrase'


def test_keyring_backend_hydrates_secrets(tmp_path, fake_keyring):
    store = AuthStore(tmp_path / 'auth.json', KeyringSecretBackend())
    store.add_or_update(_profile('okx', exchange='okx', password='phrase'))
    loaded = store.get('okx')
    assert loaded.api_key == 'kokx'
    assert loaded.password == 'phrase'


def test_keyring_backend_forget_on_remove(tmp_path, fake_keyring):
    store = AuthStore(tmp_path / 'auth.json', KeyringSecretBackend())
    store.add_or_update(_profile('okx', exchange='okx'))
    store.remove('okx')
    assert fake_keyring.get_password('ccbalancer', 'okx:key') is None


def test_keyring_backend_without_package_raises(tmp_path, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'keyring', None)  # force ImportError
    store = AuthStore(tmp_path / 'auth.json', KeyringSecretBackend())
    with pytest.raises(AuthError):
        store.add_or_update(_profile('okx', exchange='okx'))


# --- backend factory ----------------------------------------------------------

def test_make_secret_backend_file():
    assert make_secret_backend('file').name == 'file'


def test_make_secret_backend_unknown_raises():
    with pytest.raises(AuthError):
        make_secret_backend('vault')


def test_make_secret_backend_keyring_falls_back_without_backend(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'keyring', None)  # no keyring installed
    assert make_secret_backend('keyring').name == 'file'
