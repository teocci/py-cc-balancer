'''Application configuration: settings resolution and scaffolding.

Settings come from three layers with this precedence: environment variables →
TOML config file → built-in defaults. Credentials are resolved from the active
(or ``--profile``-selected) auth profile when one exists, falling back to the
``CCB_API_KEY``/``CCB_API_SECRET`` environment for back-compat; a resolved profile
also supplies its exchange and testnet flag (overridable by an explicit flag).

Discovery order for the config file (first existing wins): an explicit ``--config``
path, then ``$CCB_CONFIG``, then ``./ccbalancer.toml`` (project-local), then
``~/.ccbalancer/config.toml``. ``.env`` files are loaded from the CWD and the app
directory (real environment variables always win).
'''

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from ccbalancer import constants as c
from ccbalancer.exceptions import AuthError, ConfigError
from ccbalancer.models.auth_profile import AuthProfile
from ccbalancer.stores.auth_store import AuthStore, backend_for
from ccbalancer.utils import indicator_registry as registry

__all__ = [
    'Defaults',
    'SafetyConfig',
    'IndicatorSettings',
    'AppConfig',
    'load_config',
    'resolve_app_dir',
    'discover_config_path',
    'resolve_login_testnet',
    'masked_summary',
    'require_credentials',
    'init_app_dir',
    'read_indicator_overrides',
    'write_indicator_overrides',
]


@dataclass(slots=True, frozen=True)
class Defaults:
    '''Per-pair defaults applied when a pair omits a field.'''

    target_volatile_pct: float
    target_stable_pct: float
    band_pct: float
    min_notional: float
    max_trade_notional: float


@dataclass(slots=True, frozen=True)
class SafetyConfig:
    '''Execution safety guardrails (the ``[safety]`` config section).

    Attributes:
        max_session_notional_usd: Per-run cap on total notional placed across all
            pairs; ``0`` disables the cap (opt-out, unlimited).
        kill_switch_path: File whose presence aborts order placement.
    '''

    max_session_notional_usd: float
    kill_switch_path: Path


@dataclass(slots=True, frozen=True)
class IndicatorSettings:
    '''Resolved indicator parameters, keyed by indicator then parameter.

    Built by resolving ``indicators.toml`` overrides over the registry defaults
    (see :mod:`ccbalancer.utils.indicator_registry`). Kept dict-shaped rather
    than a fixed set of fields so new indicators need no change here — only a
    registry entry. These are *settings* (how indicators are computed and read),
    separate from the *registry* (which indicators exist) and from where they are
    stored (``indicators.toml``, its own file).

    Attributes:
        values: ``indicator -> {param -> value}`` for every registered indicator.
    '''

    values: dict[str, dict[str, object]] = field(default_factory=registry.default_values)

    def get(self, indicator: str, param: str) -> object:
        '''Return one resolved parameter value.'''
        return self.values[indicator][param]

    def section(self, indicator: str) -> dict[str, object]:
        '''Return all resolved parameters for one indicator.'''
        return self.values[indicator]


@dataclass(slots=True, frozen=True)
class AppConfig:
    '''Fully resolved application settings.

    Attributes:
        exchange: ccxt exchange id (validated against supported exchanges).
        testnet: Whether to use the exchange sandbox.
        quote_sanity_pct: Max allowed ticker deviation before rejecting it.
        limit_offset_pct: Limit-price offset from the touch.
        min_interval_hours: Optional cadence guard; 0 disables it.
        http_timeout_ms: Exchange HTTP timeout in milliseconds.
        http_retries: Max retries of transient failures on idempotent exchange calls.
        retry_backoff_ms: Base backoff between retries (doubled each attempt).
        target_review_band_pct: Price move (since target-set) that flags a regime review.
        data_exchange: ccxt exchange id supplying OHLCV (may differ from ``exchange``).
        decision_timeframes: Short cadence timeframes for decisions.
        analysis_timeframes: Longer timeframes for strategy analysis.
        ohlcv_limit: Number of candles fetched per timeframe.
        defaults: Per-pair default values.
        indicators: Resolved indicator parameters and thresholds.
        api_key: Resolved API key (from the active profile or env), or ``None``.
        api_secret: Resolved API secret (from the active profile or env), or ``None``.
        app_dir: The resolved ``~/.ccbalancer`` directory.
        config_path: The config file used, or ``None`` if none was found.
        indicators_path: Location of ``indicators.toml`` (read/written by the
            indicator commands), or ``None`` in synthetic configs.
        indicators: Resolved indicator parameters and thresholds.
        safety: Execution safety guardrails.
        profile: Name of the resolved auth profile, or ``None`` (legacy env path).
        password: Resolved passphrase for venues that require one (e.g. OKX), else ``None``.
    '''

    exchange: str
    testnet: bool
    quote_sanity_pct: float
    limit_offset_pct: float
    min_interval_hours: int
    http_timeout_ms: int
    target_review_band_pct: float
    data_exchange: str
    decision_timeframes: tuple[str, ...]
    analysis_timeframes: tuple[str, ...]
    ohlcv_limit: int
    defaults: Defaults
    safety: SafetyConfig
    api_key: str | None
    api_secret: str | None
    app_dir: Path
    config_path: Path | None
    http_retries: int = c.DEFAULT_HTTP_RETRIES
    retry_backoff_ms: int = c.DEFAULT_RETRY_BACKOFF_MS
    indicators_path: Path | None = None
    indicators: IndicatorSettings = field(default_factory=IndicatorSettings)
    profile: str | None = None
    password: str | None = None


