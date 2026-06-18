'''Application configuration: settings resolution and scaffolding.

Settings come from three layers with this precedence: environment variables →
TOML config file → built-in defaults. Secrets (API key/secret) are resolved from
the environment only and are never read from the TOML file.

Discovery order for the config file (first existing wins): an explicit ``--config``
path, then ``$CCB_CONFIG``, then ``./ccbalancer.toml`` (project-local), then
``~/.ccbalancer/config.toml``. ``.env`` files are loaded from the CWD and the app
directory (real environment variables always win).
'''

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from ccbalancer import constants as c
from ccbalancer.exceptions import ConfigError

__all__ = [
    'Defaults',
    'AppConfig',
    'load_config',
    'resolve_app_dir',
    'discover_config_path',
    'masked_summary',
    'require_credentials',
    'init_app_dir',
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
class AppConfig:
    '''Fully resolved application settings.

    Attributes:
        exchange: ccxt exchange id (validated against supported exchanges).
        testnet: Whether to use the exchange sandbox.
        quote_sanity_pct: Max allowed ticker deviation before rejecting it.
        limit_offset_pct: Limit-price offset from the touch.
        min_interval_hours: Optional cadence guard; 0 disables it.
        http_timeout_ms: Exchange HTTP timeout in milliseconds.
        defaults: Per-pair default values.
        api_key: API key from the environment, or ``None``.
        api_secret: API secret from the environment, or ``None``.
        app_dir: The resolved ``~/.ccbalancer`` directory.
        config_path: The config file used, or ``None`` if none was found.
    '''

    exchange: str
    testnet: bool
    quote_sanity_pct: float
    limit_offset_pct: float
    min_interval_hours: int
    http_timeout_ms: int
    defaults: Defaults
    api_key: str | None
    api_secret: str | None
    app_dir: Path
    config_path: Path | None


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
) -> AppConfig:
    '''Resolve settings from env, TOML, and defaults.

    Args:
        cli_config: Explicit config path from ``--config``.
        exchange_override: Exchange id from ``--exchange``.
        testnet_override: Value from ``--testnet/--no-testnet``.

    Returns:
        The resolved :class:`AppConfig`.

    Raises:
        ConfigError: If the config file is unreadable or the exchange is unsupported.
    '''
    app_dir = resolve_app_dir()
    _load_dotenv(app_dir)
    config_path = discover_config_path(cli_config, app_dir)
    glob = _read_section(config_path, 'global')
    defaults = _build_defaults(_read_section(config_path, 'defaults'))

    exchange = (exchange_override or os.getenv(c.ENV_EXCHANGE) or glob.get('exchange', c.DEFAULT_EXCHANGE)).lower()
    _validate_exchange(exchange)
    testnet = _resolve_testnet(testnet_override, glob)

    return AppConfig(
        exchange=exchange,
        testnet=testnet,
        quote_sanity_pct=float(glob.get('quote_sanity_pct', c.DEFAULT_QUOTE_SANITY_PCT)),
        limit_offset_pct=float(glob.get('limit_offset_pct', c.DEFAULT_LIMIT_OFFSET_PCT)),
        min_interval_hours=int(glob.get('min_interval_hours', c.DEFAULT_MIN_INTERVAL_HOURS)),
        http_timeout_ms=int(glob.get('http_timeout_ms', c.DEFAULT_HTTP_TIMEOUT_MS)),
        defaults=defaults,
        api_key=os.getenv(c.ENV_API_KEY),
        api_secret=os.getenv(c.ENV_API_SECRET),
        app_dir=app_dir,
        config_path=config_path,
    )


def require_credentials(config: AppConfig) -> tuple[str, str]:
    '''Return (api_key, api_secret) or raise if either is missing.

    Raises:
        ConfigError: If credentials are not set in the environment.
    '''
    if not config.api_key or not config.api_secret:
        raise ConfigError(
            f'Missing API credentials; set {c.ENV_API_KEY} and {c.ENV_API_SECRET} '
            f'in {config.app_dir / c.ENV_FILENAME}'
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
        'defaults': {
            'target_volatile_pct': config.defaults.target_volatile_pct,
            'target_stable_pct': config.defaults.target_stable_pct,
            'band_pct': config.defaults.band_pct,
            'min_notional': config.defaults.min_notional,
            'max_trade_notional': config.defaults.max_trade_notional,
        },
        'api_key': _mask(config.api_key),
        'api_secret': _mask(config.api_secret),
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


def _resolve_testnet(override: bool | None, glob: dict[str, object]) -> bool:
    if override is not None:
        return override
    env_value = os.getenv(c.ENV_TESTNET)
    if env_value is not None:
        return _parse_bool(env_value)
    return bool(glob.get('testnet', c.DEFAULT_TESTNET))


def _validate_exchange(exchange: str) -> None:
    if exchange not in c.SUPPORTED_EXCHANGES:
        supported = ', '.join(c.SUPPORTED_EXCHANGES)
        raise ConfigError(f'Unsupported exchange {exchange!r}; choose one of: {supported}')


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

[defaults]                  # applied when `pair add` omits a field
target_volatile_pct = 80.0
target_stable_pct   = 20.0
band_pct            = 5.0
min_notional        = 10.0
max_trade_notional  = 0.0   # 0 = no cap
'''

ENV_TEMPLATE = '''# Secrets for ccbalancer. Never commit this file.
CCB_API_KEY=
CCB_API_SECRET=
# Optional non-secret overrides:
# CCB_EXCHANGE=bybit
# CCB_TESTNET=true
'''
