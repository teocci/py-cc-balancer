'''Phase 10 tests: the append-only fill ledger.'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import StateError
from ccbalancer.models import Fill
from ccbalancer.stores.ledger_store import LedgerStore, fill_to_dict


def _fill(side: str = 'sell', qty: float = 0.12) -> Fill:
    return Fill(
        ts='2026-06-19T12:00:00Z', symbol='BTC/USDT', side=side, price=50010.0,
        qty=qty, fee=0.6, fee_currency='USDT', order_id='order-1',
    )


def test_load_absent_returns_empty(tmp_path):
    store = LedgerStore(tmp_path / 'ledger.jsonl')
    assert store.load() == []


def test_append_then_load_roundtrips(tmp_path):
    store = LedgerStore(tmp_path / 'ledger.jsonl')
    store.append_fill(_fill())
    store.append_fill(_fill(side='buy', qty=0.05))
    records = store.load()
    assert [r['side'] for r in records] == ['sell', 'buy']
    assert records[0] == fill_to_dict(_fill())


def test_append_creates_parent_dir(tmp_path):
    store = LedgerStore(tmp_path / 'nested' / 'ledger.jsonl')
    store.append_fill(_fill())
    assert store.ledger_path.is_file()


def test_corrupt_line_raises_state_error(tmp_path):
    path = tmp_path / 'ledger.jsonl'
    path.write_text('{not json}\n', encoding='utf-8')
    with pytest.raises(StateError):
        LedgerStore(path).load()
