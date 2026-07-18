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
    'AUTH_FILENAME',
    'PORTFOLIO_FILENAME',
    'STATE_FILENAME',
    'HISTORY_FILENAME',
    'DECISION_LOG_FILENAME',
    'LEDGER_FILENAME',
    'OPEN_ORDERS_FILENAME',
    'FLAGS_FILENAME',
    'INDICATORS_FILENAME',
    'OHLCV_DIRNAME',
    'SIMULATION_DIRNAME',
    'SIM_OHLCV_DIRNAME',
    'SIM_MANIFEST_FILENAME',
    'SIM_FETCH_PAGE_LIMIT',
    'SIM_DEFAULT_TIMEFRAMES',
    'SIM_LTF_TIMEFRAMES',
    'BINANCE_KLINES_URL',
    'BINANCE_KLINES_LIMIT',
    'BINANCE_KLINES_RETRY_STATUS',
    'BINANCE_KLINES_BLOCKED_STATUS',
    'BINANCE_ARCHIVE_URL',
    'BINANCE_KLINES_RETRIES',
    'BINANCE_KLINES_BACKOFF_MS',
    'SIM_RUNS_DIRNAME',
    'SIM_LEDGER_FILENAME',
    'SIM_RUN_FILENAME',
    'SIM_DEFAULT_DECISION_TIMEFRAME',
    'SIM_DEFAULT_CAPITAL',
    'SIM_DEFAULT_FEE_RATE',
    'SIM_DEFAULT_AMOUNT_PRECISION',
    'SIM_DEFAULT_MIN_COST',
    'PAPER_BOOK_FILENAME',
    'DEFAULT_PAPER_CAPITAL',
    'DEFAULT_PAPER_QUOTE',
    'DEFAULT_PAPER_FEE_RATE',
    'ACCOUNTS_DIRNAME',
    'DEFAULT_ACCOUNT_SCOPE',
    'KILL_SWITCH_FILENAME',
    'PROJECT_CONFIG_FILENAME',
    'CCB_PREFIX',
    'ENV_API_KEY',
    'ENV_API_SECRET',
    'ENV_PASSPHRASE',
    'ENV_EXCHANGE',
    'ENV_TESTNET',
    'ENV_CONFIG',
    'ENV_ACCOUNT',
    'ENV_PROFILE',
    'ENV_AUTH_BACKEND',
    'AUTH_KEYRING_SERVICE',
    'DEFAULT_AUTH_BACKEND',
    'DEFAULT_EXCHANGE',
    'DEFAULT_TESTNET',
    'DEFAULT_QUOTE_SANITY_PCT',
    'DEFAULT_LIMIT_OFFSET_PCT',
    'DEFAULT_MIN_INTERVAL_HOURS',
    'DEFAULT_HTTP_TIMEOUT_MS',
    'DEFAULT_HTTP_RETRIES',
    'DEFAULT_RETRY_BACKOFF_MS',
    'DEFAULT_MAX_SESSION_NOTIONAL_USD',
    'CONFIRM_TOKEN_LENGTH',
    'DEFAULT_TARGET_VOLATILE_PCT',
    'DEFAULT_TARGET_STABLE_PCT',
    'DEFAULT_BAND_PCT',
    'DEFAULT_MIN_NOTIONAL',
    'DEFAULT_MAX_TRADE_NOTIONAL',
    'DEFAULT_TARGET_REVIEW_BAND_PCT',
    'REGIME_SCENARIO_VOLATILE_PCTS',
    'MILESTONE_METRICS',
    'MILESTONE_OPS',
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
    'DEFAULT_ADX_PERIOD',
    'DEFAULT_ADX_THRESHOLD',
    'DEFAULT_SR_PIVOT_LOOKBACK',
    'DEFAULT_SR_CLUSTER_PCT',
    'DEFAULT_SR_MAX_LEVELS',
    'FIB_RATIOS',
    'RSI_ZONE_OVERBOUGHT',
    'RSI_ZONE_OVERSOLD',
    'RSI_ZONE_NEUTRAL',
    'ADX_TREND_TRENDING',
    'ADX_TREND_RANGING',
    'SCHEMA_VERSION',
    'ExitCode',
]

