'''Phase 2 tests: settings resolution, masking, scaffolding, discovery.'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer import config as config_mod
from ccbalancer.constants import ENV_API_KEY, ENV_API_SECRET, ENV_EXCHANGE
from ccbalancer.exceptions import ConfigError


def test_defaults_when_no_config(appdir):
    cfg = config_mod.load_config()
    assert cfg.exchange == 'bybit'
    assert cfg.testnet is True
    assert cfg.defaults.band_pct == 5.0
    assert cfg.config_path is None


def test_toml_overrides_defaults(appdir, tmp_path):
    path = tmp_path / 'c.toml'
    path.write_text("[global]\nexchange='binance'\ntestnet=false\n[defaults]\nband_pct=7.0\n")
    cfg = config_mod.load_config(cli_config=str(path))
    assert cfg.exchange == 'binance'
    assert cfg.testnet is False
    assert cfg.defaults.band_pct == 7.0


def test_env_overrides_toml(appdir, tmp_path, monkeypatch):
    path = tmp_path / 'c.toml'
    path.write_text("[global]\nexchange='binance'\n")
    monkeypatch.setenv(ENV_EXCHANGE, 'bybit')
    cfg = config_mod.load_config(cli_config=str(path))
    assert cfg.exchange == 'bybit'


def test_cli_override_wins(appdir):
    cfg = config_mod.load_config(exchange_override='binance', testnet_override=False)
    assert cfg.exchange == 'binance'
    assert cfg.testnet is False


def test_unsupported_exchange_raises(appdir):
    with pytest.raises(ConfigError):
        config_mod.load_config(exchange_override='kraken')


def test_secrets_from_env_are_masked(appdir, monkeypatch):
    monkeypatch.setenv(ENV_API_KEY, 'ABCD1234EFGH5678')
    monkeypatch.setenv(ENV_API_SECRET, 'supersecretvalue')
    cfg = config_mod.load_config()
    summary = config_mod.masked_summary(cfg)
    assert summary['api_key'] == 'ABCD...5678'
    assert 'supersecret' not in str(summary['api_secret'])


def test_require_credentials_raises_when_missing(appdir):
    cfg = config_mod.load_config()
    with pytest.raises(ConfigError):
        config_mod.require_credentials(cfg)


def test_init_app_dir_creates_then_idempotent(appdir):
    created = config_mod.init_app_dir(appdir)
    names = {path.name for path in created}
    assert {'config.toml', '.env'} <= names
    assert (appdir / 'config.toml').is_file()
    assert config_mod.init_app_dir(appdir) == []


def test_discovery_prefers_project_local(appdir, tmp_path):
    (tmp_path / 'ccbalancer.toml').write_text("[global]\nexchange='binance'\n")
    cfg = config_mod.load_config()
    assert cfg.exchange == 'binance'
    assert cfg.config_path is not None


def test_cli_config_show_json_exit_zero(appdir, capsys):
    rc = cli.main(['config', 'show', '--json'])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data['command'] == 'config show'
    assert data['config']['exchange'] == 'bybit'


def test_cli_config_show_missing_secret_is_ok(appdir, capsys):
    # `config show` does not require credentials; exit 0.
    assert cli.main(['config', 'show']) == 0
