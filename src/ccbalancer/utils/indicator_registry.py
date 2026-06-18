'''The indicator registry: the introspectable catalog of indicators.

The registry is the single source of truth for *which* indicators exist and
*what parameters each accepts* (name, type, default, description). It exists so a
caller — especially an AI agent — can discover the configuration surface without
prior knowledge: ``ccbalancer indicators`` serializes this catalog, and
``indicator set`` validates writes against it.

The set of indicators is fixed in code (adding one means writing a pure function
in :mod:`ccbalancer.utils.indicators` and registering it here). User-tunable
*parameters* live in ``indicators.toml``; this module resolves overrides over the
built-in defaults and validates them.
'''

from __future__ import annotations

from dataclasses import dataclass

from ccbalancer import constants as c
from ccbalancer.exceptions import ConfigError

__all__ = [
    'ParamSpec',
    'IndicatorSpec',
    'REGISTRY',
    'default_values',
    'resolve',
    'describe',
    'coerce_scalar',
]

# Parameter type tags understood by the registry.
TYPE_INT = 'int'
TYPE_FLOAT = 'float'
TYPE_INT_LIST = 'int_list'
TYPE_FLOAT_LIST = 'float_list'
_LIST_TYPES = {TYPE_INT_LIST, TYPE_FLOAT_LIST}


@dataclass(slots=True, frozen=True)
class ParamSpec:
    '''One tunable parameter of an indicator.

    Attributes:
        name: Parameter key as used in ``indicators.toml``.
        type: One of ``int``/``float``/``int_list``/``float_list``.
        default: Built-in default value.
        description: Human/agent-readable explanation.
    '''

    name: str
    type: str
    default: object
    description: str


@dataclass(slots=True, frozen=True)
class IndicatorSpec:
    '''One registered indicator and its parameters.

    Attributes:
        name: Indicator key (e.g. ``'rsi'``).
        description: What the indicator computes.
        params: Its tunable parameters.
    '''

    name: str
    description: str
    params: tuple[ParamSpec, ...]


REGISTRY: tuple[IndicatorSpec, ...] = (
    IndicatorSpec('rsi', 'Relative Strength Index (Wilder smoothing)', (
        ParamSpec('period', TYPE_INT, c.DEFAULT_RSI_PERIOD, 'Lookback period.'),
        ParamSpec('overbought', TYPE_FLOAT, c.DEFAULT_RSI_OVERBOUGHT, 'Threshold for the overbought zone.'),
        ParamSpec('oversold', TYPE_FLOAT, c.DEFAULT_RSI_OVERSOLD, 'Threshold for the oversold zone.'),
    )),
    IndicatorSpec('macd', 'Moving Average Convergence Divergence', (
        ParamSpec('fast', TYPE_INT, c.DEFAULT_MACD_FAST, 'Fast EMA length.'),
        ParamSpec('slow', TYPE_INT, c.DEFAULT_MACD_SLOW, 'Slow EMA length.'),
        ParamSpec('signal', TYPE_INT, c.DEFAULT_MACD_SIGNAL, 'Signal EMA length.'),
    )),
    IndicatorSpec('ema', 'Exponential moving averages', (
        ParamSpec('periods', TYPE_INT_LIST, list(c.DEFAULT_EMA_PERIODS), 'EMA periods to report.'),
    )),
    IndicatorSpec('bollinger', 'Bollinger Bands (population stddev)', (
        ParamSpec('period', TYPE_INT, c.DEFAULT_BOLLINGER_PERIOD, 'Moving-average window.'),
        ParamSpec('stddev', TYPE_FLOAT, c.DEFAULT_BOLLINGER_STDDEV, 'Band width in standard deviations.'),
    )),
    IndicatorSpec('atr', 'Average True Range (Wilder smoothing)', (
        ParamSpec('period', TYPE_INT, c.DEFAULT_ATR_PERIOD, 'Lookback period.'),
    )),
    IndicatorSpec('volume', 'Volume moving average', (
        ParamSpec('ma_period', TYPE_INT, c.DEFAULT_VOLUME_MA_PERIOD, 'Volume moving-average window.'),
    )),
    IndicatorSpec('fib', 'Fibonacci retracement levels', (
        ParamSpec('ratios', TYPE_FLOAT_LIST, list(c.FIB_RATIOS), 'Retracement ratios (0 = swing high, 1 = low).'),
    )),
)