APP_NAME = 'ccbalancer'
APP_DIR_NAME = '.ccbalancer'

# File names within the app directory (~/.ccbalancer).
CONFIG_FILENAME = 'config.toml'
ENV_FILENAME = '.env'
# Auth accounts store (gh-style multi-account credentials). Holds account metadata
# and the active pointer; secrets live inline (file backend) or in the OS keyring.
AUTH_FILENAME = 'auth.json'
PORTFOLIO_FILENAME = 'portfolio.json'
STATE_FILENAME = 'state.json'
HISTORY_FILENAME = 'history.jsonl'
# Append-only log of every rebalance decision (inputs + guard ladder + order),
# written on `plan`/`rebalance`; the offline decision memory read by `decisions`.
DECISION_LOG_FILENAME = 'decision_log.jsonl'
# Append-only log of executed fills (price, qty, fee, side); the cost-basis source.
LEDGER_FILENAME = 'ledger.jsonl'
# Outstanding orders awaiting reconciliation (keyed by client-order-id); written
# write-ahead at placement, drained as the reconciler books their real fills (F-6).
OPEN_ORDERS_FILENAME = 'open_orders.json'
# Agent/user milestones and watch-conditions, managed by the `flag` commands.
FLAGS_FILENAME = 'flags.json'
# Indicator parameter overrides, kept out of config.toml (own concern, safely
# machine-rewritable by `indicator set`).
INDICATORS_FILENAME = 'indicators.toml'
# Subdirectory under the app dir holding cached OHLCV candles for indicators.
OHLCV_DIRNAME = 'ohlcv'
# Backtest historical-data tree under the app dir: append-only, resumable OHLCV
# per {exchange}/{symbol}/{timeframe}.jsonl plus a per-symbol manifest. Distinct
# from OHLCV_DIRNAME (the overwrite-on-write indicator cache) — this one never
# re-downloads a range, only appends the missing tail since the last closed candle.
SIMULATION_DIRNAME = 'simulation'
SIM_OHLCV_DIRNAME = 'ohlcv'
SIM_MANIFEST_FILENAME = 'manifest.json'
# ccxt page size for the paginated range fetch (venue max is typically 1000).
SIM_FETCH_PAGE_LIMIT = 1000
# Timeframes fetched by default for a full-cycle backtest. Includes 15m — the
# coarsest execution timeframe (DESIGN decision_timeframes = 1m/5m/15m) — which
# ccxt paginates comfortably; deeper 1m/5m is opt-in via --timeframe and routes to
# the Binance REST klines fallback below.
SIM_DEFAULT_TIMEFRAMES = ('15m', '1h', '4h', '1d')
# Sub-daily timeframes routed to the Binance REST klines fallback instead of the
# ccxt pager, where candle volume makes ccxt pagination impractical. Higher
# timeframes — including 15m — stay on ccxt fetch_ohlcv_range (I-12).
SIM_LTF_TIMEFRAMES = ('1m', '5m')
# Binance public REST klines endpoint — no API key (public market data). Used only
# by stores/history_fetch.py for deep 1m/5m backfill; managers never do network.
BINANCE_KLINES_URL = 'https://api.binance.com/api/v3/klines'
# Venue page cap for /api/v3/klines (max 1000 rows/call, mirrors the ccxt pager).
BINANCE_KLINES_LIMIT = 1000
# HTTP statuses worth a backoff-and-retry: 429 rate-limit, 418 IP auto-ban.
BINANCE_KLINES_RETRY_STATUS = (429, 418)
# HTTP 451 = legal block on the API host; the documented fallback is the bulk
# archive at data.binance.vision, surfaced in the raised error.
BINANCE_KLINES_BLOCKED_STATUS = 451
BINANCE_ARCHIVE_URL = 'https://data.binance.vision'
# Retry budget and base backoff (ms, doubled each attempt) for the klines fetcher.
BINANCE_KLINES_RETRIES = 5
BINANCE_KLINES_BACKOFF_MS = 500
# Backtest run artifacts under the simulation tree: one directory per run (keyed by
# a deterministic hash of the run inputs) holding the isolated sim ledger + params.
SIM_RUNS_DIRNAME = 'runs'
SIM_LEDGER_FILENAME = 'ledger.jsonl'
SIM_RUN_FILENAME = 'run.json'
# Replay defaults. The MVP decides on the daily close; fee is a maker rate applied
# to each simulated fill's notional; amount precision floors order sizing; min-cost
# is the exchange-floor below which the sim rejects an order (0 = no floor).
SIM_DEFAULT_DECISION_TIMEFRAME = '1d'
SIM_DEFAULT_CAPITAL = 10000.0
SIM_DEFAULT_FEE_RATE = 0.001
SIM_DEFAULT_AMOUNT_PRECISION = 8
SIM_DEFAULT_MIN_COST = 0.0
# Paper (simulated-exchange) account: the per-account book file holding the
# simulated balances + resting orders, the initial all-stable capital seeded at
# `auth login --paper`, and the maker fee applied to each simulated fill.
PAPER_BOOK_FILENAME = 'paper_book.json'
DEFAULT_PAPER_CAPITAL = 10000.0
DEFAULT_PAPER_QUOTE = 'USDT'
DEFAULT_PAPER_FEE_RATE = 0.001
# Per-account books live under <app_dir>/accounts/<account-id>/. Each account's
# portfolio/state/ledger/decisions/flags are isolated by its stable id; the
# no-account env-credential path uses the 'default' scope.
ACCOUNTS_DIRNAME = 'accounts'
DEFAULT_ACCOUNT_SCOPE = 'default'
# Project-local config override found in the current working directory.
PROJECT_CONFIG_FILENAME = 'ccbalancer.toml'
# Presence of this file under the app dir blocks order placement (a manual abort
# switch the user can drop in to stop all execution); `cancel` is never blocked.
KILL_SWITCH_FILENAME = 'STOP'