def resolve_app_dir() -> Path:
    '''Return the per-user app directory ``~/.ccbalancer``.'''
    return Path.home() / c.APP_DIR_NAME


def discover_config_path(cli_config: str | None, app_dir: Path) -> Path | None:
    '''Find the config file by precedence; return ``None`` if none exists.

    Args:
        cli_config: Explicit path from ``--config``, if given.
        app_dir: The resolved app directory.
    '''
    candidates = [
        cli_config,
        os.getenv(c.ENV_CONFIG),
        c.PROJECT_CONFIG_FILENAME,
        str(app_dir / c.CONFIG_FILENAME),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def load_config(
    cli_config: str | None = None,
    exchange_override: str | None = None,
    testnet_override: bool | None = None,
    profile_override: str | None = None,
    auth_store: AuthStore | None = None,
) -> AppConfig:
    '''Resolve settings from the auth profile, env, TOML, and defaults.

    Args:
        cli_config: Explicit config path from ``--config``.
        exchange_override: Exchange id from ``--exchange``.
        testnet_override: Value from ``--testnet/--no-testnet``.
        profile_override: Profile name from ``--profile``.
        auth_store: Injected store (tests); built from the app dir when ``None``.

    Returns:
        The resolved :class:`AppConfig`.

    Raises:
        ConfigError: If the config file is unreadable or the exchange is unsupported.
        AuthError: If a selected profile name does not exist.
    '''
    app_dir = resolve_app_dir()
    _load_dotenv(app_dir)
    config_path = discover_config_path(cli_config, app_dir)
    glob = _read_section(config_path, 'global')
    defaults = _build_defaults(_read_section(config_path, 'defaults'))
    safety = _build_safety(_read_section(config_path, 'safety'), app_dir)
    profile = _resolve_profile(app_dir, profile_override, auth_store)

    exchange = _resolve_exchange(exchange_override, profile, glob)
    testnet = _resolve_testnet(testnet_override, glob, profile)
    data_exchange = _resolve_data_exchange(glob, exchange)
    indicators_path = app_dir / c.INDICATORS_FILENAME

    return AppConfig(
        exchange=exchange,
        testnet=testnet,
        quote_sanity_pct=float(glob.get('quote_sanity_pct', c.DEFAULT_QUOTE_SANITY_PCT)),
        limit_offset_pct=float(glob.get('limit_offset_pct', c.DEFAULT_LIMIT_OFFSET_PCT)),
        min_interval_hours=int(glob.get('min_interval_hours', c.DEFAULT_MIN_INTERVAL_HOURS)),
        http_timeout_ms=int(glob.get('http_timeout_ms', c.DEFAULT_HTTP_TIMEOUT_MS)),
        http_retries=int(glob.get('http_retries', c.DEFAULT_HTTP_RETRIES)),
        retry_backoff_ms=int(glob.get('retry_backoff_ms', c.DEFAULT_RETRY_BACKOFF_MS)),
        target_review_band_pct=float(
            glob.get('target_review_band_pct', c.DEFAULT_TARGET_REVIEW_BAND_PCT)
        ),
        data_exchange=data_exchange,
        decision_timeframes=_resolve_timeframes(glob, 'decision_timeframes', c.DEFAULT_DECISION_TIMEFRAMES),
        analysis_timeframes=_resolve_timeframes(glob, 'analysis_timeframes', c.DEFAULT_ANALYSIS_TIMEFRAMES),
        ohlcv_limit=int(glob.get('ohlcv_limit', c.DEFAULT_OHLCV_LIMIT)),
        defaults=defaults,
        safety=safety,
        api_key=profile.api_key if profile else os.getenv(c.ENV_API_KEY),
        api_secret=profile.api_secret if profile else os.getenv(c.ENV_API_SECRET),
        app_dir=app_dir,
        config_path=config_path,
        indicators_path=indicators_path,
        indicators=IndicatorSettings(registry.resolve(read_indicator_overrides(indicators_path))),
        profile=profile.name if profile else None,
        password=profile.password if profile else None,
    )


def _resolve_profile(
    app_dir: Path,
    profile_override: str | None,
    auth_store: AuthStore | None,
) -> AuthProfile | None:
    '''Resolve the active profile: ``--profile`` > ``CCB_PROFILE`` > active pointer.

    Returns ``None`` when no profile is selected (the legacy env credential path).

    Raises:
        AuthError: If a selected profile name does not exist.
    '''
    auth_path = app_dir / c.AUTH_FILENAME
    store = auth_store or AuthStore(auth_path, backend_for(auth_path))
    name = profile_override or os.getenv(c.ENV_PROFILE) or store.active_name()
    if name is None:
        return None
    profile = store.get(name)
    if profile is None:
        raise AuthError(f'Profile {name!r} not found; run `ccbalancer auth list`')
    return profile


def _resolve_exchange(
    override: str | None,
    profile: AuthProfile | None,
    glob: dict[str, object],
) -> str:
    source = override or (profile.exchange if profile else None) or os.getenv(c.ENV_EXCHANGE)
    exchange = (source or glob.get('exchange', c.DEFAULT_EXCHANGE)).lower()
    _validate_exchange(exchange)
    return exchange


def resolve_login_testnet(override: bool | None, cli_config: str | None = None) -> bool:
    '''Resolve the testnet flag for ``auth login`` using the app-wide precedence.

    Mirrors the resolution every other command uses (explicit flag > ``CCB_TESTNET``
    env > TOML ``[global] testnet`` > default) so a profile created by ``auth login``
    targets the same venue the rest of the tool would. No profile is consulted: the
    profile being created is what defines its own venue.

    Args:
        override: Value from ``--testnet/--no-testnet`` (``None`` if unset).
        cli_config: Explicit config path from ``--config``.
    '''
    app_dir = resolve_app_dir()
    _load_dotenv(app_dir)
    glob = _read_section(discover_config_path(cli_config, app_dir), 'global')
    return _resolve_testnet(override, glob, None)


def require_credentials(config: AppConfig) -> tuple[str, str]:
    '''Return (api_key, api_secret) or raise if either is missing.

    Raises:
        ConfigError: If credentials are not set in the environment.
    '''
    if not config.api_key or not config.api_secret:
        raise ConfigError(
            'Missing API credentials; add a profile with `ccbalancer auth login` or set '
            f'{c.ENV_API_KEY} and {c.ENV_API_SECRET} in {config.app_dir / c.ENV_FILENAME}'
        )
    return config.api_key, config.api_secret


def masked_summary(config: AppConfig) -> dict[str, object]:
    '''Build a serializable settings summary with secrets masked.'''
    return {
        'exchange': config.exchange,
        'testnet': config.testnet,
        'quote_sanity_pct': config.quote_sanity_pct,
        'limit_offset_pct': config.limit_offset_pct,
        'min_interval_hours': config.min_interval_hours,
        'http_timeout_ms': config.http_timeout_ms,
        'http_retries': config.http_retries,
        'retry_backoff_ms': config.retry_backoff_ms,
        'target_review_band_pct': config.target_review_band_pct,
        'data_exchange': config.data_exchange,
        'decision_timeframes': list(config.decision_timeframes),
        'analysis_timeframes': list(config.analysis_timeframes),
        'ohlcv_limit': config.ohlcv_limit,
        'defaults': {
            'target_volatile_pct': config.defaults.target_volatile_pct,
            'target_stable_pct': config.defaults.target_stable_pct,
            'band_pct': config.defaults.band_pct,
            'min_notional': config.defaults.min_notional,
            'max_trade_notional': config.defaults.max_trade_notional,
        },
        'safety': {
            'max_session_notional_usd': config.safety.max_session_notional_usd,
            'kill_switch_path': str(config.safety.kill_switch_path),
        },
        'profile': config.profile,
        'api_key': _mask(config.api_key),
        'api_secret': _mask(config.api_secret),
        'password': _mask(config.password),
        'app_dir': str(config.app_dir),
        'config_path': str(config.config_path) if config.config_path else None,
    }


def init_app_dir(app_dir: Path) -> list[Path]:
    '''Scaffold the app directory with config/.env templates if missing.

    Args:
        app_dir: Directory to create and populate.

    Returns:
        The list of files newly created (existing files are left untouched).
    '''
    app_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    created += _write_if_absent(app_dir / c.CONFIG_FILENAME, CONFIG_TEMPLATE)
    created += _write_if_absent(app_dir / c.INDICATORS_FILENAME, INDICATORS_TEMPLATE)
    env_path = app_dir / c.ENV_FILENAME
    created += _write_if_absent(env_path, ENV_TEMPLATE)
    _restrict_permissions(env_path)
    return created


def _load_dotenv(app_dir: Path) -> None:
    # CWD wins over the app dir; real environment variables win over both.
    load_dotenv(Path.cwd() / c.ENV_FILENAME, override=False)
    load_dotenv(app_dir / c.ENV_FILENAME, override=False)


def _read_section(config_path: Path | None, name: str) -> dict[str, object]:
    if config_path is None:
        return {}
    try:
        with open(config_path, 'rb') as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f'Cannot read config {config_path}: {exc}') from exc
    section = data.get(name, {})
    if not isinstance(section, dict):
        raise ConfigError(f'Config section [{name}] must be a table')
    return section


