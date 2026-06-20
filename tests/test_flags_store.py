'''Phase 12 tests: the milestone store and model validation.'''

from __future__ import annotations

import json

import pytest

from ccbalancer.constants import FLAGS_FILENAME, SCHEMA_VERSION
from ccbalancer.exceptions import FlagError
from ccbalancer.models import Milestone
from ccbalancer.stores.flags_store import FlagsStore


def _store(tmp_path) -> FlagsStore:
    return FlagsStore(tmp_path / FLAGS_FILENAME)


def test_add_assigns_incrementing_ids(tmp_path):
    store = _store(tmp_path)
    first = store.add(symbol='BTC/USDT', metric='price', op='ge', threshold=100000.0,
                      note=None, created_at='2026-06-21T00:00:00Z')
    second = store.add(symbol='ETH/USDT', metric='drift_pct', op='lt', threshold=-5.0,
                       note='de-risk', created_at='2026-06-21T00:01:00Z')
    assert first.id == 1
    assert second.id == 2
    assert [m.id for m in store.load()] == [1, 2]


def test_id_reuse_after_remove_picks_max_plus_one(tmp_path):
    store = _store(tmp_path)
    store.add(symbol='BTC/USDT', metric='price', op='ge', threshold=1.0, note=None, created_at='t')
    store.add(symbol='BTC/USDT', metric='price', op='ge', threshold=2.0, note=None, created_at='t')
    store.remove(2)
    third = store.add(symbol='BTC/USDT', metric='price', op='ge', threshold=3.0, note=None, created_at='t')
    assert third.id == 2  # max remaining (1) + 1


def test_remove_unknown_id_raises(tmp_path):
    store = _store(tmp_path)
    store.add(symbol='BTC/USDT', metric='price', op='ge', threshold=1.0, note=None, created_at='t')
    with pytest.raises(FlagError):
        store.remove(99)


def test_persisted_file_carries_schema_version(tmp_path):
    store = _store(tmp_path)
    store.add(symbol='BTC/USDT', metric='value', op='gt', threshold=1000.0, note=None, created_at='t')
    data = json.loads((tmp_path / FLAGS_FILENAME).read_text(encoding='utf-8'))
    assert data['schema_version'] == SCHEMA_VERSION
    assert data['milestones'][0]['symbol'] == 'BTC/USDT'


def test_load_missing_file_is_empty(tmp_path):
    assert _store(tmp_path).load() == []


def test_load_corrupt_file_raises(tmp_path):
    path = tmp_path / FLAGS_FILENAME
    path.write_text('{not json', encoding='utf-8')
    with pytest.raises(FlagError):
        FlagsStore(path).load()


def test_load_invalid_entry_raises(tmp_path):
    path = tmp_path / FLAGS_FILENAME
    path.write_text(json.dumps({'milestones': [{'id': 1, 'symbol': 'BTC/USDT'}]}), encoding='utf-8')
    with pytest.raises(FlagError):
        FlagsStore(path).load()


def test_round_trip_preserves_fields(tmp_path):
    store = _store(tmp_path)
    store.add(symbol='btc/usdt', metric='price', op='ge', threshold=100000.0,
              note='target', created_at='2026-06-21T00:00:00Z')
    loaded = store.load()[0]
    assert loaded.symbol == 'BTC/USDT'  # normalized upper
    assert loaded.note == 'target'
    assert loaded.expression == 'price >= 100000'


def test_milestone_rejects_bad_symbol():
    with pytest.raises(FlagError):
        Milestone(id=1, symbol='BTC', metric='price', op='ge', threshold=1.0)


def test_milestone_rejects_unknown_metric():
    with pytest.raises(FlagError):
        Milestone(id=1, symbol='BTC/USDT', metric='rsi', op='ge', threshold=1.0)


def test_milestone_rejects_unknown_operator():
    with pytest.raises(FlagError):
        Milestone(id=1, symbol='BTC/USDT', metric='price', op='near', threshold=1.0)
