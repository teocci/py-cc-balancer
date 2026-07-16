'''Command-scoped flag parents (I-5) and `--fields` projection (I-6).'''

from __future__ import annotations

import json

import pytest

from ccbalancer import __version__, cli


def _help(capsys, *argv) -> str:
    '''Return the `--help` text for a (sub)command (argparse exits 0).'''
    with pytest.raises(SystemExit):
        cli.main([*argv, '--help'])
    return capsys.readouterr().out


@pytest.mark.parametrize('argv,present,absent', [
    (('auth', 'login'), ['--account', '--exchange', '--testnet', '--key'], ['--pair', '--profile']),
    (('pair', 'add'), ['--account', '--target'], ['--pair', '--exchange', '--testnet']),
    (('analyze',), ['--exchange', '--testnet', '--timeframe'], ['--account', '--pair']),
    (('status',), ['--account', '--exchange', '--testnet', '--pair'], ['--profile']),
    (('auth', 'status'), ['--account'], ['--pair', '--exchange']),
    (('auth', 'use'), [], ['--account', '--pair', '--exchange']),
    (('config', 'init'), [], ['--account', '--pair', '--exchange']),
    (('decisions',), ['--account', '--pair'], ['--exchange', '--testnet']),
])
def test_command_flag_surface(capsys, argv, present, absent):
    out = _help(capsys, *argv)
    for flag in present:
        assert flag in out, f'{argv}: expected {flag} in --help'
    for flag in absent:
        assert flag not in out, f'{argv}: unexpected {flag} in --help'


def test_every_command_carries_base_flags(capsys):
    for argv in [('version',), ('status',), ('auth', 'login'), ('pair', 'list'), ('config', 'init')]:
        out = _help(capsys, *argv)
        for flag in ('--json', '--fields', '--config'):
            assert flag in out, f'{argv}: base flag {flag} missing'


def test_fields_projects_top_level_keys(capsys):
    cli.main(['version', '--json', '--fields', 'version'])
    assert json.loads(capsys.readouterr().out) == {'version': __version__}


def test_fields_unknown_key_yields_empty(capsys):
    cli.main(['version', '--json', '--fields', 'nope'])
    assert json.loads(capsys.readouterr().out) == {}


def test_fields_without_json_is_ignored(capsys):
    cli.main(['version', '--fields', 'version'])
    assert capsys.readouterr().out.strip() == __version__
