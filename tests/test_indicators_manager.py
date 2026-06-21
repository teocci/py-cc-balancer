'''Phase 8 tests: the indicators manager's cache/network resolution.

Covers the four candle-resolution paths — fresh cache hit, cache miss/refetch,
stale-cache offline fallback, and offline-with-no-cache — plus multi-timeframe
ordering. No network is used: a :class:`FakeExchangeStore` supplies or refuses
candles and a real :class:`MarketCache` writes to a tmp directory.
'''

from __future__ import annotations

from ccbalancer.managers.indicators_manager import IndicatorsManager
from ccbalancer.stores.market_cache import MarketCache

from .conftest import FakeExchangeStore

_HOUR_MS = 3_600_000
_BASE_MS = 1_700_000_000_000


def _candles(count: int, price: float = 100.0, base_ms: int = _BASE_MS) -> list[list[float]]:
    return [
        [base_ms + i * _HOUR_MS, price, price + 1.0, price - 1.0, price + 0.5, 10.0]
        for i in range(count)
    ]


def _manager(tmp_path, exchange: FakeExchangeStore) -> IndicatorsManager:
    return IndicatorsManager(exchange, MarketCache(tmp_path), ohlcv_limit=200)


def _now_after(candles: list[list[float]]) -> int:
    return candles[-1][0] + _HOUR_MS  # within the 2-timeframe freshness window


def test_cache_miss_fetches_and_writes(tmp_path):
    candles = _candles(30)
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): candles})
    manager = _manager(tmp_path, exchange)

    snapshot = manager.snapshot('BTC/USDT', '1h', at_ms=_now_after(candles))

    assert snapshot is not None
    assert snapshot.stale is False
    assert snapshot.candle_count == 30
    assert exchange.ohlcv_calls == [('BTC/USDT', '1h', 200)]
    assert manager.cache.read('BTC/USDT', '1h') == candles


def test_fresh_cache_hit_skips_network(tmp_path):
    candles = _candles(30)
    exchange = FakeExchangeStore(offline=True)  # would raise if called
    manager = _manager(tmp_path, exchange)
    manager.cache.write('BTC/USDT', '1h', candles)

    snapshot = manager.snapshot('BTC/USDT', '1h', at_ms=_now_after(candles))

    assert snapshot is not None
    assert snapshot.stale is False
    assert exchange.ohlcv_calls == []


def test_stale_cache_online_refetches(tmp_path):
    old = _candles(30, price=100.0)
    fresh = _candles(30, price=200.0, base_ms=_BASE_MS + 100 * _HOUR_MS)
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): fresh})
    manager = _manager(tmp_path, exchange)
    manager.cache.write('BTC/USDT', '1h', old)

    # ``now`` far past the old candles -> stale -> refetch.
    snapshot = manager.snapshot('BTC/USDT', '1h', at_ms=old[-1][0] + 50 * _HOUR_MS)

    assert snapshot is not None
    assert snapshot.stale is False
    assert snapshot.close == fresh[-1][4]
    assert exchange.ohlcv_calls == [('BTC/USDT', '1h', 200)]


def test_stale_cache_offline_falls_back(tmp_path):
    candles = _candles(30)
    exchange = FakeExchangeStore(offline=True)
    manager = _manager(tmp_path, exchange)
    manager.cache.write('BTC/USDT', '1h', candles)

    snapshot = manager.snapshot('BTC/USDT', '1h', at_ms=candles[-1][0] + 50 * _HOUR_MS)

    assert snapshot is not None
    assert snapshot.stale is True
    assert exchange.ohlcv_calls == [('BTC/USDT', '1h', 200)]


def test_offline_no_cache_returns_none(tmp_path):
    exchange = FakeExchangeStore(offline=True)
    manager = _manager(tmp_path, exchange)

    assert manager.snapshot('BTC/USDT', '1h', at_ms=_BASE_MS) is None


def test_require_fresh_offline_stale_returns_none(tmp_path):
    candles = _candles(30)
    exchange = FakeExchangeStore(offline=True)
    manager = _manager(tmp_path, exchange)
    manager.cache.write('BTC/USDT', '1h', candles)

    snapshot = manager.snapshot(
        'BTC/USDT', '1h', require_fresh=True, at_ms=candles[-1][0] + 50 * _HOUR_MS
    )
    assert snapshot is None


def test_snapshots_preserve_order_with_gaps(tmp_path):
    candles = _candles(30)
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): candles})  # only 1h available
    manager = _manager(tmp_path, exchange)

    results = manager.snapshots('BTC/USDT', ['1h', '4h'], at_ms=_now_after(candles))

    assert results[0] is not None and results[0].timeframe == '1h'
    assert results[1] is None


def test_snapshot_populates_indicator_values(tmp_path):
    # A long ascending series yields RSI 100 and a defined EMA-12.
    candles = [
        [_BASE_MS + i * _HOUR_MS, i, i + 1.0, i - 1.0, float(i), 10.0]
        for i in range(1, 60)
    ]
    exchange = FakeExchangeStore(ohlcv={('BTC/USDT', '1h'): candles})
    manager = _manager(tmp_path, exchange)

    snapshot = manager.snapshot('BTC/USDT', '1h', at_ms=_now_after(candles))

    assert snapshot.rsi == 100.0
    assert '12' in snapshot.ema
    assert snapshot.fib['0'] == max(c[2] for c in candles)
