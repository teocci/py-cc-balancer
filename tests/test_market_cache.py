'''Phase 8 tests: OHLCV cache read/write and freshness judgement.'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import StateError
from ccbalancer.stores.market_cache import MarketCache

# A candle is [time_ms, open, high, low, close, volume].
_CANDLES = [
    [1_000_000_000_000, 10.0, 11.0, 9.0, 10.5, 100.0],
    [1_000_003_600_000, 10.5, 12.0, 10.0, 11.5, 120.0],
]
_HOUR_MS = 3_600_000


def test_path_for_replaces_slash(tmp_path):
    cache = MarketCache(tmp_path)
    assert cache.path_for('BTC/USDT', '1h') == tmp_path / 'BTC_USDT' / '1h.jsonl'


def test_write_then_read_round_trips(tmp_path):
    cache = MarketCache(tmp_path)
    cache.write('BTC/USDT', '1h', _CANDLES)
    assert cache.read('BTC/USDT', '1h') == _CANDLES


def test_read_absent_returns_empty(tmp_path):
    assert MarketCache(tmp_path).read('ETH/USDT', '4h') == []


def test_read_corrupt_raises_state_error(tmp_path):
    cache = MarketCache(tmp_path)
    path = cache.path_for('BTC/USDT', '1h')
    path.parent.mkdir(parents=True)
    path.write_text('not json\n', encoding='utf-8')
    with pytest.raises(StateError):
        cache.read('BTC/USDT', '1h')


def test_is_fresh_within_two_timeframes(tmp_path):
    cache = MarketCache(tmp_path)
    newest = _CANDLES[-1][0]
    assert cache.is_fresh(_CANDLES, '1h', newest + _HOUR_MS) is True


def test_is_stale_beyond_two_timeframes(tmp_path):
    cache = MarketCache(tmp_path)
    newest = _CANDLES[-1][0]
    assert cache.is_fresh(_CANDLES, '1h', newest + 3 * _HOUR_MS) is False


def test_is_fresh_empty_is_false(tmp_path):
    assert MarketCache(tmp_path).is_fresh([], '1h', 1_000_000_000_000) is False
