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


def test_data_exchange_defaults_to_trading_exchange(appdir):
    cfg = config_mod.load_config()
    assert cfg.data_exchange == 'bybit'
    assert cfg.decision_timeframes == ('1m', '5m', '15m')
    assert cfg.analysis_timeframes == ('1h', '4h', '1d', '1w')
    assert cfg.ohlcv_limit == 500


def test_data_exchange_override_from_toml(appdir, tmp_path):
    path = tmp_path / 'c.toml'
    path.write_text(
        "[global]\nexchange='bybit'\ndata_exchange='binance'\n"
        "decision_timeframes=['5m']\nanalysis_timeframes=['1d']\nohlcv_limit=100\n"
    )
    cfg = config_mod.load_config(cli_config=str(path))
    assert cfg.data_exchange == 'binance'
    assert cfg.decision_timeframes == ('5m',)
    assert cfg.analysis_timeframes == ('1d',)
    assert cfg.ohlcv_limit == 100


def test_unsupported_data_exchange_raises(appdir, tmp_path):
    path = tmp_path / 'c.toml'
    path.write_text("[global]\ndata_exchange='kraken'\n")
    with pytest.raises(ConfigError):
        config_mod.load_config(cli_config=str(path))


def test_bad_timeframes_type_raises(appdir, tmp_path):
    path = tmp_path / 'c.toml'
    path.write_text("[global]\ndecision_timeframes='5m'\n")
    with pytest.raises(ConfigError):
        config_mod.load_config(cli_config=str(path))


def test_indicator_defaults_when_no_file(appdir):
    cfg = config_mod.load_config()
    assert cfg.indicators.get('rsi', 'overbought') == 70.0
    assert cfg.indicators.get('ema', 'periods') == [12, 26, 200]
    assert cfg.indicators_path == appdir / 'indicators.toml'


def test_indicator_overrides_from_indicators_toml(appdir):
    appdir.mkdir(parents=True, exist_ok=True)
    (appdir / 'indicators.toml').write_text(
        '[rsi]\noverbought = 63.5\noversold = 32\n[ema]\nperiods = [9, 21]\n'
    )
    cfg = config_mod.load_config()
    assert cfg.indicators.get('rsi', 'overbought') == 63.5
    assert cfg.indicators.get('rsi', 'oversold') == 32.0
    assert cfg.indicators.get('rsi', 'period') == 14  # untouched default
    assert cfg.indicators.get('ema', 'periods') == [9, 21]


def test_bad_indicators_toml_unknown_param_raises(appdir):
    appdir.mkdir(parents=True, exist_ok=True)
    (appdir / 'indicators.toml').write_text('[rsi]\nlookback = 14\n')
    with pytest.raises(ConfigError):
        config_mod.load_config()


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
