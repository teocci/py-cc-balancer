'''Project-wide constants.

Holds default values, file/directory names, environment-variable keys, the
client-order-id prefix used to identify our orders on the exchange, and the
process exit codes. No environment-specific values are hardcoded elsewhere.
'''

from __future__ import annotations

from enum import IntEnum

__all__ = [
    'APP_NAME',
    'APP_DIR_NAME',
    'CONFIG_FILENAME',
    'ENV_FILENAME',
    'PORTFOLIO_FILENAME',
    'STATE_FILENAME',
    'HISTORY_FILENAME',
    'INDICATORS_FILENAME',
    'OHLCV_DIRNAME',
    'PROJECT_CONFIG_FILENAME',
    'CCB_PREFIX',
    'ENV_API_KEY',
    'ENV_API_SECRET',
    'ENV_EXCHANGE',
    'ENV_TESTNET',
    'ENV_CONFIG',
    'DEFAULT_EXCHANGE',
    'DEFAULT_TESTNET',
    'DEFAULT_QUOTE_SANITY_PCT',
    'DEFAULT_LIMIT_OFFSET_PCT',
    'DEFAULT_MIN_INTERVAL_HOURS',
    'DEFAULT_HTTP_TIMEOUT_MS',
    'DEFAULT_TARGET_VOLATILE_PCT',
    'DEFAULT_TARGET_STABLE_PCT',
    'DEFAULT_BAND_PCT',
    'DEFAULT_MIN_NOTIONAL',
    'DEFAULT_MAX_TRADE_NOTIONAL',
    'RATIO_TOTAL_PCT',
    'SUPPORTED_EXCHANGES',
    'DEFAULT_DATA_EXCHANGE',
    'DEFAULT_DECISION_TIMEFRAMES',
    'DEFAULT_ANALYSIS_TIMEFRAMES',
    'DEFAULT_OHLCV_LIMIT',
    'CACHE_STALE_FACTOR',
    'DEFAULT_RSI_PERIOD',
    'DEFAULT_RSI_OVERBOUGHT',
    'DEFAULT_RSI_OVERSOLD',
    'DEFAULT_MACD_FAST',
    'DEFAULT_MACD_SLOW',
    'DEFAULT_MACD_SIGNAL',
    'DEFAULT_EMA_PERIODS',
    'DEFAULT_BOLLINGER_PERIOD',
    'DEFAULT_BOLLINGER_STDDEV',
    'DEFAULT_ATR_PERIOD',
    'DEFAULT_VOLUME_MA_PERIOD',
    'FIB_RATIOS',
    'RSI_ZONE_OVERBOUGHT',
    'RSI_ZONE_OVERSOLD',
    'RSI_ZONE_NEUTRAL',
    'SCHEMA_VERSION',
    'ExitCode',
]

APP_NAME = 'ccbalancer'
APP_DIR_NAME = '.ccbalancer'

# File names within the app directory (~/.ccbalancer).
CONFIG_FILENAME = 'config.toml'
ENV_FILENAME = '.env'
PORTFOLIO_FILENAME = 'portfolio.json'
STATE_FILENAME = 'state.json'
HISTORY_FILENAME = 'history.jsonl'
# Indicator parameter overrides, kept out of config.toml (own concern, safely
# machine-rewritable by `indicator set`).
INDICATORS_FILENAME = 'indicators.toml'
# Subdirectory under the app dir holding cached OHLCV candles for indicators.
OHLCV_DIRNAME = 'ohlcv'
# Project-local config override found in the current working directory.
PROJECT_CONFIG_FILENAME = 'ccbalancer.toml'

# Prefix on clientOrderId to recognize orders placed by this tool.
CCB_PREFIX = 'ccb-'

# Environment-variable keys.
ENV_API_KEY = 'CCB_API_KEY'
ENV_API_SECRET = 'CCB_API_SECRET'
ENV_EXCHANGE = 'CCB_EXCHANGE'
ENV_TESTNET = 'CCB_TESTNET'
ENV_CONFIG = 'CCB_CONFIG'

# Settings defaults (overridable via TOML, then environment).
DEFAULT_EXCHANGE = 'bybit'
DEFAULT_TESTNET = True
DEFAULT_QUOTE_SANITY_PCT = 15.0
DEFAULT_LIMIT_OFFSET_PCT = 0.0
DEFAULT_MIN_INTERVAL_HOURS = 0
DEFAULT_HTTP_TIMEOUT_MS = 10000

# Per-pair defaults (applied when `pair add` omits a field).
DEFAULT_TARGET_VOLATILE_PCT = 80.0
DEFAULT_TARGET_STABLE_PCT = 20.0
DEFAULT_BAND_PCT = 5.0
DEFAULT_MIN_NOTIONAL = 10.0
DEFAULT_MAX_TRADE_NOTIONAL = 0.0

# A pair's volatile + stable target must sum to this.
RATIO_TOTAL_PCT = 100.0

# Exchanges supported via ccxt for this tool.
SUPPORTED_EXCHANGES = ('bybit', 'binance')

# Market intelligence (Phase 8). The data exchange supplies OHLCV and may differ
# from the trading exchange; an empty default means "use the trading exchange".
DEFAULT_DATA_EXCHANGE = ''
DEFAULT_DECISION_TIMEFRAMES = ('1m', '5m', '15m')
DEFAULT_ANALYSIS_TIMEFRAMES = ('1h', '4h', '1d', '1w')
# Number of candles fetched per timeframe (enough to seed EMA-200).
DEFAULT_OHLCV_LIMIT = 500
# Cached candles are stale once the newest is older than this many timeframes.
CACHE_STALE_FACTOR = 2

# Indicator parameters (see DESIGN.md "v1 indicators"). These are the built-in
# defaults; users override per-indicator via the [indicators.*] config tables.
DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_OVERBOUGHT = 70.0
DEFAULT_RSI_OVERSOLD = 30.0
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_EMA_PERIODS = (12, 26, 200)
DEFAULT_BOLLINGER_PERIOD = 20
DEFAULT_BOLLINGER_STDDEV = 2.0
DEFAULT_ATR_PERIOD = 14
DEFAULT_VOLUME_MA_PERIOD = 20
# Standard Fibonacci retracement ratios (0 = swing high, 1 = swing low).
FIB_RATIOS = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)

# Deterministic RSI zone labels (a comparison fact; the agent still judges).
RSI_ZONE_OVERBOUGHT = 'overbought'
RSI_ZONE_OVERSOLD = 'oversold'
RSI_ZONE_NEUTRAL = 'neutral'

# Version of the stable JSON contract emitted by read commands.
SCHEMA_VERSION = 1


class ExitCode(IntEnum):
    '''Process exit codes returned by the CLI.'''

    OK = 0
    CONFIG_ERROR = 2
    EXCHANGE_ERROR = 3
    ORDER_REJECTED = 4
    PARTIAL_FAILURE = 5
