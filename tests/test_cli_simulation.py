'''Phase 17 tests: the `simulation fetch` command wired end to end.

The exchange is faked via the ``_simulation_manager`` seam; the store is real
(under tmp_path) so resumability is exercised through the CLI.
'''

from __future__ import annotations

import json

from ccbalancer import cli
from ccbalancer.constants import SCHEMA_VERSION, ExitCode
from ccbalancer.managers.simulation_manager import SimulationManager
from ccbalancer.stores.simulation_store import SimulationStore

from .conftest import FakeExchangeStore

_HOUR_MS = 3_600_000
_START = 1_661_990_400_000  # 2022-09-01T00:00:00Z


def _hourly(count: int) -> list[list[float]]:
    return [[_START + i * _HOUR_MS, 10.0 + i, 12.0 + i, 9.0 + i, 11.0 + i, 100.0 + i] for i in range(count)]


def _inject(monkeypatch, tmp_path, exchange: FakeExchangeStore) -> SimulationStore:
    store = SimulationStore(tmp_path / 'simulation')
    manager = SimulationManager(exchange, store)
    monkeypatch.setattr(cli, '_simulation_manager', lambda config: manager)
    return store


def test_fetch_json_emits_stable_contract(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={('BTC/USDT', '1h'): _hourly(5)})
    _inject(monkeypatch, tmp_path, exchange)

    code = cli.main(['simulation', 'fetch', 'BTC/USDT', '--timeframe', '1h',
                     '--start', '2022-09-01', '--end', '2022-09-02', '--json'])
    assert code == int(ExitCode.OK)
    payload = json.loads(capsys.readouterr().out)

    assert payload['schema_version'] == SCHEMA_VERSION
    assert payload['command'] == 'simulation fetch'
    assert payload['symbol'] == 'BTC/USDT'
    frame = payload['timeframes'][0]
    assert frame['timeframe'] == '1h'
    assert frame['appended'] == 5
    assert frame['total_rows'] == 5
    assert frame['up_to_date'] is False
    assert frame['first_open'] == '2022-09-01T00:00:00Z'


def test_fetch_lowercase_symbol_is_normalized(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={('BTC/USDT', '1h'): _hourly(3)})
    _inject(monkeypatch, tmp_path, exchange)

    cli.main(['simulation', 'fetch', 'btc/usdt', '--timeframe', '1h',
              '--start', '2022-09-01', '--end', '2022-09-02', '--json'])
    assert json.loads(capsys.readouterr().out)['symbol'] == 'BTC/USDT'


def test_fetch_defaults_to_15m_1h_4h_1d(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={
        ('BTC/USDT', '15m'): [[_START, 10.0, 12.0, 9.0, 11.0, 100.0]],
        ('BTC/USDT', '1h'): _hourly(3),
        ('BTC/USDT', '4h'): [[_START, 10.0, 12.0, 9.0, 11.0, 100.0]],
        ('BTC/USDT', '1d'): [[_START, 10.0, 12.0, 9.0, 11.0, 100.0]],
    })
    _inject(monkeypatch, tmp_path, exchange)

    cli.main(['simulation', 'fetch', 'BTC/USDT', '--start', '2022-09-01', '--end', '2022-09-05', '--json'])
    payload = json.loads(capsys.readouterr().out)

    assert [f['timeframe'] for f in payload['timeframes']] == ['15m', '1h', '4h', '1d']


def test_fetch_resume_is_up_to_date_on_second_run(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={('BTC/USDT', '1h'): _hourly(5)})
    _inject(monkeypatch, tmp_path, exchange)
    args = ['simulation', 'fetch', 'BTC/USDT', '--timeframe', '1h',
            '--start', '2022-09-01', '--end', '2022-09-02', '--json']

    cli.main(args)
    capsys.readouterr()  # discard first run
    cli.main(args)
    frame = json.loads(capsys.readouterr().out)['timeframes'][0]

    assert frame['appended'] == 0
    assert frame['up_to_date'] is True
    assert frame['total_rows'] == 5


def test_fetch_invalid_start_exits_config_error(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={('BTC/USDT', '1h'): _hourly(1)})
    _inject(monkeypatch, tmp_path, exchange)

    code = cli.main(['simulation', 'fetch', 'BTC/USDT', '--start', 'not-a-date', '--json'])
    assert code == int(ExitCode.CONFIG_ERROR)


def test_fetch_text_output(appdir, monkeypatch, tmp_path, capsys):
    exchange = FakeExchangeStore(exchange_id='binance', ohlcv={('BTC/USDT', '1h'): _hourly(4)})
    _inject(monkeypatch, tmp_path, exchange)

    cli.main(['simulation', 'fetch', 'BTC/USDT', '--timeframe', '1h', '--start', '2022-09-01', '--end', '2022-09-02'])
    out = capsys.readouterr().out
    assert 'BTC/USDT' in out and '1h' in out and '+4' in out
