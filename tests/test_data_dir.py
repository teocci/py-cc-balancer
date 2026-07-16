'''Per-account data directories and the legacy-book migration (F-5 / I-8).'''

from __future__ import annotations

from ccbalancer import config as config_mod
from ccbalancer.constants import (
    ACCOUNTS_DIRNAME,
    AUTH_FILENAME,
    DECISION_LOG_FILENAME,
    DEFAULT_ACCOUNT_SCOPE,
    LEDGER_FILENAME,
    PORTFOLIO_FILENAME,
    STATE_FILENAME,
)
from ccbalancer.models.account import Account
from ccbalancer.stores.auth_store import AuthStore, FileSecretBackend

_BOOKS = (PORTFOLIO_FILENAME, STATE_FILENAME, LEDGER_FILENAME, DECISION_LOG_FILENAME)


def _store(appdir) -> AuthStore:
    return AuthStore(appdir / AUTH_FILENAME, FileSecretBackend())


def _seed_root_books(appdir) -> None:
    appdir.mkdir(parents=True, exist_ok=True)
    for name in _BOOKS:
        (appdir / name).write_text('{}', encoding='utf-8')


def test_no_account_uses_default_scope(appdir):
    config = config_mod.load_config(auth_store=_store(appdir))
    assert config.data_dir == appdir / ACCOUNTS_DIRNAME / DEFAULT_ACCOUNT_SCOPE
    assert config.data_dir != config.app_dir  # OHLCV / config stay at the root


def test_account_scopes_data_dir_by_id(appdir):
    store = _store(appdir)
    store.add_or_update(Account('bybit', 'bybit', False, 'k', 's'))
    account_id = store.get('bybit').id
    config = config_mod.load_config(auth_store=store)
    assert config.data_dir == appdir / ACCOUNTS_DIRNAME / account_id


def test_two_accounts_get_separate_dirs(appdir):
    store = _store(appdir)
    store.add_or_update(Account('bybit', 'bybit', False, 'k', 's'))
    store.add_or_update(Account('okx', 'okx', False, 'k', 's'))
    dir_a = config_mod.load_config(account_override='bybit', auth_store=store).data_dir
    dir_b = config_mod.load_config(account_override='okx', auth_store=store).data_dir
    assert dir_a != dir_b


def test_legacy_books_migrate_to_active_account(appdir):
    store = _store(appdir)
    store.add_or_update(Account('bybit', 'bybit', False, 'k', 's'))  # active
    _seed_root_books(appdir)
    config = config_mod.load_config(auth_store=store)
    for name in _BOOKS:
        assert (config.data_dir / name).is_file(), name
        assert not (appdir / name).exists(), f'{name} left at root'
    # idempotent: a second load moves nothing new and does not duplicate
    config_mod.load_config(auth_store=store)
    assert sorted(p.name for p in config.data_dir.iterdir()) == sorted(_BOOKS)


def test_legacy_books_without_account_go_to_default(appdir):
    _seed_root_books(appdir)
    config = config_mod.load_config(auth_store=_store(appdir))
    assert config.data_dir.name == DEFAULT_ACCOUNT_SCOPE
    for name in _BOOKS:
        assert (config.data_dir / name).is_file(), name


def test_legacy_books_migrate_to_selected_account_not_active(appdir):
    # A --account selection must own the migrated book (the dir the command reads),
    # never the unrelated active pointer.
    store = _store(appdir)
    store.add_or_update(Account('bybit', 'bybit', False, 'k', 's'))  # active
    store.add_or_update(Account('okx', 'okx', False, 'k', 's'))
    _seed_root_books(appdir)
    config = config_mod.load_config(account_override='okx', auth_store=store)
    assert config.data_dir == appdir / ACCOUNTS_DIRNAME / store.get('okx').id
    for name in _BOOKS:
        assert (config.data_dir / name).is_file(), name
        assert not (appdir / name).exists(), f'{name} left at root'


def test_partial_scoped_book_does_not_strand_root_books(appdir):
    # A single pre-scoped book must not block the remaining root books from migrating.
    store = _store(appdir)
    store.add_or_update(Account('bybit', 'bybit', False, 'k', 's'))
    data_dir = appdir / ACCOUNTS_DIRNAME / store.get('bybit').id
    data_dir.mkdir(parents=True)
    (data_dir / PORTFOLIO_FILENAME).write_text('{"scoped": true}', encoding='utf-8')
    _seed_root_books(appdir)
    config = config_mod.load_config(auth_store=store)
    # the pre-scoped book is authoritative (never clobbered)...
    assert (config.data_dir / PORTFOLIO_FILENAME).read_text(encoding='utf-8') == '{"scoped": true}'
    # ...and the siblings still migrate rather than being orphaned at the root
    for name in (STATE_FILENAME, LEDGER_FILENAME, DECISION_LOG_FILENAME):
        assert (config.data_dir / name).is_file(), name
        assert not (appdir / name).exists(), f'{name} left at root'
