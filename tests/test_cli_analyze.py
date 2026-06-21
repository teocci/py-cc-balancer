'''Phase 8 tests: the `analyze` read command wired end to end.'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import SCHEMA_VERSION, ExitCode
from ccbalancer.managers.indicators_manager import IndicatorsManager
from ccbalancer.stores.market_cache import MarketCache

from .conftest import FakeExchangeStore

_HOUR_MS = 3_600_000
_BASE_MS = 1_700_000_000_000


def _candles(count: int = 40) -> list[list[float]]:
    return [
        [_BASE_MS + i * _HOUR_MS, 100.0, 101.0, 99.0, 100.0 + i, 10.0]
        for i in range(count)
    ]


def _inject(monkeypatch, tmp_path, exchange: FakeExchangeStore) -> None:
    manager = IndicatorsManager(exchange, MarketCache(tmp_path / 'ohlcv'), ohlcv_limit=200)
    monkeypatch.setattr(cli, '_indicators_manager', lambda config: manager)


def test_analyze_json_emits_stable_contract(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): _candles()})
    _inject(monkeypatch, tmp_path, exchange)

    code = cli.main(['analyze', 'BTC/USDT', '--timeframe', '1h', '--json'])
    assert code == int(ExitCode.OK)
    payload = json.loads(capsys.readouterr().out)

    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'analyze'
    assert payload['symbol'] == 'BTC/USDT'
    assert payload['unavailable_timeframes'] == []
    frame = payload['timeframes'][0]
    assert frame['timeframe'] == '1h'
    assert frame['stale'] is False
    assert 'rsi' in frame and 'macd' in frame and 'bollinger' in frame and 'fib' in frame


def test_analyze_lowercase_symbol_is_normalized(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): _candles()})
    _inject(monkeypatch, tmp_path, exchange)

    cli.main(['analyze', 'btc/usdt', '--timeframe', '1h', '--json'])
    assert json.loads(capsys.readouterr().out)['symbol'] == 'BTC/USDT'


def test_analyze_default_timeframes_used_when_omitted(appdir, monkeypatch, tmp_path, capsys):
    # Provide only 1h; the other default timeframes report unavailable.
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): _candles()})
    _inject(monkeypatch, tmp_path, exchange)

    cli.main(['analyze', 'BTC/USDT', '--json'])
    payload = json.loads(capsys.readouterr().out)

    assert [f['timeframe'] for f in payload['timeframes']] == ['1h']
    assert set(payload['unavailable_timeframes']) == {'1m', '5m', '15m', '4h', '1d', '1w'}


def test_analyze_offline_no_cache_exits_exchange_error(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(offline=True)
    _inject(monkeypatch, tmp_path, exchange)

    code = cli.main(['analyze', 'BTC/USDT', '--timeframe', '1h', '--json'])
    assert code == int(ExitCode.EXCHANGE_ERROR)
    payload = json.loads(capsys.readouterr().out)
    assert payload['timeframes'] == []
    assert payload['unavailable_timeframes'] == ['1h']


def test_analyze_text_output(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): _candles()})
    _inject(monkeypatch, tmp_path, exchange)

    cli.main(['analyze', 'BTC/USDT', '--timeframe', '1h'])
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out
    assert '1h' in out