# Prefix on clientOrderId to recognize orders placed by this tool.
CCB_PREFIX = 'ccb-'

# Environment-variable keys.
ENV_API_KEY = 'CCB_API_KEY'
ENV_API_SECRET = 'CCB_API_SECRET'
# Passphrase for venues that require a third credential (e.g. OKX's OK-ACCESS-PASSPHRASE).
ENV_PASSPHRASE = 'CCB_PASSPHRASE'
ENV_EXCHANGE = 'CCB_EXCHANGE'
ENV_TESTNET = 'CCB_TESTNET'
ENV_CONFIG = 'CCB_CONFIG'
# Selects the active auth account for one invocation (overridden by --account).
ENV_ACCOUNT = 'CCB_ACCOUNT'
# Deprecated alias for ENV_ACCOUNT; still honored as a fallback for back-compat.
ENV_PROFILE = 'CCB_PROFILE'
# Forces the secret-storage backend: 'keyring' or 'file'.
ENV_AUTH_BACKEND = 'CCB_AUTH_BACKEND'

# Service name under which credentials are stored in the OS keyring.
AUTH_KEYRING_SERVICE = 'ccbalancer'
# Default secret-storage backend; 'keyring' falls back to the 'file' backend when
# the keyring package or an OS backend is unavailable (e.g. headless CI).
DEFAULT_AUTH_BACKEND = 'keyring'

# Settings defaults (overridable via TOML, then environment).
DEFAULT_EXCHANGE = 'bybit'
DEFAULT_TESTNET = True
DEFAULT_QUOTE_SANITY_PCT = 15.0
DEFAULT_LIMIT_OFFSET_PCT = 0.0
DEFAULT_MIN_INTERVAL_HOURS = 0
DEFAULT_HTTP_TIMEOUT_MS = 10000
# Bounded retry of transient exchange failures (timeouts, DDoS protection, venue
# unavailable). Applied only to idempotent calls (reads + cancel); order placement
# never auto-retries, since a timed-out create may have landed (see exchange.py).
DEFAULT_HTTP_RETRIES = 2
# Base backoff between retries; doubled each attempt (exponential).
DEFAULT_RETRY_BACKOFF_MS = 500
# Per-run cap on total notional placed across all pairs (a safety backstop, since
# the intent-level confirm-token does not bound magnitude). 0 = unlimited (opt-out).
DEFAULT_MAX_SESSION_NOTIONAL_USD = 1000.0
# Hex length of the confirm-token issued by `plan` and required by `rebalance`.
CONFIRM_TOKEN_LENGTH = 12

