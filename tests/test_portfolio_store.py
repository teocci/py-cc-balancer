'''Phase 3 tests: portfolio store CRUD and `pair` CLI commands.'''

from __future__ import annotations

import json

import pytest

from ccbalancer import cli
from ccbalancer.exceptions import PortfolioError
from ccbalancer.models import PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore


@pytest.fixture
def store(tmp_path):
    return PortfolioStore(tmp_path / 'portfolio.json')


def _pair(symbol: str = 'BTC/USDT') -> PairConfig:
    return PairConfig(symbol, 80.0, 20.0, 5.0, 10.0)


def test_load_empty_when_absent(store):
    assert store.load() == []


def test_add_and_roundtrip(store):
    store.add(_pair())
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].symbol == 'BTC/USDT'


def test_add_duplicate_rejected(store):
    store.add(_pair())
    with pytest.raises(PortfolioError):
        store.add(_pair())


def test_get_is_case_insensitive(store):
    store.add(_pair())
    assert store.get('btc/usdt') is not None


def test_replace_updates_existing(store):
    store.add(_pair())
    store.replace(PairConfig('BTC/USDT', 60.0, 40.0, 7.0, 5.0))
    updated = store.get('BTC/USDT')
    assert updated.target_volatile_pct == 60.0
    assert updated.band_pct == 7.0


def test_replace_missing_rejected(store):
    with pytest.raises(PortfolioError):
        store.replace(_pair('ETH/USDT'))


def test_remove_missing_rejected(store):
    with pytest.raises(PortfolioError):
        store.remove('SOL/USDT')


def test_bad_ratio_rejected_on_construct():
    with pytest.raises(PortfolioError):
        PairConfig('BTC/USDT', 80.0, 30.0, 5.0, 10.0)


def test_baseline_fields_round_trip(store):
    pair = PairConfig(
        'BTC/USDT', 80.0, 20.0, 5.0, 10.0,
        entry_price=48000.0, entry_ts='2026-06-01T00:00:00Z',
        invested_capital=10000.0, target_set_price=50000.0,
        target_set_ts='2026-06-02T00:00:00Z',
    )
    store.add(pair)
    loaded = store.get('BTC/USDT')
    assert loaded.entry_price == 48000.0
    assert loaded.entry_ts == '2026-06-01T00:00:00Z'
    assert loaded.invested_capital == 10000.0
    assert loaded.target_set_price == 50000.0
    assert loaded.target_set_ts == '2026-06-02T00:00:00Z'


def test_baselines_default_to_none(store):
    store.add(_pair())
    loaded = store.get('BTC/USDT')
    assert loaded.entry_price is None
    assert loaded.target_set_ts is None


def test_negative_entry_price_rejected():
    with pytest.raises(PortfolioError):
        PairConfig('BTC/USDT', 80.0, 20.0, 5.0, 10.0, entry_price=-1.0)


def test_cli_pair_add_captures_entry_and_stamps_ts(appdir, capsys):
    rc = cli.main([
        'pair', 'add', 'BTC/USDT', '--entry-price', '48000',
        '--invested', '10000', '--target-set-price', '50000', '--json',
    ])
    assert rc == 0
    pair = json.loads(capsys.readouterr().out)['pair']
    assert pair['entry_price'] == 48000.0
    assert pair['invested_capital'] == 10000.0
    assert pair['target_set_price'] == 50000.0
    assert pair['entry_ts'].endswith('Z')
    assert pair['target_set_ts'].endswith('Z')


def test_cli_pair_add_without_baselines_leaves_them_null(appdir, capsys):
    cli.main(['pair', 'add', 'BTC/USDT', '--json'])
    pair = json.loads(capsys.readouterr().out)['pair']
    assert pair['entry_price'] is None
    assert pair['entry_ts'] is None


def test_cli_pair_add_then_list_json(appdir, capsys):
    assert cli.main(['pair', 'add', 'sui/usdt', '--target', '25/75', '--min-notional', '5']) == 0
    capsys.readouterr()
    assert cli.main(['pair', 'list', '--json']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['command'] == 'pair list'
    assert data['pairs'][0]['symbol'] == 'SUI/USDT'
    assert data['pairs'][0]['target_volatile_pct'] == 25.0
    assert data['pairs'][0]['min_notional'] == 5.0


def test_cli_pair_add_uses_defaults(appdir, capsys):
    assert cli.main(['pair', 'add', 'BTC/USDT', '--json']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['pair']['target_volatile_pct'] == 80.0
    assert data['pair']['band_pct'] == 5.0


def test_cli_pair_add_bad_target_is_config_error(appdir, capsys):
    rc = cli.main(['pair', 'add', 'BTC/USDT', '--target', '80-20'])
    assert rc == 2


def test_cli_pair_set_then_remove(appdir, capsys):
    cli.main(['pair', 'add', 'ETH/USDT', '--target', '70/30'])
    capsys.readouterr()
    assert cli.main(['pair', 'set', 'ETH/USDT', '--band', '8', '--json']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['pair']['band_pct'] == 8.0
    assert cli.main(['pair', 'remove', 'ETH/USDT']) == 0
    capsys.readouterr()
    cli.main(['pair', 'list', '--json'])
    assert json.loads(capsys.readouterr().out)['pairs'] == []


def test_cli_pair_set_missing_is_config_error(appdir):
    assert cli.main(['pair', 'set', 'XRP/USDT', '--band', '5']) == 2