def _build_defaults(section: dict[str, object]) -> Defaults:
    return Defaults(
        target_volatile_pct=float(section.get('target_volatile_pct', c.DEFAULT_TARGET_VOLATILE_PCT)),
        target_stable_pct=float(section.get('target_stable_pct', c.DEFAULT_TARGET_STABLE_PCT)),
        band_pct=float(section.get('band_pct', c.DEFAULT_BAND_PCT)),
        min_notional=float(section.get('min_notional', c.DEFAULT_MIN_NOTIONAL)),
        max_trade_notional=float(section.get('max_trade_notional', c.DEFAULT_MAX_TRADE_NOTIONAL)),
    )


def _build_safety(section: dict[str, object], app_dir: Path) -> SafetyConfig:
    raw_switch = section.get('kill_switch_path')
    kill_switch_path = Path(str(raw_switch)) if raw_switch else app_dir / c.KILL_SWITCH_FILENAME
    return SafetyConfig(
        max_session_notional_usd=float(
            section.get('max_session_notional_usd', c.DEFAULT_MAX_SESSION_NOTIONAL_USD)
        ),
        kill_switch_path=kill_switch_path,
    )


def read_indicator_overrides(path: Path | None) -> dict[str, object]:
    '''Return raw indicator overrides parsed from ``indicators.toml``.

    Returns an empty mapping if the file is absent. The result is the on-disk
    overrides only (not merged with defaults); pass it to
    :func:`indicator_registry.resolve` to validate and merge.

    Raises:
        ConfigError: If the file exists but cannot be parsed.
    '''
    if path is None or not path.is_file():
        return {}
    try:
        with open(path, 'rb') as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f'Cannot read indicators {path}: {exc}') from exc


