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
from ccbalancer.constants import PORTFOLIO_FILENAME, ExitCode
from ccbalancer.exceptions import (
    AppError,
    ConfigError,
    ExchangeError,
    OrderRejectedError,
    PortfolioError,
    StateError,
)
from ccbalancer.models import PairConfig
from ccbalancer.stores.portfolio_store import PortfolioStore, pair_to_dict
from ccbalancer.utils.logging import configure_logging

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
    remove = pair_sub.add_parser('remove', parents=[common], help='Remove a pair.')
    remove.add_argument('symbol', help='Pair as BASE/QUOTE (e.g. BTC/USDT).')


def _dispatch(args: argparse.Namespace) -> ExitCode:
    if args.command == 'version':
        return _cmd_version(args)
    if args.command == 'config':
        return _cmd_config(args)
    if args.command == 'pair':
        return _cmd_pair(args)
    return ExitCode.OK


def _cmd_version(args: argparse.Namespace) -> ExitCode:
    _emit(args, {'version': __version__}, [__version__])
    return ExitCode.OK


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
