'''CLI tests for the `auth` command group (run via :func:`cli.main`).'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import (
    AUTH_FILENAME,
    ENV_API_KEY,
    ENV_API_SECRET,
    ENV_AUTH_BACKEND,
    ENV_PASSPHRASE,
    ExitCode,
)
from ccbalancer.stores.auth_store import AuthStore, FileSecretBackend

from .conftest import FakeExchangeStore


def _stored(auth_env, name):
    '''Read a stored account back from the isolated file-backed auth.json.'''
    return AuthStore(auth_env / AUTH_FILENAME, FileSecretBackend()).get(name)


def _login_bybit(capsys, *extra):
    '''Verified bybit login (ref captured from the injected fake exchange).'''
    return _run(capsys, 'auth', 'login', '--account', 'bybit', '--exchange', 'bybit',
                '--no-testnet', '--key', 'K1', '--secret', 'S1', *extra)


@pytest.fixture
def auth_env(appdir, monkeypatch):
    '''Isolated app dir with the file secret backend forced (no real keyring).'''
    monkeypatch.setenv(ENV_AUTH_BACKEND, 'file')
    return appdir


def _run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _login(capsys, *extra: str) -> tuple[int, str]:
    return _run(capsys, 'auth', 'login', '--no-verify', *extra)


# --- login --------------------------------------------------------------------

def test_login_with_key_secret(auth_env, capsys):
    code, out = _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K1', '--secret', 'S1')
    assert code == int(ExitCode.OK)
    assert 'bybit-main' in out
    _, listing = _run(capsys, 'auth', 'list', '--json')
    data = json.loads(listing)
    assert data['active'] == 'bybit-main'
    assert data['accounts'][0]['api_secret'] != 'S1'  # masked


def test_login_testnet_defaults_to_sandbox(auth_env, capsys):
    _login(capsys, '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['testnet'] is True


def test_login_honors_ccb_testnet_env(auth_env, monkeypatch, capsys):
    monkeypatch.setenv('CCB_TESTNET', 'false')
    _login(capsys, '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['testnet'] is False


def test_login_no_testnet_flag_overrides_env(auth_env, monkeypatch, capsys):
    monkeypatch.setenv('CCB_TESTNET', 'true')
    _login(capsys, '--no-testnet', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['testnet'] is False


def test_login_name_defaults_to_exchange(auth_env, capsys):
    _login(capsys, '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['name'] == 'okx'


def test_login_unsupported_exchange_errors(auth_env, capsys):
    code, _ = _login(capsys, '--exchange', 'kraken', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.CONFIG_ERROR)


def test_login_from_env(auth_env, monkeypatch, capsys):
    monkeypatch.setenv(ENV_API_KEY, 'envkey1234')
    monkeypatch.setenv(ENV_API_SECRET, 'envsecret1234')
    code, _ = _login(capsys, '--exchange', 'bybit', '--from-env')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['api_key'] is not None


def test_login_interactive_prompts(auth_env, monkeypatch, capsys):
    answers = iter(['IKEY1234', 'ISECRET1234', 'IPHRASE'])
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt='': next(answers))
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(cli, 'requires_passphrase', lambda exchange: True)
    code, _ = _login(capsys, '--exchange', 'okx')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['password'] is not None


def test_login_non_interactive_without_creds_errors(auth_env, monkeypatch, capsys):
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: False)
    code, _ = _login(capsys, '--exchange', 'bybit')
    assert code == int(ExitCode.CONFIG_ERROR)


def test_login_okx_with_flags_prompts_passphrase(auth_env, monkeypatch, capsys):
    '''Key+secret flags on OKX must still collect the required passphrase.'''
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt='': 'PROMPTEDPHRASE')
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: True)
    code, _ = _login(capsys, '--exchange', 'okx', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['password'] is not None


def test_login_okx_non_interactive_without_passphrase_errors(auth_env, monkeypatch, capsys):
    '''A complete key+secret pair is still incomplete for OKX without a passphrase.'''
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: False)
    code, _ = _login(capsys, '--exchange', 'okx', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.CONFIG_ERROR)


def test_non_interactive_error_names_passphrase_env():
    '''The non-interactive guard names the actual gap (passphrase, not key/secret).'''
    err = cli._non_interactive_error('okx', 'K', 'S', needs_password=True)
    assert 'passphrase' in str(err).lower()
    assert 'CCB_PASSPHRASE' in str(err)


def test_login_okx_from_env_imports_passphrase(auth_env, monkeypatch, capsys):
    monkeypatch.setenv(ENV_API_KEY, 'envkey1234')
    monkeypatch.setenv(ENV_API_SECRET, 'envsecret1234')
    monkeypatch.setenv(ENV_PASSPHRASE, 'envphrase1234')
    code, _ = _login(capsys, '--exchange', 'okx', '--from-env')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['password'] is not None


def test_login_bybit_with_flags_skips_passphrase_prompt(auth_env, monkeypatch, capsys):
    '''Venues that need no passphrase must not prompt or error on key+secret alone.'''
    def _boom(prompt: str = '') -> str:
        raise AssertionError('getpass should not be called for bybit')

    monkeypatch.setattr(cli.getpass, 'getpass', _boom)
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: False)
    code, _ = _login(capsys, '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['password'] is None


def test_login_failed_check_hints_testnet(auth_env, monkeypatch, capsys):
    '''A failed credential check on a testnet account explains the likely cause.'''
    monkeypatch.setattr(cli, '_account_exchange_store', lambda account: FakeExchangeStore(offline=True))
    code, out = _run(capsys, 'auth', 'login', '--account', 'bybit-main',
                     '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.EXCHANGE_ERROR)
    assert 'testnet' in out and '--no-testnet' in out


# --- login verification -------------------------------------------------------

def test_login_verify_success(auth_env, monkeypatch, capsys, fake_exchange):
    monkeypatch.setattr(cli, '_account_exchange_store', lambda account: fake_exchange)
    code, out = _run(capsys, 'auth', 'login', '--account', 'bybit-main',
                     '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.OK)
    assert 'verified' in out


def test_login_verify_failure_keeps_account(auth_env, monkeypatch, capsys):
    offline = FakeExchangeStore(offline=True)
    monkeypatch.setattr(cli, '_account_exchange_store', lambda account: offline)
    code, _ = _run(capsys, 'auth', 'login', '--account', 'okx', '--exchange', 'okx',
                   '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    assert code == int(ExitCode.EXCHANGE_ERROR)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['accounts'][0]['name'] == 'okx'  # saved despite failure


# --- list / use / logout ------------------------------------------------------

def test_list_marks_active(auth_env, capsys):
    _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--account', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    _, out = _run(capsys, 'auth', 'list')
    active_line = next(line for line in out.splitlines() if line.startswith('*'))
    assert 'bybit-main' in active_line


def test_use_switches_active(auth_env, capsys):
    _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--account', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    code, _ = _run(capsys, 'auth', 'use', 'okx')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['active'] == 'okx'


def test_use_unknown_errors(auth_env, capsys):
    code, _ = _run(capsys, 'auth', 'use', 'ghost')
    assert code == int(ExitCode.CONFIG_ERROR)


def test_logout_defaults_to_active(auth_env, capsys):
    _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--account', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    code, _ = _run(capsys, 'auth', 'logout')  # active is bybit-main (first added)
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    data = json.loads(listing)
    assert data['active'] == 'okx'
    assert [p['name'] for p in data['accounts']] == ['okx']


# --- status / whoami ----------------------------------------------------------

def test_status_online_valid(auth_env, monkeypatch, capsys, fake_exchange):
    _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    monkeypatch.setattr(cli, '_account_exchange_store', lambda account: fake_exchange)
    _, out = _run(capsys, 'auth', 'status', '--json')
    assert json.loads(out)['valid'] is True


def test_status_offline_is_null(auth_env, monkeypatch, capsys):
    _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    monkeypatch.setattr(cli, '_account_exchange_store', lambda account: FakeExchangeStore(offline=True))
    code, out = _run(capsys, 'auth', 'status', '--json')
    assert code == int(ExitCode.OK)
    assert json.loads(out)['valid'] is None


def test_whoami_no_active(auth_env, capsys):
    code, out = _run(capsys, 'auth', 'whoami')
    assert code == int(ExitCode.OK)
    assert 'No active account' in out


# --- secret hygiene -----------------------------------------------------------

def test_secret_never_in_stdout(auth_env, monkeypatch, capsys, fake_exchange):
    secret = 'SUPERSECRETVALUE'
    _login(capsys, '--account', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', secret, '--passphrase', 'PASSPHRASEVAL')
    monkeypatch.setattr(cli, '_account_exchange_store', lambda account: fake_exchange)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    _, status = _run(capsys, 'auth', 'status', '--json')
    _, whoami = _run(capsys, 'auth', 'whoami', '--json')
    assert secret not in listing + status + whoami
    assert 'PASSPHRASEVAL' not in listing + status + whoami


def test_account_flag_threads_through_config_show(auth_env, capsys):
    _login(capsys, '--account', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--account', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    _, out = _run(capsys, 'config', 'show', '--account', 'okx', '--json')
    assert json.loads(out)['config']['account'] == 'okx'


# --- account identity: ref capture, rotation guard, rename (I-8) ---------------

def test_login_captures_account_ref(auth_env, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_account_exchange_store', lambda a: FakeExchangeStore(account_ref='ref-A'))
    code, _ = _login_bybit(capsys)
    assert code == int(ExitCode.OK)
    assert _stored(auth_env, 'bybit').account_ref == 'ref-A'


def test_rotation_same_ref_keeps_id(auth_env, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_account_exchange_store', lambda a: FakeExchangeStore(account_ref='ref-A'))
    _login_bybit(capsys)
    first_id = _stored(auth_env, 'bybit').id
    _login_bybit(capsys, '--key', 'K2', '--secret', 'S2')  # rotate, same real account
    rotated = _stored(auth_env, 'bybit')
    assert rotated.id == first_id and rotated.api_key == 'K2'


def test_rotation_different_ref_is_refused(auth_env, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_account_exchange_store', lambda a: FakeExchangeStore(account_ref='ref-A'))
    _login_bybit(capsys)
    first_id = _stored(auth_env, 'bybit').id
    # New key resolves to a *different* exchange account → refused, nothing written.
    monkeypatch.setattr(cli, '_account_exchange_store', lambda a: FakeExchangeStore(account_ref='ref-B'))
    code, _ = _login_bybit(capsys, '--key', 'K2', '--secret', 'S2')
    assert code == int(ExitCode.CONFIG_ERROR)
    unchanged = _stored(auth_env, 'bybit')
    assert unchanged.id == first_id and unchanged.account_ref == 'ref-A' and unchanged.api_key == 'K1'


def test_rotation_different_ref_with_force_repoints(auth_env, monkeypatch, capsys):
    monkeypatch.setattr(cli, '_account_exchange_store', lambda a: FakeExchangeStore(account_ref='ref-A'))
    _login_bybit(capsys)
    first_id = _stored(auth_env, 'bybit').id
    monkeypatch.setattr(cli, '_account_exchange_store', lambda a: FakeExchangeStore(account_ref='ref-B'))
    code, _ = _login_bybit(capsys, '--key', 'K2', '--secret', 'S2', '--force')
    assert code == int(ExitCode.OK)
    repointed = _stored(auth_env, 'bybit')
    assert repointed.id == first_id and repointed.account_ref == 'ref-B' and repointed.api_key == 'K2'


def test_auth_rename_preserves_id_and_moves_active(auth_env, capsys):
    _login(capsys, '--account', 'bybit', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    original_id = _stored(auth_env, 'bybit').id
    code, _ = _run(capsys, 'auth', 'rename', 'bybit', 'bybit-main')
    assert code == int(ExitCode.OK)
    assert _stored(auth_env, 'bybit') is None
    renamed = _stored(auth_env, 'bybit-main')
    assert renamed is not None and renamed.id == original_id
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['active'] == 'bybit-main'


def test_auth_rename_to_existing_errors(auth_env, capsys):
    _login(capsys, '--account', 'bybit', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--account', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    code, _ = _run(capsys, 'auth', 'rename', 'bybit', 'okx')
    assert code == int(ExitCode.CONFIG_ERROR)