# Per-pair defaults (applied when `pair add` omits a field).
DEFAULT_TARGET_VOLATILE_PCT = 80.0
DEFAULT_TARGET_STABLE_PCT = 20.0
DEFAULT_BAND_PCT = 5.0
DEFAULT_MIN_NOTIONAL = 10.0
DEFAULT_MAX_TRADE_NOTIONAL = 0.0

# A pair's volatile + stable target must sum to this.
RATIO_TOTAL_PCT = 100.0

# Regime / price-variance-since-target-set (DESIGN.md signal #3). The CLI flags
# the target ratio for review once price has moved more than this percent since
# the ratio was set (`pair set --target-set-price`). Wider than the allocation
# band: a trade-trigger is routine; a strategy review is not.
DEFAULT_TARGET_REVIEW_BAND_PCT = 20.0
# Fixed ladder of candidate volatile shares used for the regime what-if scenarios
# and the deterministic suggested-ratio step (the pair's current target is always
# added as a rung). Descending = most to least at-risk.
REGIME_SCENARIO_VOLATILE_PCTS = (80.0, 50.0, 25.0)

# Milestone watch-conditions (agent-defined flags). Metrics are read from the live
# per-pair snapshot/decision; operators use word forms to avoid shell quoting of
# `<`/`>`. Each maps to its human comparison symbol.
MILESTONE_METRICS = ('price', 'drift_pct', 'volatile_pct', 'value')
MILESTONE_OPS = {'ge': '>=', 'le': '<=', 'gt': '>', 'lt': '<', 'eq': '=='}

# Exchanges supported via ccxt for this tool. OKX additionally requires a
# passphrase credential (handled generically via the exchange's requiredCredentials).
SUPPORTED_EXCHANGES = ('bybit', 'binance', 'okx')

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
# ADX (Average Directional Index): Wilder lookback and the trend-strength cutoff
# above which the trend is labelled "trending" rather than "ranging".
DEFAULT_ADX_PERIOD = 14
DEFAULT_ADX_THRESHOLD = 25.0
# Support/Resistance swing-pivot detector: bars of confirmation on each side of a
# pivot, the percent tolerance that merges nearby pivots into one level, and the
# cap on levels reported per side.
DEFAULT_SR_PIVOT_LOOKBACK = 2
DEFAULT_SR_CLUSTER_PCT = 0.5
DEFAULT_SR_MAX_LEVELS = 5
# Standard Fibonacci retracement ratios (0 = swing high, 1 = swing low).
FIB_RATIOS = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)

# Deterministic RSI zone labels (a comparison fact; the agent still judges).
RSI_ZONE_OVERBOUGHT = 'overbought'
RSI_ZONE_OVERSOLD = 'oversold'
RSI_ZONE_NEUTRAL = 'neutral'

# Deterministic ADX trend labels vs the configured threshold (a comparison fact).
ADX_TREND_TRENDING = 'trending'
ADX_TREND_RANGING = 'ranging'

# Version of the stable JSON contract emitted by read commands. Bumped to 2 when
# `analyze` gained the adx{} block and supports[]/resistances[] level lists.
SCHEMA_VERSION = 2


class ExitCode(IntEnum):
    '''Process exit codes returned by the CLI.'''

    OK = 0
    CONFIG_ERROR = 2
    EXCHANGE_ERROR = 3
    ORDER_REJECTED = 4
    PARTIAL_FAILURE = 5
    SAFETY_BLOCKED = 6
