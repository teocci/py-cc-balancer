'''Phase 8 tests: `indicator list` (discovery) and `indicator set` (write).

These prove the agent-facing loop: discover the parameter surface, change it,
and see the change take effect (in the file, in discovery, and in `analyze`).
'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import INDICATORS_FILENAME, SCHEMA_VERSION, ExitCode
from ccbalancer.managers.indicators_manager import IndicatorsManager
from ccbalancer.stores.market_cache import MarketCache

from .conftest import FakeExchangeStore

_HOUR_MS = 3_600_000
_BASE_MS = 1_700_000_000_000


def _run_json(argv: list[str], capsys) -> dict:
    code = cli.main(argv)
    assert code == int(ExitCode.OK)
    return json.loads(capsys.readouterr().out)


def test_indicator_list_exposes_schema_and_values(appdir, capsys):
    payload = _run_json(['indicator', 'list', '--json'], capsys)
    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'indicator list'
    rsi = next(entry for entry in payload['indicators'] if entry['name'] == 'rsi')
    period = next(param for param in rsi['params'] if param['name'] == 'period')
    assert period['type'] == 'int'
    assert period['default'] == 14
    assert period['value'] == 14


def test_indicator_set_writes_file_and_updates_discovery(appdir, capsys):
    code = cli.main(['indicator', 'set', 'rsi', 'overbought=63.5', 'oversold=32'])
    assert code == int(ExitCode.OK)
    capsys.readouterr()

    assert (appdir / INDICATORS_FILENAME).is_file()
    payload = _run_json(['indicator', 'list', '--json'], capsys)
    rsi = next(entry for entry in payload['indicators'] if entry['name'] == 'rsi')
    overbought = next(param for param in rsi['params'] if param['name'] == 'overbought')
    assert overbought['value'] == 63.5
    assert overbought['default'] == 70.0  # default unchanged, only the value


def test_indicator_set_list_value(appdir, capsys):
    cli.main(['indicator', 'set', 'ema', 'periods=9,21,55'])
    capsys.readouterr()
    payload = _run_json(['indicator', 'list', '--json'], capsys)
    ema = next(entry for entry in payload['indicators'] if entry['name'] == 'ema')
    assert ema['params'][0]['value'] == [9, 21, 55]


def test_indicator_set_unknown_param_is_config_error(appdir):
    assert cli.main(['indicator', 'set', 'rsi', 'lookback=14']) == int(ExitCode.CONFIG_ERROR)


def test_indicator_set_unknown_indicator_is_config_error(appdir):
    assert cli.main(['indicator', 'set', 'supertrend', 'period=10']) == int(ExitCode.CONFIG_ERROR)


def test_indicator_set_bad_assignment_is_config_error(appdir):
    assert cli.main(['indicator', 'set', 'rsi', 'overbought']) == int(ExitCode.CONFIG_ERROR)


def test_custom_thresholds_flow_into_analyze(appdir, monkeypatch, tmp_path, capsys):
    # An RSI of ~37 is 'neutral' at default 30/70 but 'oversold' once oversold=40.
    candles = [[_BASE_MS + i * _HOUR_MS, 100.0, 101.0, 99.0, 100.0 - i * 0.1, 10.0] for i in range(60)]
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): candles})
    manager_cache = MarketCache(tmp_path / 'ohlcv')

    def _factory(config):
        return IndicatorsManager(exchange, manager_cache, ohlcv_limit=200, settings=config.indicators)

    monkeypatch.setattr(cli, '_indicators_manager', _factory)

    cli.main(['indicator', 'set', 'rsi', 'oversold=40'])
    capsys.readouterr()
    payload = _run_json(['analyze', 'BTC/USDT', '--timeframe', '1h', '--json'], capsys)
    rsi = payload['timeframes'][0]['rsi']
    assert rsi['oversold'] == 40.0
    assert rsi['zone'] == 'oversold'
