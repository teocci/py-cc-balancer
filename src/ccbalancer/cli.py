'''Command-line entry point for ccbalancer.

Wires argparse, dispatches to command handlers, and maps domain errors to process
exit codes. User-facing results go to stdout (text or compact JSON); operational
diagnostics go to stderr via logging.
'''

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import sys

from ccbalancer import __version__
from ccbalancer import config as config_mod
from ccbalancer import constants as c
from ccbalancer.config import Defaults
from ccbalancer.constants import (
    AUTH_FILENAME,
    DECISION_LOG_FILENAME,
    HISTORY_FILENAME,
    LEDGER_FILENAME,
    OHLCV_DIRNAME,
    PORTFOLIO_FILENAME,
    STATE_FILENAME,
    ExitCode,
)
from ccbalancer.exceptions import (
    AppError,
    AuthError,
    ConfigError,
    ExchangeError,
    OrderRejectedError,
    PortfolioError,
    SafetyError,
    StateError,
)
from ccbalancer.managers.execution_manager import (
    ExecutionManager,
    confirm_token,
    kill_switch_active,
    session_notional,
)
from ccbalancer.managers.indicators_manager import IndicatorsManager
from ccbalancer.managers.performance_manager import PerformanceManager, portfolio_totals
from ccbalancer.managers.portfolio_manager import PortfolioManager
from ccbalancer.managers.rebalance_manager import RebalanceManager
from ccbalancer.models import AuthProfile, ExecutionResult, PairConfig
from ccbalancer.stores.auth_store import AuthStore, backend_for, normalize_profile_name
from ccbalancer.stores.decision_store import DecisionStore
from ccbalancer.stores.exchange import ExchangeStore, requires_passphrase
from ccbalancer.stores.ledger_store import LedgerStore
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
    AuthError: ExitCode.CONFIG_ERROR,
    PortfolioError: ExitCode.CONFIG_ERROR,
    StateError: ExitCode.CONFIG_ERROR,
    ExchangeError: ExitCode.EXCHANGE_ERROR,
    OrderRejectedError: ExitCode.ORDER_REJECTED,
    SafetyError: ExitCode.SAFETY_BLOCKED,
}


# Commands grouped by side effect, shown in `--help` so an agent can tell read
# (live data, no writes) from write (mutates/places orders) from audit (local
# logs only, no network).
_COMMAND_TAXONOMY = '''command categories:
  read   (live data, no side effects):  status, plan, analyze, indicator list, performance, orders, version
  write  (mutate state / place orders):  rebalance, cancel, pair, indicator set, config
  audit  (local logs only, no network):  decisions, history, performance --history, export

rebalance is dry-run by default; pass --execute --confirm <token> (from plan) to place orders.'''


