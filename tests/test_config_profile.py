'''Tests for credential and profile resolution in :func:`config.load_config`.'''

from __future__ import annotations

import pytest

from ccbalancer import config as config_mod
from ccbalancer.constants import ENV_API_KEY, ENV_API_SECRET, ENV_PROFILE, ENV_TESTNET
from ccbalancer.exceptions import AuthError, ConfigError
from ccbalancer.models.auth_profile import AuthProfile
from ccbalancer.stores.auth_store import AuthStore, FileSecretBackend


def _store(appdir) -> AuthStore:
    return AuthStore(appdir / 'auth.json', FileSecretBackend())


def _add(store, name='bybit-main', exchange='bybit', testnet=True, key='K', secret='S', password=None):
    store.add_or_update(AuthProfile(name, exchange, testnet, key, secret, password))


def _load(store, **kw):
    return config_mod.load_config(auth_store=store, **kw)


def test_no_profile_uses_legacy_env(appdir, monkeypatch):
    monkeypatch.setenv(ENV_API_KEY, 'env-key')
    monkeypatch.setenv(ENV_API_SECRET, 'env-secret')
    config = _load(_store(appdir))
    assert config.profile is None
    assert config.api_key == 'env-key'
    assert config.api_secret == 'env-secret'


def test_no_profile_no_env_requires_credentials_raises(appdir):
    config = _load(_store(appdir))
    assert config.api_key is None
    with pytest.raises(ConfigError):
        config_mod.require_credentials(config)


def test_active_profile_supplies_creds_and_exchange(appdir):
    store = _store(appdir)
    _add(store, name='okx', exchange='okx', key='ok-key', secret='ok-secret', password='phrase')
    config = _load(store)
    assert config.profile == 'okx'
    assert config.exchange == 'okx'
    assert config.api_key == 'ok-key'
    assert config.password == 'phrase'


def test_profile_override_beats_active(appdir):
    store = _store(appdir)
    _add(store, name='bybit-main', exchange='bybit')  # active (first added)
    _add(store, name='okx', exchange='okx', key='ok')
    config = _load(store, profile_override='okx')
    assert config.profile == 'okx'
    assert config.api_key == 'ok'


def test_env_profile_selects(appdir, monkeypatch):
    store = _store(appdir)
    _add(store, name='bybit-main', exchange='bybit')
    _add(store, name='okx', exchange='okx', key='ok')
    monkeypatch.setenv(ENV_PROFILE, 'okx')
    config = _load(store)
    assert config.profile == 'okx'


def test_flag_beats_env_profile(appdir, monkeypatch):
    store = _store(appdir)
    _add(store, name='bybit-main', exchange='bybit', key='by')
    _add(store, name='okx', exchange='okx', key='ok')
    monkeypatch.setenv(ENV_PROFILE, 'bybit-main')
    config = _load(store, profile_override='okx')
    assert config.api_key == 'ok'


def test_exchange_override_beats_profile(appdir):
    store = _store(appdir)
    _add(store, name='okx', exchange='okx', key='ok')
    config = _load(store, exchange_override='binance')
    assert config.exchange == 'binance'
    assert config.api_key == 'ok'  # creds still come from the profile


def test_testnet_override_beats_profile(appdir):
    store = _store(appdir)
    _add(store, name='okx', exchange='okx', testnet=True)
    config = _load(store, testnet_override=False)
    assert config.testnet is False


def test_testnet_from_profile_outranks_env(appdir, monkeypatch):
    store = _store(appdir)
    _add(store, name='okx', exchange='okx', testnet=False)
    monkeypatch.setenv(ENV_TESTNET, 'true')
    config = _load(store)
    assert config.testnet is False


def test_unknown_profile_raises(appdir):
    with pytest.raises(AuthError):
        _load(_store(appdir), profile_override='ghost')


def test_invalid_slug_profile_override_raises(appdir):
    with pytest.raises(AuthError):
        _load(_store(appdir), profile_override='Bad Name')


def test_case_insensitive_profile_resolution(appdir):
    store = _store(appdir)
    _add(store, name='okx', exchange='okx', key='ok')
    config = _load(store, profile_override='OKX')
    assert config.profile == 'okx'
    assert config.api_key == 'ok'


def test_masked_summary_reports_profile_and_masks_password(appdir):
    store = _store(appdir)
    _add(store, name='okx', exchange='okx', secret='supersecretvalue', password='passphrasevalue')
    summary = config_mod.masked_summary(_load(store))
    assert summary['profile'] == 'okx'
    assert summary['password'] != 'passphrasevalue'
    assert summary['api_secret'] != 'supersecretvalue'