_SPEC_BY_NAME: dict[str, IndicatorSpec] = {spec.name: spec for spec in REGISTRY}


def default_values() -> dict[str, dict[str, object]]:
    '''Return the built-in default value for every indicator parameter.'''
    return {
        spec.name: {param.name: _copy(param.default) for param in spec.params}
        for spec in REGISTRY
    }


def resolve(overrides: dict[str, object]) -> dict[str, dict[str, object]]:
    '''Merge ``overrides`` over the defaults, validating against the registry.

    Args:
        overrides: Mapping of indicator -> {param -> raw value}, e.g. parsed
            from ``indicators.toml``.

    Returns:
        The fully resolved indicator -> {param -> value} mapping.

    Raises:
        ConfigError: If an unknown indicator/parameter is given or a value has
            the wrong type.
    '''
    values = default_values()
    for indicator, params in overrides.items():
        spec = _require_spec(indicator)
        if not isinstance(params, dict):
            raise ConfigError(f'indicators.toml [{indicator}] must be a table')
        for param_name, raw in params.items():
            param = _require_param(spec, param_name)
            values[indicator][param_name] = _coerce(param, raw)
    return values


def describe(values: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    '''Serialize the registry plus current ``values`` for discovery output.'''
    return [
        {
            'name': spec.name,
            'description': spec.description,
            'params': [_describe_param(param, values[spec.name][param.name]) for param in spec.params],
        }
        for spec in REGISTRY
    ]


def coerce_scalar(indicator: str, param_name: str, raw: str) -> object:
    '''Coerce a CLI string value to the registered type for one parameter.

    Raises:
        ConfigError: For unknown indicator/parameter or an unparseable value.
    '''
    spec = _require_spec(indicator)
    param = _require_param(spec, param_name)
    if param.type in _LIST_TYPES:
        items = [item.strip() for item in raw.split(',') if item.strip()]
        return _coerce(param, items)
    return _coerce(param, raw)


def _describe_param(param: ParamSpec, value: object) -> dict[str, object]:
    return {
        'name': param.name,
        'type': param.type,
        'default': param.default,
        'value': value,
        'description': param.description,
    }


def _require_spec(indicator: str) -> IndicatorSpec:
    spec = _SPEC_BY_NAME.get(indicator)
    if spec is None:
        known = ', '.join(_SPEC_BY_NAME)
        raise ConfigError(f'Unknown indicator {indicator!r}; known: {known}')
    return spec


def _require_param(spec: IndicatorSpec, param_name: str) -> ParamSpec:
    param = next((p for p in spec.params if p.name == param_name), None)
    if param is None:
        known = ', '.join(p.name for p in spec.params)
        raise ConfigError(f'Unknown parameter {param_name!r} for {spec.name!r}; known: {known}')
    return param


def _coerce(param: ParamSpec, raw: object) -> object:
    try:
        return _coerce_by_type(param.type, raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f'Invalid value for {param.name!r} ({param.type}): {raw!r}') from exc


def _coerce_by_type(type_tag: str, raw: object) -> object:
    if type_tag == TYPE_INT:
        return int(raw)
    if type_tag == TYPE_FLOAT:
        return float(raw)
    if type_tag in _LIST_TYPES:
        if not isinstance(raw, (list, tuple)):
            raise ValueError('expected a list')
        cast = int if type_tag == TYPE_INT_LIST else float
        return [cast(item) for item in raw]
    raise ValueError(f'unknown type tag {type_tag!r}')


def _copy(value: object) -> object:
    return list(value) if isinstance(value, (list, tuple)) else value
