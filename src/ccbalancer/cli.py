'''Command-line entry point for ccbalancer.

Wires argparse, dispatches to command handlers, and maps domain errors to process
exit codes. User-facing results go to stdout (text or compact JSON); operational
diagnostics go to stderr via logging.
'''

from __future__ import annotations

import argparse
import json
import logging
import sys

from ccbalancer import __version__
from ccbalancer import config as config_mod
from ccbalancer.config import Defaults
from ccbalancer.constants import (
    HISTORY_FILENAME,
    OHLCV_DIRNAME,
    PORTFOLIO_FILENAME,
    STATE_FILENAME,
    ExitCode,
)
from ccbalancer.exceptions import (
    AppError,
    ConfigError,
    ExchangeError,
    OrderRejectedError,
    PortfolioError,
    StateError,
)
from ccbalancer.managers.indicators_manager import IndicatorsManager
from ccbalancer.managers.portfolio_manager import PortfolioManager
from ccbalancer.managers.rebalance_manager import RebalanceManager
from ccbalancer.models import PairConfig
from ccbalancer.stores.exchange import ExchangeStore
from ccbalancer.stores.market_cache import MarketCache
from ccbalancer.stores.portfolio_store import PortfolioStore, pair_to_dict
from ccbalancer.stores.state_store import StateStore
from ccbalancer.utils import indicator_registry as registry
from ccbalancer.utils import render
from ccbalancer.utils.logging import configure_logging
from ccbalancer.utils.timeutil import now_iso

__all__ = ['build_parser', 'main']

_logger = logging.getLogger(__name__)

_EXIT_BY_ERROR: dict[type[AppError], ExitCode] = {
    ConfigError: ExitCode.CONFIG_ERROR,
    PortfolioError: ExitCode.CONFIG_ERROR,
    StateError: ExitCode.CONFIG_ERROR,
    ExchangeError: ExitCode.EXCHANGE_ERROR,
    OrderRejectedError: ExitCode.ORDER_REJECTED,
}


def build_parser() -> argparse.ArgumentParser:
    '''Build the top-level argument parser with all commands.'''
    common = _common_flags()
    parser = argparse.ArgumentParser(
        prog='ccbalancer', description='Agent-driven crypto portfolio rebalancer.'
    )
    subparsers = parser.add_subparsers(dest='command', metavar='<command>')
    subparsers.add_parser('version', parents=[common], help='Print the ccbalancer version.')
    subparsers.add_parser('status', parents=[common], help='Show current vs target allocation per pair.')
    subparsers.add_parser('plan', parents=[common], help='Show rebalance decisions without executing.')
    _add_analyze_command(subparsers, common)
    _add_indicator_command(subparsers, common)
    _add_config_command(subparsers, common)
    _add_pair_command(subparsers, common)
    return parser


def main(argv: list[str] | None = None) -> int:
    '''CLI entry point. Returns a process exit code.'''
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return int(ExitCode.OK)
    try:
        return int(_dispatch(args))
    except AppError as exc:
        _logger.error('%s', exc)
        return int(_exit_code_for(exc))


def _common_flags() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--json', action='store_true', help='Emit compact JSON to stdout.')
    common.add_argument('--config', metavar='PATH', help='Path to a config TOML file.')
    common.add_argument('--exchange', help='Override the configured exchange (bybit|binance).')
    common.add_argument(
        '--testnet', action=argparse.BooleanOptionalAction, default=None,
        help='Use (or disable) the exchange sandbox.',
    )
    common.add_argument(
        '--pair', action='append', metavar='SYMBOL', help='Restrict to a pair (repeatable).'
    )
    return common