def build_parser() -> argparse.ArgumentParser:
    '''Build the top-level argument parser with all commands.'''
    common = _common_flags()
    parser = argparse.ArgumentParser(
        prog='ccbalancer',
        description='Agent-driven crypto portfolio rebalancer.',
        epilog=_COMMAND_TAXONOMY,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', metavar='<command>')
    subparsers.add_parser('version', parents=[common], help='Print the ccbalancer version.')
    subparsers.add_parser('status', parents=[common], help='Show current vs target allocation per pair.')
    subparsers.add_parser('plan', parents=[common], help='Show rebalance decisions without executing.')
    _add_execution_commands(subparsers, common)
    _add_performance_command(subparsers, common)
    _add_analyze_command(subparsers, common)
    _add_indicator_command(subparsers, common)
    _add_config_command(subparsers, common)
    _add_auth_command(subparsers, common)
    _add_pair_command(subparsers, common)
    _add_audit_commands(subparsers, common)
    return parser


def _add_execution_commands(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    rebalance = subparsers.add_parser(
        'rebalance', parents=[common],
        help='Place rebalance orders (dry-run by default; needs --execute --confirm).',
    )
    rebalance.add_argument(
        '--execute', action='store_true', help='Place orders (default: dry-run, writes nothing).'
    )
    rebalance.add_argument(
        '--confirm', metavar='TOKEN', help='Confirm-token from a prior plan/dry-run (required with --execute).'
    )
    subparsers.add_parser('orders', parents=[common], help='List open orders (this tool\'s are flagged).')
    cancel = subparsers.add_parser(
        'cancel', parents=[common], help='Cancel this tool\'s open orders (dry-run by default).'
    )
    cancel.add_argument('--execute', action='store_true', help='Actually cancel (default: dry-run).')


def _add_performance_command(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    performance = subparsers.add_parser(
        'performance', parents=[common],
        help='Show cost-basis P&L and ROI per pair (--history for the ledger replay).',
    )
    performance.add_argument(
        '--history', action='store_true',
        help='Replay realized P&L from the local ledger only (no network).',
    )


def _add_audit_commands(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    subparsers.add_parser(
        'decisions', parents=[common], help='Replay the local decision log (no network).'
    )
    subparsers.add_parser(
        'history', parents=[common], help='Replay the local rebalance history (no network).'
    )
    subparsers.add_parser(
        'export', parents=[common], help='Export local decision and history logs as JSON.'
    )


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
    common.add_argument('--profile', metavar='NAME', help='Use a named auth profile (overrides the active one).')
    common.add_argument('--exchange', help='Override the configured/profile exchange (bybit|binance|okx).')
    common.add_argument(
        '--testnet', action=argparse.BooleanOptionalAction, default=None,
        help='Use (or disable) the exchange sandbox.',
    )
    common.add_argument(
        '--pair', action='append', metavar='SYMBOL', help='Restrict to a pair (repeatable).'
    )
    return common


def _load_config(args: argparse.Namespace) -> config_mod.AppConfig:
    '''Resolve config, threading the global flags (incl. ``--profile``).'''
    return config_mod.load_config(args.config, args.exchange, args.testnet, args.profile)


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


def _add_auth_command(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    auth = subparsers.add_parser('auth', help='Manage exchange credential profiles (gh-style).')
    sub = auth.add_subparsers(dest='auth_command', metavar='<action>')
    _add_auth_login(sub, common)
    logout = sub.add_parser('logout', parents=[common], help='Remove a profile (default: the active one).')
    logout.add_argument('name', nargs='?', help='Profile to remove.')
    sub.add_parser('list', parents=[common], help='List profiles (active marked, secrets masked).')
    use = sub.add_parser('use', parents=[common], help='Switch the active profile.')
    use.add_argument('name', help='Profile to make active.')
    sub.add_parser('status', parents=[common], help='Show the active profile and a live credential check.')
    sub.add_parser('whoami', parents=[common], help='Print the active profile name and exchange (local).')


def _add_auth_login(sub: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    login = sub.add_parser('login', parents=[common], help='Add or update a credential profile.')
    # The exchange/sandbox for the new profile reuse the inherited --exchange and
    # --testnet flags; --testnet defaults to None (BooleanOptionalAction) → testnet.
    login.add_argument('--name', help='Profile name slug (default: the exchange id).')
    login.add_argument('--key', help='API key (omit to be prompted when interactive).')
    login.add_argument('--secret', help='API secret (omit to be prompted when interactive).')
    login.add_argument('--passphrase', help='Passphrase for venues that require one (e.g. OKX).')
    login.add_argument(
        '--keyring', action=argparse.BooleanOptionalAction, default=None,
        help='Store secrets in the OS keyring (default) or, with --no-keyring, inline in auth.json.',
    )
    login.add_argument(
        '--from-env', action='store_true', dest='from_env',
        help=f'Import {c.ENV_API_KEY}/{c.ENV_API_SECRET} from the environment.',
    )
    login.add_argument(
        '--no-verify', action='store_true', dest='no_verify',
        help='Skip the live fetch_balance credential check.',
    )


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
    if args.command == 'rebalance':
        return _cmd_rebalance(args)
    if args.command == 'orders':
        return _cmd_orders(args)
    if args.command == 'cancel':
        return _cmd_cancel(args)
    if args.command == 'performance':
        return _cmd_performance(args)
    if args.command == 'analyze':
        return _cmd_analyze(args)
    if args.command == 'indicator':
        return _cmd_indicator(args)
    if args.command == 'config':
        return _cmd_config(args)
    if args.command == 'auth':
        return _cmd_auth(args)
    if args.command == 'pair':
        return _cmd_pair(args)
    if args.command == 'decisions':
        return _cmd_decisions(args)
    if args.command == 'history':
        return _cmd_history(args)
    if args.command == 'export':
        return _cmd_export(args)
    return ExitCode.OK


def _cmd_version(args: argparse.Namespace) -> ExitCode:
    _emit(args, {'version': __version__}, [__version__])
    return ExitCode.OK


def _cmd_status(args: argparse.Namespace) -> ExitCode:
    pairs, portfolio_mgr, rebalance_mgr, _decisions, meta = _read_context(args)
    snapshots = portfolio_mgr.snapshots(pairs)
    rows = [
        (snapshot, rebalance_mgr.decide(pair, snapshot, now=meta['generated_at']))
        for pair, snapshot in zip(pairs, snapshots)
    ]
    payload = render.status_response(rows, meta)
    _emit(args, payload, render.status_lines(rows) or ['(no pairs configured)'])
    return ExitCode.OK


def _cmd_plan(args: argparse.Namespace) -> ExitCode:
    pairs, portfolio_mgr, rebalance_mgr, decision_store, meta = _read_context(args)
    snapshots = portfolio_mgr.snapshots(pairs)
    decisions = [
        rebalance_mgr.decide(pair, snapshot, now=meta['generated_at'])
        for pair, snapshot in zip(pairs, snapshots)
    ]
    _record_decisions(decision_store, decisions, meta)
    token = confirm_token(decisions, exchange=str(meta['exchange']), testnet=bool(meta['testnet']))
    payload = render.plan_response(decisions, meta, token)
    _emit(args, payload, render.plan_lines(decisions) or ['(no pairs configured)'])
    return ExitCode.OK


def _record_decisions(store: DecisionStore, decisions: list, meta: dict[str, object]) -> None:
    '''Append one decision-memory record per pair (the `plan` audit trail).'''
    for decision in decisions:
        store.append_decision(
            decision,
            ts=str(meta['generated_at']),
            exchange=str(meta['exchange']),
            testnet=bool(meta['testnet']),
            command='plan',
        )


def _cmd_rebalance(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    pairs, portfolio_mgr, rebalance_mgr, exchange, state = _execution_context(config, args.pair)
    meta = _live_meta(config)
    snapshots = portfolio_mgr.snapshots(pairs)
    decisions = [
        rebalance_mgr.decide(pair, snapshot, now=str(meta['generated_at']))
        for pair, snapshot in zip(pairs, snapshots)
    ]
    token = confirm_token(decisions, exchange=config.exchange, testnet=config.testnet)
    if not args.execute:
        payload = render.rebalance_dry_response(decisions, meta, token)
        _emit(args, payload, render.rebalance_dry_lines(decisions, token))
        return ExitCode.OK
    _enforce_safety(config, args, decisions, token)
    manager = _build_execution_manager(config, exchange, state)
    results = manager.execute(decisions, now=str(meta['generated_at']))
    _emit(args, render.rebalance_exec_response(results, meta, token), render.rebalance_exec_lines(results))
    return _exit_for_results(results)


def _enforce_safety(
    config: config_mod.AppConfig,
    args: argparse.Namespace,
    decisions: list,
    token: str | None,
) -> None:
    '''Enforce the execution guardrails; raise :class:`SafetyError` to block.'''
    if token is None:
        return  # nothing actionable: --execute is a harmless no-op
    if kill_switch_active(config.safety.kill_switch_path):
        raise SafetyError(
            f'Kill-switch present at {config.safety.kill_switch_path}; remove it to execute'
        )
    if args.confirm != token:
        raise SafetyError(
            'Confirm-token missing or stale; re-run plan/dry-run and pass --confirm <token>'
        )
    cap = config.safety.max_session_notional_usd
    total = session_notional(decisions)
    if cap > 0 and total > cap:
        raise SafetyError(
            f'Session notional {total:.2f} exceeds cap {cap:.2f}; '
            f'raise [safety].max_session_notional_usd to proceed'
        )
    config_mod.require_credentials(config)


def _exit_for_results(results: list[ExecutionResult]) -> ExitCode:
    '''Map execution results to an exit code (partial vs total failure).'''
    failed = [r for r in results if r.status == 'failed']
    if not failed:
        return ExitCode.OK
    if any(r.placed for r in results):
        return ExitCode.PARTIAL_FAILURE
    return ExitCode.ORDER_REJECTED


def _cmd_orders(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    config_mod.require_credentials(config)
    exchange = _exchange_store(config)
    orders = _open_orders(exchange, args.pair)
    _emit(args, render.orders_response(orders, _live_meta(config)),
          render.orders_lines(orders) or ['(no open orders)'])
    return ExitCode.OK


def _cmd_cancel(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    config_mod.require_credentials(config)
    exchange = _exchange_store(config)
    state = StateStore(config.app_dir / STATE_FILENAME, config.app_dir / HISTORY_FILENAME)
    manager = _build_execution_manager(config, exchange, state)
    symbols = [s.upper() for s in args.pair] if args.pair else None
    orders = manager.owned_open_orders(symbols)
    if args.execute:
        orders = manager.cancel_orders(orders)
    meta = _live_meta(config)
    empty = ['(dry-run) no orders to cancel' if not args.execute else '(no orders to cancel)']
    _emit(args, render.cancel_response(orders, meta, dry_run=not args.execute),
          render.cancel_lines(orders, dry_run=not args.execute) or empty)
    return ExitCode.OK


def _execution_context(
    config: config_mod.AppConfig, requested: list[str] | None
) -> tuple[list[PairConfig], PortfolioManager, RebalanceManager, ExchangeStore, StateStore]:
    '''Resolve the pairs, managers, and stores the execution path needs.'''
    portfolio = PortfolioStore(config.app_dir / PORTFOLIO_FILENAME)
    pairs = _selected_pairs(portfolio, requested)
    state = StateStore(config.app_dir / STATE_FILENAME, config.app_dir / HISTORY_FILENAME)
    exchange = _exchange_store(config)
    return pairs, PortfolioManager(exchange, state), RebalanceManager.from_config(config), exchange, state


def _build_execution_manager(
    config: config_mod.AppConfig, exchange: ExchangeStore, state: StateStore
) -> ExecutionManager:
    return ExecutionManager(
        exchange=exchange,
        state_store=state,
        ledger_store=LedgerStore(config.app_dir / LEDGER_FILENAME),
        decision_store=DecisionStore(config.app_dir / DECISION_LOG_FILENAME),
        exchange_id=config.exchange,
        testnet=config.testnet,
    )


def _open_orders(exchange: ExchangeStore, requested: list[str] | None) -> list[dict[str, object]]:
    if not requested:
        return exchange.fetch_open_orders(None)
    symbols = dict.fromkeys(symbol.upper() for symbol in requested)
    return [order for symbol in symbols for order in exchange.fetch_open_orders(symbol)]


def _live_meta(config: config_mod.AppConfig) -> dict[str, object]:
    return {'exchange': config.exchange, 'testnet': config.testnet, 'generated_at': now_iso()}


def _cmd_performance(args: argparse.Namespace) -> ExitCode:
    if args.history:
        return _cmd_performance_history(args)
    return _cmd_performance_live(args)


def _cmd_performance_live(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    portfolio = PortfolioStore(config.app_dir / PORTFOLIO_FILENAME)
    pairs = _selected_pairs(portfolio, args.pair)
    ledger = LedgerStore(config.app_dir / LEDGER_FILENAME)
    manager = PerformanceManager(ledger, _exchange_store(config))
    snapshots = manager.snapshots(pairs)
    totals = portfolio_totals(snapshots)
    payload = render.performance_response(snapshots, totals, _live_meta(config))
    _emit(args, payload, render.performance_lines(snapshots, totals) or ['(no pairs configured)'])
    return ExitCode.OK


def _cmd_performance_history(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    ledger = LedgerStore(config.app_dir / LEDGER_FILENAME)
    manager = PerformanceManager(ledger)  # audit: no exchange access
    symbols = {symbol.upper() for symbol in args.pair} if args.pair else None
    records = manager.realized_history(symbols)
    payload = render.performance_history_response(records, now_iso())
    _emit(args, payload, render.performance_history_lines(records) or ['(no fills logged)'])
    return ExitCode.OK


def _cmd_analyze(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
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
    config = _load_config(args)
    catalog = registry.describe(config.indicators.values)
    payload = render.indicator_catalog_response(catalog, now_iso())
    _emit(args, payload, render.indicator_catalog_lines(catalog))
    return ExitCode.OK


def _cmd_indicator_set(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
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
) -> tuple[list[PairConfig], PortfolioManager, RebalanceManager, DecisionStore, dict[str, object]]:
    '''Resolve config and stores into the managers a read command needs.'''
    config = _load_config(args)
    portfolio = PortfolioStore(config.app_dir / PORTFOLIO_FILENAME)
    pairs = _selected_pairs(portfolio, args.pair)
    state = StateStore(config.app_dir / STATE_FILENAME, config.app_dir / HISTORY_FILENAME)
    portfolio_mgr = PortfolioManager(_exchange_store(config), state)
    rebalance_mgr = RebalanceManager.from_config(config)
    decision_store = DecisionStore(config.app_dir / DECISION_LOG_FILENAME)
    meta = {'exchange': config.exchange, 'testnet': config.testnet, 'generated_at': now_iso()}
    return pairs, portfolio_mgr, rebalance_mgr, decision_store, meta


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
    config = _load_config(args)
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


def _cmd_auth(args: argparse.Namespace) -> ExitCode:
    handlers = {
        'login': _cmd_auth_login,
        'logout': _cmd_auth_logout,
        'list': _cmd_auth_list,
        'use': _cmd_auth_use,
        'status': _cmd_auth_status,
        'whoami': _cmd_auth_whoami,
    }
    handler = handlers.get(args.auth_command)
    if handler is None:
        usage = 'Usage: auth login|logout|list|use|status|whoami'
        _emit(args, {'error': 'specify: auth login|logout|list|use|status|whoami'}, [usage])
        return ExitCode.CONFIG_ERROR
    return handler(args)


def _cmd_auth_login(args: argparse.Namespace) -> ExitCode:
    exchange = _login_exchange(args)
    name = normalize_profile_name(args.name or exchange)
    testnet = c.DEFAULT_TESTNET if args.testnet is None else args.testnet
    key, secret, password = _collect_credentials(args, exchange)
    profile = AuthProfile(name, exchange, testnet, key, secret, password)
    store = _auth_store(args)
    store.add_or_update(profile)
    return _verify_and_emit_login(args, store, profile)


def _verify_and_emit_login(args: argparse.Namespace, store: AuthStore, profile: AuthProfile) -> ExitCode:
    active = store.active_name()
    if args.no_verify:
        _emit_login(args, profile, active, None)
        return ExitCode.OK
    try:
        _verify_profile(profile)
    except ExchangeError as exc:
        _logger.warning('credential check failed: %s', exc)
        _emit_login(args, profile, active, False)
        return ExitCode.EXCHANGE_ERROR
    _emit_login(args, profile, active, True)
    return ExitCode.OK


def _emit_login(
    args: argparse.Namespace, profile: AuthProfile, active: str | None, verified: bool | None
) -> None:
    payload = {
        'command': 'auth login',
        'profile': render.masked_profile(profile),
        'active': active,
        'verified': verified,
    }
    status = {True: 'verified', False: 'saved (credential check failed)', None: 'saved (unverified)'}
    _emit(args, payload, [f'Logged in {profile.name} ({profile.exchange}): {status[verified]}'])


def _cmd_auth_logout(args: argparse.Namespace) -> ExitCode:
    store = _auth_store(args)
    name = args.name or store.active_name()
    if name is None:
        _emit(args, {'error': 'no profile to remove'}, ['No active profile to remove.'])
        return ExitCode.CONFIG_ERROR
    store.remove(name)
    active = store.active_name()
    removed = normalize_profile_name(name)
    _emit(args, {'command': 'auth logout', 'removed': removed, 'active': active},
          [f'Removed {removed}', f'Active profile: {active or "(none)"}'])
    return ExitCode.OK


def _cmd_auth_list(args: argparse.Namespace) -> ExitCode:
    store = _auth_store(args)
    profiles = store.load()
    active = store.active_name()
    payload = render.auth_list_response(profiles, active, now_iso())
    empty = ['(no profiles; run `ccbalancer auth login`)']
    _emit(args, payload, render.auth_list_lines(profiles, active) or empty)
    return ExitCode.OK


def _cmd_auth_use(args: argparse.Namespace) -> ExitCode:
    store = _auth_store(args)
    store.set_active(args.name)
    active = normalize_profile_name(args.name)
    _emit(args, {'command': 'auth use', 'active': active}, [f'Active profile: {active}'])
    return ExitCode.OK


def _cmd_auth_status(args: argparse.Namespace) -> ExitCode:
    store = _auth_store(args)
    profile = _selected_profile(store, args.profile)
    if profile is None:
        _emit(args, {'command': 'auth status', 'active': None},
              ['No active profile; run `ccbalancer auth login`.'])
        return ExitCode.OK
    valid = _probe_profile(profile)
    active = store.active_name()
    payload = render.auth_status_response(profile, active, valid, now_iso())
    _emit(args, payload, render.auth_status_lines(profile, active, valid))
    return ExitCode.OK


def _cmd_auth_whoami(args: argparse.Namespace) -> ExitCode:
    store = _auth_store(args)
    profile = _selected_profile(store, args.profile)
    if profile is None:
        _emit(args, {'command': 'auth whoami', 'profile': None}, ['No active profile.'])
        return ExitCode.OK
    _emit(args, render.auth_whoami_response(profile, now_iso()), render.auth_whoami_lines(profile))
    return ExitCode.OK


def _auth_store(args: argparse.Namespace) -> AuthStore:
    '''Build the auth store (seam for tests to inject a fake).'''
    path = config_mod.resolve_app_dir() / AUTH_FILENAME
    return AuthStore(path, backend_for(path, _backend_pref(args)))


def _backend_pref(args: argparse.Namespace) -> str | None:
    keyring = getattr(args, 'keyring', None)
    if keyring is None:
        return None
    return 'keyring' if keyring else 'file'


def _selected_profile(store: AuthStore, profile_flag: str | None) -> AuthProfile | None:
    name = profile_flag or os.getenv(c.ENV_PROFILE) or store.active_name()
    if name is None:
        return None
    profile = store.get(name)
    if profile is None:
        raise AuthError(f'Profile {name!r} not found; run `ccbalancer auth list`')
    return profile


def _login_exchange(args: argparse.Namespace) -> str:
    exchange = (args.exchange or c.DEFAULT_EXCHANGE).lower()
    if exchange not in c.SUPPORTED_EXCHANGES:
        supported = ', '.join(c.SUPPORTED_EXCHANGES)
        raise AuthError(f'Unsupported exchange {exchange!r}; choose one of: {supported}')
    return exchange


def _collect_credentials(args: argparse.Namespace, exchange: str) -> tuple[str, str, str | None]:
    '''Resolve (key, secret, passphrase): flags/env, then interactive prompts.'''
    key = args.key or (os.getenv(c.ENV_API_KEY) if args.from_env else None)
    secret = args.secret or (os.getenv(c.ENV_API_SECRET) if args.from_env else None)
    password = args.passphrase
    if key and secret:
        return key, secret, password
    if not sys.stdin.isatty():
        raise AuthError('Provide --key and --secret (or --from-env) for non-interactive login')
    key = key or getpass.getpass('API key: ')
    secret = secret or getpass.getpass('API secret: ')
    if password is None and requires_passphrase(exchange):
        password = getpass.getpass('Passphrase: ') or None
    return key, secret, password


def _verify_profile(profile: AuthProfile) -> None:
    '''Prove the credentials work: local check then a live balance fetch.'''
    store = _profile_exchange_store(profile)
    store.check_credentials()
    store.fetch_balance()


def _probe_profile(profile: AuthProfile) -> bool | None:
    '''Three-state credential probe: True valid, False missing, None unreachable.'''
    store = _profile_exchange_store(profile)
    try:
        store.check_credentials()
    except ExchangeError:
        return False
    try:
        store.fetch_balance()
    except ExchangeError:
        return None
    return True


def _profile_exchange_store(profile: AuthProfile) -> ExchangeStore:
    '''Build an exchange store for a profile (seam for tests to inject a fake).'''
    return ExchangeStore(
        exchange_id=profile.exchange,
        testnet=profile.testnet,
        api_key=profile.api_key,
        api_secret=profile.api_secret,
        password=profile.password,
    )


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


def _cmd_decisions(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    store = DecisionStore(config.app_dir / DECISION_LOG_FILENAME)
    records = _filter_by_pair(store.load(), args.pair)
    payload = render.decisions_response(records, now_iso())
    _emit(args, payload, render.decisions_lines(records) or ['(no decisions logged)'])
    return ExitCode.OK


def _cmd_history(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    state = StateStore(config.app_dir / STATE_FILENAME, config.app_dir / HISTORY_FILENAME)
    events = _filter_by_pair(state.load_history(), args.pair)
    payload = render.history_response(events, now_iso())
    _emit(args, payload, render.history_lines(events) or ['(no history logged)'])
    return ExitCode.OK


def _cmd_export(args: argparse.Namespace) -> ExitCode:
    config = _load_config(args)
    decisions = DecisionStore(config.app_dir / DECISION_LOG_FILENAME).load()
    state = StateStore(config.app_dir / STATE_FILENAME, config.app_dir / HISTORY_FILENAME)
    payload = render.export_response(decisions, state.load_history(), now_iso())
    # Export is a data bundle: always JSON, even without --json.
    print(json.dumps(payload, separators=(',', ':'), default=str))
    return ExitCode.OK


def _filter_by_pair(
    records: list[dict[str, object]], requested: list[str] | None
) -> list[dict[str, object]]:
    '''Keep records whose symbol is in ``requested`` (no portfolio validation).'''
    if not requested:
        return records
    wanted = {symbol.upper() for symbol in requested}
    return [record for record in records if record.get('symbol') in wanted]


def _portfolio_store(args: argparse.Namespace) -> tuple[PortfolioStore, config_mod.AppConfig]:
    config = _load_config(args)
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