def write_indicator_overrides(path: Path, overrides: dict[str, dict[str, object]]) -> None:
    '''Write indicator overrides to ``indicators.toml`` (atomic, machine-owned).

    Only the overridden parameters are persisted; omitted ones fall back to the
    registry defaults on the next read.
    '''
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _render_indicators_toml(overrides)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(body, encoding='utf-8')
    tmp.replace(path)


def _render_indicators_toml(overrides: dict[str, dict[str, object]]) -> str:
    lines = ['# Managed by ccbalancer. Indicator parameter overrides.',
             '# Discover available indicators and parameters with `ccbalancer indicators`.', '']
    for indicator, params in overrides.items():
        if not params:
            continue
        lines.append(f'[{indicator}]')
        lines.extend(f'{name} = {_toml_value(value)}' for name, value in params.items())
        lines.append('')
    return '\n'.join(lines)


def _toml_value(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return '[' + ', '.join(_toml_value(item) for item in value) + ']'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return repr(value) if isinstance(value, float) else str(value)


def _resolve_testnet(
    override: bool | None,
    glob: dict[str, object],
    profile: AuthProfile | None = None,
) -> bool:
    # Precedence: explicit flag > profile > env > TOML > default. A profile owns
    # its account, so it outranks a stray CCB_TESTNET in the shell.
    if override is not None:
        return override
    if profile is not None:
        return profile.testnet
    env_value = os.getenv(c.ENV_TESTNET)
    if env_value is not None:
        return _parse_bool(env_value)
    return bool(glob.get('testnet', c.DEFAULT_TESTNET))


def _validate_exchange(exchange: str) -> None:
    if exchange not in c.SUPPORTED_EXCHANGES:
        supported = ', '.join(c.SUPPORTED_EXCHANGES)
        raise ConfigError(f'Unsupported exchange {exchange!r}; choose one of: {supported}')


def _resolve_data_exchange(glob: dict[str, object], trading_exchange: str) -> str:
    configured = str(glob.get('data_exchange', c.DEFAULT_DATA_EXCHANGE)).lower()
    data_exchange = configured or trading_exchange
    _validate_exchange(data_exchange)
    return data_exchange


def _resolve_timeframes(glob: dict[str, object], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = glob.get(key)
    if raw is None:
        return default
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigError(f'Config [global] {key} must be a list of timeframe strings')
    return tuple(raw)


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _mask(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return '***'
    return f'{secret[:4]}...{secret[-4:]}'


def _write_if_absent(path: Path, content: str) -> list[Path]:
    if path.exists():
        return []
    path.write_text(content, encoding='utf-8')
    return [path]


def _restrict_permissions(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        # Best-effort on platforms without POSIX permissions (e.g. Windows).
        pass


CONFIG_TEMPLATE = '''[global]
exchange = 'bybit'          # ccxt id; 'binance' switchable
testnet = true
quote_sanity_pct = 15.0     # reject ticker deviating > this vs recent
limit_offset_pct = 0.0      # limit price offset from touch (0 = at best bid/ask)
min_interval_hours = 0      # optional TOO_SOON guard; 0 = disabled (agent owns cadence)
http_timeout_ms = 10000
http_retries = 2            # retries of transient failures on idempotent calls (reads + cancel)
retry_backoff_ms = 500      # base backoff between retries, doubled each attempt
target_review_band_pct = 20.0   # flag a target-ratio review once price moves > this since target-set
data_exchange = ''          # OHLCV source; '' = use the trading exchange
decision_timeframes = ['1m', '5m', '15m']   # short cadence timeframes
analysis_timeframes = ['1h', '4h', '1d', '1w']   # longer strategy timeframes
ohlcv_limit = 500           # candles fetched per timeframe

[defaults]                  # applied when `pair add` omits a field
target_volatile_pct = 80.0
target_stable_pct   = 20.0
band_pct            = 5.0
min_notional        = 10.0
max_trade_notional  = 0.0   # 0 = no cap

[safety]                    # execution guardrails (rebalance is dry-run by default)
max_session_notional_usd = 1000.0   # per-run cap on total notional placed; 0 = unlimited
# kill_switch_path = ''     # defaults to ~/.ccbalancer/STOP; create it to block all placement
# Use a trade-only API key (no withdrawal scope) for CCB_API_KEY / CCB_API_SECRET.
'''

INDICATORS_TEMPLATE = '''# Indicator parameter overrides for ccbalancer.
# This file is its own concern (kept out of config.toml) and may be rewritten by
# `ccbalancer indicator set`. Every table and key is optional; omitted ones fall
# back to built-in defaults. The set of available indicators is fixed in code;
# discover them and their parameters with `ccbalancer indicators`.

[rsi]
period     = 14
overbought = 70.0           # the CLI reports an rsi_zone vs these; it never acts
oversold   = 30.0

[macd]
fast   = 12
slow   = 26
signal = 9

[ema]
periods = [12, 26, 200]

[bollinger]
period = 20
stddev = 2.0

[atr]
period = 14

[volume]
ma_period = 20

[fib]
ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
'''

ENV_TEMPLATE = '''# Secrets for ccbalancer. Never commit this file.
# Preferred: manage credentials with `ccbalancer auth login` (multi-account,
# OS-keyring storage). These env vars remain a single-account fallback for CI.
CCB_API_KEY=
CCB_API_SECRET=
# Optional non-secret overrides:
# CCB_EXCHANGE=bybit
# CCB_TESTNET=true
# CCB_PROFILE=bybit-main   # select an auth profile by name
'''