def _add_analyze_command(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    analyze = subparsers.add_parser(
        'analyze', parents=[common], help='Show market indicators for a pair across timeframes.'
    )
    analyze.add_argument('symbol', help='Pair as BASE/QUOTE (e.g. BTC/USDT).')
    analyze.add_argument(
        '--timeframe', action='append', metavar='TF',
        help='Timeframe to analyze, repeatable (default: configured timeframes).',
    )
    analyze.add_argument(
        '--require-fresh', action='store_true', dest='require_fresh',
        help='Fail a timeframe rather than fall back to a stale cache.',
    )


def _add_indicator_command(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser('indicator', help='List or set indicator parameters.')
    sub = parser.add_subparsers(dest='indicator_command', metavar='<action>')
    sub.add_parser('list', parents=[common], help='List indicators, parameters, defaults, and current values.')
    set_node = sub.add_parser('set', parents=[common], help='Set indicator parameters in indicators.toml.')
    set_node.add_argument('name', help='Indicator name (see `indicator list`).')
    set_node.add_argument(
        'assignments', nargs='+', metavar='KEY=VALUE',
        help='Parameter assignments, e.g. overbought=63.5 period=14 (lists: periods=12,26,200).',
    )


def _add_config_command(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    config_parser = subparsers.add_parser('config', help='Show or initialize configuration.')
    config_sub = config_parser.add_subparsers(dest='config_command', metavar='<action>')
    config_sub.add_parser('show', parents=[common], help='Show resolved settings (secrets masked).')
    config_sub.add_parser('init', parents=[common], help='Scaffold ~/.ccbalancer with templates.')


def _add_pair_command(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    pair_parser = subparsers.add_parser('pair', help='Manage portfolio pairs and targets.')
    pair_sub = pair_parser.add_subparsers(dest='pair_command', metavar='<action>')
    pair_sub.add_parser('list', parents=[common], help='List configured pairs.')
    for action in ('add', 'set'):
        node = pair_sub.add_parser(action, parents=[common], help=f'{action.capitalize()} a pair.')
        node.add_argument('symbol', help='Pair as BASE/QUOTE (e.g. BTC/USDT).')
        node.add_argument('--target', help='Target ratio volatile/stable, e.g. 80/20.')
        node.add_argument('--band', type=float, help='No-trade band percent.')
        node.add_argument('--min-notional', type=float, dest='min_notional', help='Min order notional.')
        node.add_argument('--max-trade', type=float, dest='max_trade', help='Max trade notional (0 = none).')
        node.add_argument('--entry-price', type=float, dest='entry_price', help='Entry price (stamps entry time).')
        node.add_argument('--invested', type=float, dest='invested', help='Invested capital (quote terms).')
        node.add_argument(
            '--target-set-price', type=float, dest='target_set_price',
            help='Price when the target ratio was set (stamps target-set time).',
        )
    remove = pair_sub.add_parser('remove', parents=[common], help='Remove a pair.')
    remove.add_argument('symbol', help='Pair as BASE/QUOTE (e.g. BTC/USDT).')


def _dispatch(args: argparse.Namespace) -> ExitCode:
    if args.command == 'version':
        return _cmd_version(args)
    if args.command == 'status':
        return _cmd_status(args)
    if args.command == 'plan':
        return _cmd_plan(args)
    if args.command == 'analyze':
        return _cmd_analyze(args)
    if args.command == 'indicator':
        return _cmd_indicator(args)
    if args.command == 'config':
        return _cmd_config(args)
    if args.command == 'pair':
        return _cmd_pair(args)
    return ExitCode.OK


def _cmd_version(args: argparse.Namespace) -> ExitCode:
    _emit(args, {'version': __version__}, [__version__])
    return ExitCode.OK


def _cmd_status(args: argparse.Namespace) -> ExitCode:
    pairs, portfolio_mgr, rebalance_mgr, meta = _read_context(args)
    snapshots = portfolio_mgr.snapshots(pairs)
    rows = [
        (snapshot, rebalance_mgr.decide(pair, snapshot, now=meta['generated_at']))
        for pair, snapshot in zip(pairs, snapshots)
    ]
    payload = render.status_response(rows, meta)
    _emit(args, payload, render.status_lines(rows) or ['(no pairs configured)'])
    return ExitCode.OK


def _cmd_plan(args: argparse.Namespace) -> ExitCode:
    pairs, portfolio_mgr, rebalance_mgr, meta = _read_context(args)
    snapshots = portfolio_mgr.snapshots(pairs)
    decisions = [
        rebalance_mgr.decide(pair, snapshot, now=meta['generated_at'])
        for pair, snapshot in zip(pairs, snapshots)
    ]
    payload = render.plan_response(decisions, meta)
    _emit(args, payload, render.plan_lines(decisions) or ['(no pairs configured)'])
    return ExitCode.OK


def _cmd_analyze(args: argparse.Namespace) -> ExitCode:
    config = config_mod.load_config(args.config, args.exchange, args.testnet)
    manager = _indicators_manager(config)
    symbol = args.symbol.upper()
    timeframes = args.timeframe or _default_timeframes(config)
    snapshots = manager.snapshots(symbol, timeframes, require_fresh=args.require_fresh)
    meta = {'exchange': config.data_exchange, 'testnet': config.testnet, 'generated_at': now_iso()}
    payload = render.analyze_response(symbol, timeframes, snapshots, meta)
    _emit(args, payload, render.analyze_lines(symbol, timeframes, snapshots))
    if all(snapshot is None for snapshot in snapshots):
        return ExitCode.EXCHANGE_ERROR
    return ExitCode.OK


def _default_timeframes(config: config_mod.AppConfig) -> list[str]:
    '''Decision then analysis timeframes, de-duplicated, order preserved.'''
    ordered = dict.fromkeys((*config.decision_timeframes, *config.analysis_timeframes))
    return list(ordered)


def _indicators_manager(config: config_mod.AppConfig) -> IndicatorsManager:
    '''Build the indicators manager (seam for tests to inject a fake).'''
    data_store = ExchangeStore(
        exchange_id=config.data_exchange,
        testnet=config.testnet,
        timeout_ms=config.http_timeout_ms,
    )
    cache = MarketCache(config.app_dir / OHLCV_DIRNAME)
    return IndicatorsManager(
        data_store, cache, ohlcv_limit=config.ohlcv_limit, settings=config.indicators
    )


def _cmd_indicator(args: argparse.Namespace) -> ExitCode:
    if args.indicator_command == 'list':
        return _cmd_indicator_list(args)
    if args.indicator_command == 'set':
        return _cmd_indicator_set(args)
    _emit(args, {'error': 'specify: indicator list | indicator set'}, ['Usage: indicator list | indicator set <name> KEY=VALUE ...'])
    return ExitCode.CONFIG_ERROR


def _cmd_indicator_list(args: argparse.Namespace) -> ExitCode:
    config = config_mod.load_config(args.config, args.exchange, args.testnet)
    catalog = registry.describe(config.indicators.values)
    payload = render.indicator_catalog_response(catalog, now_iso())
    _emit(args, payload, render.indicator_catalog_lines(catalog))
    return ExitCode.OK


def _cmd_indicator_set(args: argparse.Namespace) -> ExitCode:
    config = config_mod.load_config(args.config, args.exchange, args.testnet)
    if config.indicators_path is None:
        raise ConfigError('No indicators.toml location resolved')
    overrides = config_mod.read_indicator_overrides(config.indicators_path)
    section = dict(overrides.get(args.name, {}))
    section.update(_parse_assignments(args.name, args.assignments))
    overrides[args.name] = section
    resolved = registry.resolve(overrides)  # validates the merged result
    config_mod.write_indicator_overrides(config.indicators_path, overrides)
    params = resolved[args.name]
    text = f'Updated {args.name}: ' + ', '.join(f'{key}={value}' for key, value in params.items())
    _emit(args, {'command': 'indicator set', 'indicator': args.name, 'params': params}, [text])
    return ExitCode.OK


def _parse_assignments(name: str, assignments: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in assignments:
        if '=' not in item:
            raise ConfigError(f'Invalid assignment {item!r}; expected KEY=VALUE')
        key, raw = item.split('=', 1)
        result[key] = registry.coerce_scalar(name, key, raw)
    return result


def _read_context(
    args: argparse.Namespace,
) -> tuple[list[PairConfig], PortfolioManager, RebalanceManager, dict[str, object]]:
    '''Resolve config and stores into the managers a read command needs.'''
    config = config_mod.load_config(args.config, args.exchange, args.testnet)
    portfolio = PortfolioStore(config.app_dir / PORTFOLIO_FILENAME)
    pairs = _selected_pairs(portfolio, args.pair)
    state = StateStore(config.app_dir / STATE_FILENAME, config.app_dir / HISTORY_FILENAME)
    portfolio_mgr = PortfolioManager(_exchange_store(config), state)
    rebalance_mgr = RebalanceManager.from_config(config)
    meta = {'exchange': config.exchange, 'testnet': config.testnet, 'generated_at': now_iso()}
    return pairs, portfolio_mgr, rebalance_mgr, meta


def _exchange_store(config: config_mod.AppConfig) -> ExchangeStore:
    '''Build the exchange store (seam for tests to inject a fake).'''
    return ExchangeStore.from_config(config)


def _selected_pairs(store: PortfolioStore, requested: list[str] | None) -> list[PairConfig]:
    pairs = store.load()
    if not requested:
        return pairs
    wanted = {symbol.upper() for symbol in requested}
    known = {pair.symbol for pair in pairs}
    missing = sorted(wanted - known)
    if missing:
        raise PortfolioError(f'Pair(s) not configured: {", ".join(missing)}')
    return [pair for pair in pairs if pair.symbol in wanted]


def _cmd_config(args: argparse.Namespace) -> ExitCode:
    if args.config_command == 'init':
        return _cmd_config_init(args)
    if args.config_command == 'show':
        return _cmd_config_show(args)
    _emit(args, {'error': 'specify: config show | config init'}, ['Usage: config show | config init'])
    return ExitCode.CONFIG_ERROR


def _cmd_config_show(args: argparse.Namespace) -> ExitCode:
    config = config_mod.load_config(args.config, args.exchange, args.testnet)
    summary = config_mod.masked_summary(config)
    _emit(args, {'command': 'config show', 'config': summary}, _format_summary(summary))
    return ExitCode.OK


def _cmd_config_init(args: argparse.Namespace) -> ExitCode:
    app_dir = config_mod.resolve_app_dir()
    created = config_mod.init_app_dir(app_dir)
    created_str = [str(path) for path in created]
    text = [f'Initialized {app_dir}'] + [f'  created {path}' for path in created_str]
    if not created_str:
        text.append('  (all files already present)')
    _emit(args, {'command': 'config init', 'app_dir': str(app_dir), 'created': created_str}, text)
    return ExitCode.OK


def _cmd_pair(args: argparse.Namespace) -> ExitCode:
    handlers = {
        'list': _cmd_pair_list,
        'add': _cmd_pair_add,
        'set': _cmd_pair_set,
        'remove': _cmd_pair_remove,
    }
    handler = handlers.get(args.pair_command)
    if handler is None:
        _emit(args, {'error': 'specify: pair list|add|set|remove'}, ['Usage: pair list|add|set|remove'])
        return ExitCode.CONFIG_ERROR
    return handler(args)


def _cmd_pair_list(args: argparse.Namespace) -> ExitCode:
    store, _ = _portfolio_store(args)
    pairs = store.load()
    payload = {'command': 'pair list', 'pairs': [pair_to_dict(pair) for pair in pairs]}
    _emit(args, payload, [_format_pair(pair) for pair in pairs] or ['(no pairs configured)'])
    return ExitCode.OK


def _cmd_pair_add(args: argparse.Namespace) -> ExitCode:
    store, config = _portfolio_store(args)
    pair = _build_pair(args, config.defaults)
    store.add(pair)
    _emit(args, {'command': 'pair add', 'pair': pair_to_dict(pair)}, [f'Added {_format_pair(pair)}'])
    return ExitCode.OK


def _cmd_pair_set(args: argparse.Namespace) -> ExitCode:
    store, _ = _portfolio_store(args)
    existing = store.get(args.symbol)
    if existing is None:
        raise PortfolioError(f'Pair {args.symbol.upper()} not found; use `pair add`')
    pair = _merge_pair(existing, args)
    store.replace(pair)
    _emit(args, {'command': 'pair set', 'pair': pair_to_dict(pair)}, [f'Updated {_format_pair(pair)}'])
    return ExitCode.OK


def _cmd_pair_remove(args: argparse.Namespace) -> ExitCode:
    store, _ = _portfolio_store(args)
    store.remove(args.symbol)
    symbol = args.symbol.upper()
    _emit(args, {'command': 'pair remove', 'symbol': symbol}, [f'Removed {symbol}'])
    return ExitCode.OK


def _portfolio_store(args: argparse.Namespace) -> tuple[PortfolioStore, config_mod.AppConfig]:
    config = config_mod.load_config(args.config, args.exchange, args.testnet)
    return PortfolioStore(config.app_dir / PORTFOLIO_FILENAME), config


def _build_pair(args: argparse.Namespace, defaults: Defaults) -> PairConfig:
    volatile, stable = _resolve_target(args.target, defaults)
    return PairConfig(
        symbol=args.symbol.upper(),
        target_volatile_pct=volatile,
        target_stable_pct=stable,
        band_pct=args.band if args.band is not None else defaults.band_pct,
        min_notional=args.min_notional if args.min_notional is not None else defaults.min_notional,
        max_trade_notional=args.max_trade if args.max_trade is not None else defaults.max_trade_notional,
        entry_price=args.entry_price,
        entry_ts=now_iso() if args.entry_price is not None else None,
        invested_capital=args.invested,
        target_set_price=args.target_set_price,
        target_set_ts=now_iso() if args.target_set_price is not None else None,
    )


def _merge_pair(existing: PairConfig, args: argparse.Namespace) -> PairConfig:
    volatile, stable = existing.target_volatile_pct, existing.target_stable_pct
    if args.target is not None:
        volatile, stable = _parse_target(args.target)
    return PairConfig(
        symbol=existing.symbol,
        target_volatile_pct=volatile,
        target_stable_pct=stable,
        band_pct=args.band if args.band is not None else existing.band_pct,
        min_notional=args.min_notional if args.min_notional is not None else existing.min_notional,
        max_trade_notional=args.max_trade if args.max_trade is not None else existing.max_trade_notional,
        entry_price=args.entry_price if args.entry_price is not None else existing.entry_price,
        entry_ts=now_iso() if args.entry_price is not None else existing.entry_ts,
        invested_capital=args.invested if args.invested is not None else existing.invested_capital,
        target_set_price=args.target_set_price if args.target_set_price is not None else existing.target_set_price,
        target_set_ts=now_iso() if args.target_set_price is not None else existing.target_set_ts,
    )


def _resolve_target(target: str | None, defaults: Defaults) -> tuple[float, float]:
    if target is None:
        return defaults.target_volatile_pct, defaults.target_stable_pct
    return _parse_target(target)


def _parse_target(target: str) -> tuple[float, float]:
    parts = target.split('/')
    if len(parts) != 2:
        raise PortfolioError(f'Invalid --target {target!r}; expected VOLATILE/STABLE, e.g. 80/20')
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise PortfolioError(f'Invalid --target {target!r}: {exc}') from exc


def _format_pair(pair: PairConfig) -> str:
    return (
        f'{pair.symbol} target={pair.target_volatile_pct:g}/{pair.target_stable_pct:g} '
        f'band={pair.band_pct:g} min={pair.min_notional:g} max={pair.max_trade_notional:g}'
    )


def _emit(args: argparse.Namespace, payload: dict[str, object], text_lines: list[str]) -> None:
    if getattr(args, 'json', False):
        print(json.dumps(payload, separators=(',', ':'), default=str))
    else:
        for line in text_lines:
            print(line)


def _format_summary(summary: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, dict):
            lines.append(f'{key}:')
            lines.extend(f'  {sub}: {sub_value}' for sub, sub_value in value.items())
        else:
            lines.append(f'{key}: {value}')
    return lines


def _exit_code_for(exc: AppError) -> ExitCode:
    for error_type, code in _EXIT_BY_ERROR.items():
        if isinstance(exc, error_type):
            return code
    return ExitCode.CONFIG_ERROR


if __name__ == '__main__':
    sys.exit(main())
