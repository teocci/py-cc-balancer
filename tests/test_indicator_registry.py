'''Phase 8 tests: the introspectable indicator registry.

The registry is what lets a caller (e.g. an agent) discover which indicators
exist and what parameters they accept, and is the validator for overrides.
'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import ConfigError
from ccbalancer.utils import indicator_registry as registry


def test_default_values_cover_every_indicator():
    values = registry.default_values()
    assert {'rsi', 'macd', 'ema', 'bollinger', 'atr', 'volume', 'fib'} <= set(values)
    assert values['rsi']['period'] == 14
    assert values['rsi']['overbought'] == 70.0
    assert values['ema']['periods'] == [12, 26, 200]


def test_default_values_are_independent_copies():
    first = registry.default_values()
    first['ema']['periods'].append(999)
    assert registry.default_values()['ema']['periods'] == [12, 26, 200]


def test_resolve_merges_overrides_over_defaults():
    resolved = registry.resolve({'rsi': {'overbought': 63.5, 'oversold': 32}})
    assert resolved['rsi']['overbought'] == 63.5
    assert resolved['rsi']['oversold'] == 32.0
    assert resolved['rsi']['period'] == 14  # untouched default


def test_resolve_coerces_types():
    resolved = registry.resolve({'rsi': {'period': 21}, 'ema': {'periods': [9, 21]}})
    assert resolved['rsi']['period'] == 21
    assert resolved['ema']['periods'] == [9, 21]


def test_resolve_rejects_unknown_indicator():
    with pytest.raises(ConfigError):
        registry.resolve({'supertrend': {'period': 10}})


def test_resolve_rejects_unknown_param():
    with pytest.raises(ConfigError):
        registry.resolve({'rsi': {'lookback': 14}})


def test_resolve_rejects_bad_type():
    with pytest.raises(ConfigError):
        registry.resolve({'rsi': {'period': 'fourteen'}})


def test_resolve_rejects_non_table_section():
    with pytest.raises(ConfigError):
        registry.resolve({'rsi': 14})


def test_describe_exposes_schema_and_current_values():
    catalog = registry.describe(registry.resolve({'rsi': {'overbought': 63.5}}))
    rsi = next(entry for entry in catalog if entry['name'] == 'rsi')
    overbought = next(param for param in rsi['params'] if param['name'] == 'overbought')
    assert overbought['type'] == 'float'
    assert overbought['default'] == 70.0
    assert overbought['value'] == 63.5
    assert overbought['description']


@pytest.mark.parametrize(
    'indicator, param, raw, expected',
    [
        ('rsi', 'period', '21', 21),
        ('rsi', 'overbought', '63.5', 63.5),
        ('ema', 'periods', '12,26,200', [12, 26, 200]),
        ('fib', 'ratios', '0,0.5,1', [0.0, 0.5, 1.0]),
    ],
)
def test_coerce_scalar(indicator, param, raw, expected):
    assert registry.coerce_scalar(indicator, param, raw) == expected


def test_coerce_scalar_rejects_unknown_and_bad():
    with pytest.raises(ConfigError):
        registry.coerce_scalar('rsi', 'nope', '1')
    with pytest.raises(ConfigError):
        registry.coerce_scalar('rsi', 'period', 'x')
