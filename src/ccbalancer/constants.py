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


class ExitCode(IntEnum):
    '''Process exit codes returned by the CLI.'''

    OK = 0
    CONFIG_ERROR = 2
    EXCHANGE_ERROR = 3
    ORDER_REJECTED = 4
    PARTIAL_FAILURE = 5
