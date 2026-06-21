'''CLI tests for the `auth` command group (run via :func:`cli.main`).'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.constants import (
    ENV_API_KEY,
    ENV_API_SECRET,
    ENV_AUTH_BACKEND,
    ExitCode,
)

from .conftest import FakeExchangeStore


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
    code, out = _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K1', '--secret', 'S1')
    assert code == int(ExitCode.OK)
    assert 'bybit-main' in out
    _, listing = _run(capsys, 'auth', 'list', '--json')
    data = json.loads(listing)
    assert data['active'] == 'bybit-main'
    assert data['profiles'][0]['api_secret'] != 'S1'  # masked


def test_login_testnet_defaults_to_sandbox(auth_env, capsys):
    _login(capsys, '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['testnet'] is True


def test_login_honors_ccb_testnet_env(auth_env, monkeypatch, capsys):
    monkeypatch.setenv('CCB_TESTNET', 'false')
    _login(capsys, '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['testnet'] is False


def test_login_no_testnet_flag_overrides_env(auth_env, monkeypatch, capsys):
    monkeypatch.setenv('CCB_TESTNET', 'true')
    _login(capsys, '--no-testnet', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['testnet'] is False


def test_login_name_defaults_to_exchange(auth_env, capsys):
    _login(capsys, '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['name'] == 'okx'


def test_login_unsupported_exchange_errors(auth_env, capsys):
    code, _ = _login(capsys, '--exchange', 'kraken', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.CONFIG_ERROR)


def test_login_from_env(auth_env, monkeypatch, capsys):
    monkeypatch.setenv(ENV_API_KEY, 'envkey1234')
    monkeypatch.setenv(ENV_API_SECRET, 'envsecret1234')
    code, _ = _login(capsys, '--exchange', 'bybit', '--from-env')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['api_key'] is not None


def test_login_interactive_prompts(auth_env, monkeypatch, capsys):
    answers = iter(['IKEY1234', 'ISECRET1234', 'IPHRASE'])
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt='': next(answers))
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(cli, 'requires_passphrase', lambda exchange: True)
    code, _ = _login(capsys, '--exchange', 'okx')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['password'] is not None


def test_login_non_interactive_without_creds_errors(auth_env, monkeypatch, capsys):
    monkeypatch.setattr(cli.sys.stdin, 'isatty', lambda: False)
    code, _ = _login(capsys, '--exchange', 'bybit')
    assert code == int(ExitCode.CONFIG_ERROR)


# --- login verification -------------------------------------------------------

def test_login_verify_success(auth_env, monkeypatch, capsys, fake_exchange):
    monkeypatch.setattr(cli, '_profile_exchange_store', lambda profile: fake_exchange)
    code, out = _run(capsys, 'auth', 'login', '--name', 'bybit-main',
                     '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    assert code == int(ExitCode.OK)
    assert 'verified' in out


def test_login_verify_failure_keeps_profile(auth_env, monkeypatch, capsys):
    offline = FakeExchangeStore(offline=True)
    monkeypatch.setattr(cli, '_profile_exchange_store', lambda profile: offline)
    code, _ = _run(capsys, 'auth', 'login', '--name', 'okx', '--exchange', 'okx',
                   '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    assert code == int(ExitCode.EXCHANGE_ERROR)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['profiles'][0]['name'] == 'okx'  # saved despite failure


# --- list / use / logout ------------------------------------------------------

def test_list_marks_active(auth_env, capsys):
    _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--name', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    _, out = _run(capsys, 'auth', 'list')
    active_line = next(line for line in out.splitlines() if line.startswith('*'))
    assert 'bybit-main' in active_line


def test_use_switches_active(auth_env, capsys):
    _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--name', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    code, _ = _run(capsys, 'auth', 'use', 'okx')
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    assert json.loads(listing)['active'] == 'okx'


def test_use_unknown_errors(auth_env, capsys):
    code, _ = _run(capsys, 'auth', 'use', 'ghost')
    assert code == int(ExitCode.CONFIG_ERROR)


def test_logout_defaults_to_active(auth_env, capsys):
    _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--name', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    code, _ = _run(capsys, 'auth', 'logout')  # active is bybit-main (first added)
    assert code == int(ExitCode.OK)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    data = json.loads(listing)
    assert data['active'] == 'okx'
    assert [p['name'] for p in data['profiles']] == ['okx']


# --- status / whoami ----------------------------------------------------------

def test_status_online_valid(auth_env, monkeypatch, capsys, fake_exchange):
    _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    monkeypatch.setattr(cli, '_profile_exchange_store', lambda profile: fake_exchange)
    _, out = _run(capsys, 'auth', 'status', '--json')
    assert json.loads(out)['valid'] is True


def test_status_offline_is_null(auth_env, monkeypatch, capsys):
    _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    monkeypatch.setattr(cli, '_profile_exchange_store', lambda profile: FakeExchangeStore(offline=True))
    code, out = _run(capsys, 'auth', 'status', '--json')
    assert code == int(ExitCode.OK)
    assert json.loads(out)['valid'] is None


def test_whoami_no_active(auth_env, capsys):
    code, out = _run(capsys, 'auth', 'whoami')
    assert code == int(ExitCode.OK)
    assert 'No active profile' in out


# --- secret hygiene -----------------------------------------------------------

def test_secret_never_in_stdout(auth_env, monkeypatch, capsys, fake_exchange):
    secret = 'SUPERSECRETVALUE'
    _login(capsys, '--name', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', secret, '--passphrase', 'PASSPHRASEVAL')
    monkeypatch.setattr(cli, '_profile_exchange_store', lambda profile: fake_exchange)
    _, listing = _run(capsys, 'auth', 'list', '--json')
    _, status = _run(capsys, 'auth', 'status', '--json')
    _, whoami = _run(capsys, 'auth', 'whoami', '--json')
    assert secret not in listing + status + whoami
    assert 'PASSPHRASEVAL' not in listing + status + whoami


def test_profile_flag_threads_through_config_show(auth_env, capsys):
    _login(capsys, '--name', 'bybit-main', '--exchange', 'bybit', '--key', 'K', '--secret', 'S')
    _login(capsys, '--name', 'okx', '--exchange', 'okx', '--key', 'K', '--secret', 'S', '--passphrase', 'P')
    _, out = _run(capsys, 'config', 'show', '--profile', 'okx', '--json')
    assert json.loads(out)['config']['profile'] == 'okx'
