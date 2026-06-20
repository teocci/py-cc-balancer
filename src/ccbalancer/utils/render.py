'''Render read-command results as stable JSON or human-readable text.

The read commands (`status`, `plan`) share one serialization path so their JSON
contract stays stable for agent consumers: keys emit in a fixed order, enum
reasons render as their string values, and every response is wrapped in an
envelope carrying ``schema_version`` plus the exchange context. Text output is a
compact one-line-per-pair summary for humans.

Both views are built from a :class:`~ccbalancer.models.RebalanceDecision` (and,
for `status`, its originating :class:`~ccbalancer.models.PairSnapshot`); the
quote-denominated metrics are computed once by the rebalance manager and reused
here, never recomputed.
'''

from __future__ import annotations

from typing import TYPE_CHECKING

from ccbalancer.constants import CCB_PREFIX, SCHEMA_VERSION

if TYPE_CHECKING:
    from ccbalancer.models import (
        AuthProfile,
        ExecutionResult,
        IndicatorSnapshot,
        PairSnapshot,
        PerformanceSnapshot,
        ProposedOrder,
        RebalanceDecision,
    )

__all__ = [
    'order_to_dict',
    'decision_to_dict',
    'status_to_dict',
    'indicator_to_dict',
    'performance_to_dict',
    'result_to_dict',
    'open_order_to_dict',
    'plan_response',
    'status_response',
    'analyze_response',
    'indicator_catalog_response',
    'performance_response',
    'performance_history_response',
    'decisions_response',
    'history_response',
    'export_response',
    'rebalance_dry_response',
    'rebalance_exec_response',
    'orders_response',
    'cancel_response',
    'masked_profile',
    'auth_list_response',
    'auth_status_response',
    'auth_whoami_response',
    'auth_list_lines',
    'auth_status_lines',
    'auth_whoami_lines',
    'plan_lines',
    'status_lines',
    'analyze_lines',
    'indicator_catalog_lines',
    'performance_lines',
    'performance_history_lines',
    'decisions_lines',
    'history_lines',
    'rebalance_dry_lines',
    'rebalance_exec_lines',
    'orders_lines',
    'cancel_lines',
]

# Pairs of (snapshot, decision) carried through the status path.
StatusRow = 'tuple[PairSnapshot, RebalanceDecision]'


def order_to_dict(order: ProposedOrder) -> dict[str, object]:
    '''Serialize a :class:`ProposedOrder` with a fixed key order.'''
    return {
        'side': order.side.value,
        'amount': order.amount,
        'limit_price': order.limit_price,
        'notional': order.notional,
        'clamped': order.clamped,
    }


def result_to_dict(result: ExecutionResult) -> dict[str, object]:
    '''Serialize an :class:`ExecutionResult` with a fixed key order.'''
    return {
        'symbol': result.symbol,
        'placed': result.placed,
        'status': result.status,
        'reason': result.reason,
        'side': result.side,
        'amount': result.amount,
        'price': result.price,
        'notional': result.notional,
        'order_id': result.order_id,
        'detail': result.detail,
    }


def open_order_to_dict(order: dict[str, object]) -> dict[str, object]:
    '''Serialize one exchange open order, flagging whether the tool placed it.'''
    client_id = order.get('clientOrderId')
    ours = isinstance(client_id, str) and client_id.startswith(CCB_PREFIX)
    return {
        'id': order.get('id'),
        'symbol': order.get('symbol'),
        'side': order.get('side'),
        'amount': order.get('amount'),
        'price': order.get('price'),
        'client_order_id': client_id,
        'ours': ours,
    }


def decision_to_dict(decision: RebalanceDecision) -> dict[str, object]:
    '''Serialize a :class:`RebalanceDecision` with a fixed key order.'''
    order = decision.proposed_order
    return {
        'symbol': decision.symbol,
        'rebalance': decision.rebalance,
        'reason': decision.reason.value,
        'drift_pct': decision.drift_pct,
        'target_volatile_pct': decision.target_volatile_pct,
        'current_volatile_pct': decision.current_volatile_pct,
        'total_value': decision.total_value,
        'last_rebalance_at': decision.last_rebalance_at,
        'days_since_last': decision.days_since_last,
        'proposed_order': order_to_dict(order) if order else None,
        'detail': decision.detail,
    }


def status_to_dict(snapshot: PairSnapshot, decision: RebalanceDecision) -> dict[str, object]:
    '''Serialize one pair's allocation status (current vs target + holdings).'''
    return {
        'symbol': snapshot.symbol,
        'target_volatile_pct': decision.target_volatile_pct,
        'current_volatile_pct': decision.current_volatile_pct,
        'drift_pct': decision.drift_pct,
        'total_value': decision.total_value,
        'base_total': snapshot.base_total,
        'stable_total': snapshot.stable_total,
        'price': snapshot.price,
        'last_rebalance_at': decision.last_rebalance_at,
        'days_since_last': decision.days_since_last,
    }


def indicator_to_dict(snapshot: IndicatorSnapshot) -> dict[str, object]:
    '''Serialize an :class:`IndicatorSnapshot` with a fixed key order.'''
    return {
        'timeframe': snapshot.timeframe,
        'as_of': snapshot.as_of,
        'candle_count': snapshot.candle_count,
        'stale': snapshot.stale,
        'close': snapshot.close,
        'rsi': {
            'value': snapshot.rsi,
            'overbought': snapshot.rsi_overbought,
            'oversold': snapshot.rsi_oversold,
            'zone': snapshot.rsi_zone,
        },
        'macd': snapshot.macd,
        'macd_signal': snapshot.macd_signal,
        'macd_histogram': snapshot.macd_histogram,
        'ema': snapshot.ema,
        'bollinger': {
            'upper': snapshot.bollinger_upper,
            'middle': snapshot.bollinger_middle,
            'lower': snapshot.bollinger_lower,
        },
        'atr': snapshot.atr,
        'volume': snapshot.volume,
        'volume_ma': snapshot.volume_ma,
        'fib': snapshot.fib,
    }


def performance_to_dict(snapshot: PerformanceSnapshot) -> dict[str, object]:
    '''Serialize a :class:`PerformanceSnapshot` with a fixed key order.'''
    return {
        'symbol': snapshot.symbol,
        'position_qty': snapshot.position_qty,
        'avg_cost': snapshot.avg_cost,
        'cost_basis': snapshot.cost_basis,
        'current_price': snapshot.current_price,
        'market_value': snapshot.market_value,
        'realized_pnl': snapshot.realized_pnl,
        'unrealized_pnl': snapshot.unrealized_pnl,
        'total_pnl': snapshot.total_pnl,
        'fees_paid': snapshot.fees_paid,
        'invested': snapshot.invested,
        'roi_pct': snapshot.roi_pct,
        'from_baseline': snapshot.from_baseline,
        'fill_count': snapshot.fill_count,
    }


def plan_response(
    decisions: list[RebalanceDecision],
    meta: dict[str, object],
    confirm_token: str | None = None,
) -> dict[str, object]:
    '''Build the `plan` JSON envelope from per-pair decisions.

    When any pair is actionable, ``confirm_token`` carries the handshake token the
    user passes to ``rebalance --execute --confirm``; it is ``None`` for a no-op plan.
    '''
    body = {'confirm_token': confirm_token, 'pairs': [decision_to_dict(d) for d in decisions]}
    return _envelope('plan', meta, body)


def analyze_response(
    symbol: str,
    timeframes: list[str],
    snapshots: list[IndicatorSnapshot | None],
    meta: dict[str, object],
) -> dict[str, object]:
    '''Build the `analyze` JSON envelope; ``None`` snapshots become unavailable.'''
    available = [indicator_to_dict(snap) for snap in snapshots if snap is not None]
    unavailable = [tf for tf, snap in zip(timeframes, snapshots) if snap is None]
    body = {'symbol': symbol, 'timeframes': available, 'unavailable_timeframes': unavailable}
    return _envelope('analyze', meta, body)


def status_response(rows: list[StatusRow], meta: dict[str, object]) -> dict[str, object]:
    '''Build the `status` JSON envelope from per-pair (snapshot, decision) rows.'''
    pairs = [status_to_dict(snapshot, decision) for snapshot, decision in rows]
    return _envelope('status', meta, {'pairs': pairs})


def performance_response(
    snapshots: list[PerformanceSnapshot],
    totals: dict[str, object],
    meta: dict[str, object],
) -> dict[str, object]:
    '''Build the `performance` JSON envelope: per-pair P&L plus portfolio totals.'''
    body = {'pairs': [performance_to_dict(s) for s in snapshots], 'portfolio': totals}
    return _envelope('performance', meta, body)


def performance_history_response(
    records: list[dict[str, object]], generated_at: str
) -> dict[str, object]:
    '''Build the `performance --history` JSON envelope (realized P&L, no network).'''
    body = {'count': len(records), 'pairs': records}
    return _local_envelope('performance', generated_at, body)


def plan_lines(decisions: list[RebalanceDecision]) -> list[str]:
    '''Render `plan` decisions as one text line per pair.'''
    return [_plan_line(decision) for decision in decisions]


def status_lines(rows: list[StatusRow]) -> list[str]:
    '''Render `status` rows as one text line per pair.'''
    return [_status_line(snapshot, decision) for snapshot, decision in rows]


def performance_lines(
    snapshots: list[PerformanceSnapshot], totals: dict[str, object]
) -> list[str]:
    '''Render `performance` as one line per pair plus a portfolio total line.'''
    lines = [_performance_line(snapshot) for snapshot in snapshots]
    if snapshots:
        lines.append(_performance_total_line(totals))
    return lines


def performance_history_lines(records: list[dict[str, object]]) -> list[str]:
    '''Render `performance --history` as one realized-P&L line per symbol.'''
    return [_performance_history_line(record) for record in records]


def indicator_catalog_response(catalog: list[dict[str, object]], generated_at: str) -> dict[str, object]:
    '''Build the `indicator list` JSON envelope from the registry catalog.

    Local command (no exchange context), so the envelope is the registry
    description plus ``schema_version`` for the agent's discovery.
    '''
    return _local_envelope('indicator list', generated_at, {'indicators': catalog})


def decisions_response(records: list[dict[str, object]], generated_at: str) -> dict[str, object]:
    '''Build the `decisions` JSON envelope from logged decision records.'''
    body = {'count': len(records), 'decisions': records}
    return _local_envelope('decisions', generated_at, body)


def history_response(events: list[dict[str, object]], generated_at: str) -> dict[str, object]:
    '''Build the `history` JSON envelope from logged rebalance events.'''
    body = {'count': len(events), 'history': events}
    return _local_envelope('history', generated_at, body)


def export_response(
    decisions: list[dict[str, object]],
    history: list[dict[str, object]],
    generated_at: str,
) -> dict[str, object]:
    '''Build the `export` JSON document bundling the local audit logs.'''
    body = {'decisions': decisions, 'history': history}
    return _local_envelope('export', generated_at, body)


def rebalance_dry_response(
    decisions: list[RebalanceDecision], meta: dict[str, object], confirm_token: str | None
) -> dict[str, object]:
    '''Build the dry-run `rebalance` envelope: the plan plus its confirm-token.'''
    body = {
        'dry_run': True,
        'confirm_token': confirm_token,
        'pairs': [decision_to_dict(d) for d in decisions],
    }
    return _envelope('rebalance', meta, body)


def rebalance_exec_response(
    results: list[ExecutionResult], meta: dict[str, object], confirm_token: str | None
) -> dict[str, object]:
    '''Build the executed `rebalance` envelope from per-pair execution results.'''
    body = {
        'dry_run': False,
        'confirm_token': confirm_token,
        'results': [result_to_dict(r) for r in results],
    }
    return _envelope('rebalance', meta, body)


def orders_response(orders: list[dict[str, object]], meta: dict[str, object]) -> dict[str, object]:
    '''Build the `orders` envelope listing open orders (ours flagged).'''
    return _envelope('orders', meta, {'orders': [open_order_to_dict(o) for o in orders]})


def cancel_response(
    orders: list[dict[str, object]], meta: dict[str, object], *, dry_run: bool
) -> dict[str, object]:
    '''Build the `cancel` envelope: the tool's open orders that were (or would be) cancelled.'''
    body = {'dry_run': dry_run, 'cancelled': [open_order_to_dict(o) for o in orders]}
    return _envelope('cancel', meta, body)


def decisions_lines(records: list[dict[str, object]]) -> list[str]:
    '''Render logged decisions as one text line per record.'''
    return [_decision_record_line(record) for record in records]


def history_lines(events: list[dict[str, object]]) -> list[str]:
    '''Render logged rebalance events as one text line per record.'''
    return [_history_event_line(event) for event in events]


def rebalance_dry_lines(
    decisions: list[RebalanceDecision], confirm_token: str | None
) -> list[str]:
    '''Render the dry-run `rebalance` plan plus a confirm hint.'''
    lines = [_plan_line(decision) for decision in decisions]
    if confirm_token:
        lines.append(f'(dry-run) confirm with: rebalance --execute --confirm {confirm_token}')
    else:
        lines.append('(dry-run) nothing to rebalance')
    return lines


def rebalance_exec_lines(results: list[ExecutionResult]) -> list[str]:
    '''Render executed `rebalance` results as one text line per pair.'''
    return [_result_line(result) for result in results]


def orders_lines(orders: list[dict[str, object]]) -> list[str]:
    '''Render open orders as one text line per order.'''
    return [_open_order_line(order) for order in orders]


def cancel_lines(orders: list[dict[str, object]], *, dry_run: bool) -> list[str]:
    '''Render the orders that were (or, in dry-run, would be) cancelled.'''
    verb = 'would cancel' if dry_run else 'cancelled'
    return [f'{verb} {_open_order_line(order)}' for order in orders]


def indicator_catalog_lines(catalog: list[dict[str, object]]) -> list[str]:
    '''Render the indicator catalog as text: one header + indented params.'''
    lines: list[str] = []
    for indicator in catalog:
        lines.append(f'{indicator["name"]}  {indicator["description"]}')
        lines.extend(_param_line(param) for param in indicator['params'])
    return lines


def _param_line(param: dict[str, object]) -> str:
    return (
        f'  {param["name"]} = {param["value"]}  '
        f'({param["type"]}, default {param["default"]})  {param["description"]}'
    )


def analyze_lines(
    symbol: str,
    timeframes: list[str],
    snapshots: list[IndicatorSnapshot | None],
) -> list[str]:
    '''Render `analyze` results as a header plus one line per timeframe.'''
    lines = [symbol]
    for timeframe, snapshot in zip(timeframes, snapshots):
        if snapshot is None:
            lines.append(f'  {timeframe}: (unavailable)')
        else:
            lines.append(_analyze_line(snapshot))
    return lines


def masked_profile(profile: AuthProfile) -> dict[str, object]:
    '''Serialize a profile with every secret masked (never the full value).'''
    return {
        'name': profile.name,
        'exchange': profile.exchange,
        'testnet': profile.testnet,
        'api_key': _mask_secret(profile.api_key),
        'api_secret': _mask_secret(profile.api_secret),
        'password': _mask_secret(profile.password),
    }


def auth_list_response(
    profiles: list[AuthProfile], active: str | None, generated_at: str
) -> dict[str, object]:
    '''Build the `auth list` JSON envelope (secrets masked).'''
    body = {'active': active, 'profiles': [masked_profile(p) for p in profiles]}
    return _local_envelope('auth list', generated_at, body)


def auth_status_response(
    profile: AuthProfile, active: str | None, valid: bool | None, generated_at: str
) -> dict[str, object]:
    '''Build the `auth status` JSON envelope; ``valid`` is true/false/null.'''
    body = {'active': active, 'valid': valid, 'profile': masked_profile(profile)}
    return _local_envelope('auth status', generated_at, body)


def auth_whoami_response(profile: AuthProfile, generated_at: str) -> dict[str, object]:
    '''Build the `auth whoami` JSON envelope (secrets masked).'''
    return _local_envelope('auth whoami', generated_at, {'profile': masked_profile(profile)})


def auth_list_lines(profiles: list[AuthProfile], active: str | None) -> list[str]:
    '''Render profiles as one line each, marking the active one.'''
    return [_auth_profile_line(profile, active) for profile in profiles]


def auth_status_lines(profile: AuthProfile, active: str | None, valid: bool | None) -> list[str]:
    '''Render the active profile's status as human-readable lines.'''
    state = {True: 'valid', False: 'invalid', None: 'unknown (offline)'}[valid]
    active_mark = ' (active)' if profile.name == active else ''
    return [
        f'profile: {profile.name}{active_mark}',
        f'exchange: {profile.exchange} ({_net(profile.testnet)})',
        f'key: {_mask_secret(profile.api_key)}',
        f'credentials: {state}',
    ]


def auth_whoami_lines(profile: AuthProfile) -> list[str]:
    '''Render the active profile identity as a single line.'''
    return [f'{profile.name}  {profile.exchange} ({_net(profile.testnet)})']


def _auth_profile_line(profile: AuthProfile, active: str | None) -> str:
    marker = '*' if profile.name == active else ' '
    return (
        f'{marker} {profile.name}  {profile.exchange}  {_net(profile.testnet)}  '
        f'key={_mask_secret(profile.api_key)}'
    )


def _net(testnet: bool) -> str:
    return 'testnet' if testnet else 'live'


def _mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return '***'
    return f'{secret[:4]}...{secret[-4:]}'


def _envelope(command: str, meta: dict[str, object], body: dict[str, object]) -> dict[str, object]:
    return {
        'schema_version': SCHEMA_VERSION,
        'command': command,
        'exchange': meta['exchange'],
        'testnet': meta['testnet'],
        'generated_at': meta['generated_at'],
        **body,
    }


def _local_envelope(command: str, generated_at: str, body: dict[str, object]) -> dict[str, object]:
    '''Envelope for local commands that carry no live exchange context.'''
    return {
        'schema_version': SCHEMA_VERSION,
        'command': command,
        'generated_at': generated_at,
        **body,
    }


def _decision_record_line(record: dict[str, object]) -> str:
    drift = _signed_pp(record.get('drift_pct'))
    order = record.get('proposed_order')
    action = _order_summary(order) if record.get('rebalance') and order else 'hold'
    return (
        f'{record.get("ts")}  {record.get("symbol")}  {action}  '
        f'drift {drift}  [{record.get("reason")}]'
    )


def _history_event_line(event: dict[str, object]) -> str:
    quote = _quote(str(event.get('symbol', '')))
    notional = event.get('notional')
    notional_str = f'{notional:.2f}' if isinstance(notional, (int, float)) else str(notional)
    return (
        f'{event.get("ts")}  {event.get("symbol")}  {event.get("side")} '
        f'{event.get("amount")} @ {event.get("price")} ({notional_str} {quote})  '
        f'[{event.get("reason")}] {event.get("status")}'
    )


def _result_line(result: ExecutionResult) -> str:
    if result.side is None:
        return f'{result.symbol}  {result.status}  [{result.reason}]'
    quote = _quote(result.symbol)
    return (
        f'{result.symbol}  {result.status}  {result.side} {result.amount:g} @ '
        f'{result.price:g} ({result.notional:.2f} {quote})  [{result.reason}]'
    )


def _open_order_line(order: dict[str, object]) -> str:
    mark = '*' if (str(order.get('clientOrderId') or '')).startswith(CCB_PREFIX) else ' '
    return (
        f'{mark} {order.get("symbol")}  {order.get("side")} {order.get("amount")} @ '
        f'{order.get("price")}  id {order.get("id")}'
    )


def _order_summary(order: dict[str, object]) -> str:
    return (
        f'{order.get("side")} {order.get("amount")} @ {order.get("limit_price")} '
        f'({order.get("notional")} notional)'
    )


def _signed_pp(value: object) -> str:
    if not isinstance(value, (int, float)):
        return 'n/a'
    return f'{value:+.2f}pp'


def _plan_line(decision: RebalanceDecision) -> str:
    drift = f'{decision.drift_pct:+.2f}pp'
    action = _action(decision)
    return f'{decision.symbol}  {action}  drift {drift}  [{decision.reason.value}]'


def _action(decision: RebalanceDecision) -> str:
    order = decision.proposed_order
    if not decision.rebalance or order is None:
        return 'hold'
    return (
        f'REBALANCE {order.side.value} {order.amount:g} @ {order.limit_price:g} '
        f'({order.notional:.2f} {_quote(decision.symbol)})'
    )


def _status_line(snapshot: PairSnapshot, decision: RebalanceDecision) -> str:
    last = _format_last(decision.last_rebalance_at, decision.days_since_last)
    return (
        f'{snapshot.symbol}  current {decision.current_volatile_pct:.2f}% / '
        f'target {decision.target_volatile_pct:.2f}%  drift {decision.drift_pct:+.2f}pp  '
        f'value {decision.total_value:.2f} {_quote(snapshot.symbol)}  last {last}'
    )


def _performance_line(snapshot: PerformanceSnapshot) -> str:
    quote = _quote(snapshot.symbol)
    tag = ' (baseline)' if snapshot.from_baseline else ''
    return (
        f'{snapshot.symbol}  pos {snapshot.position_qty:g}  '
        f'value {snapshot.market_value:.2f} {quote}  '
        f'realized {snapshot.realized_pnl:+.2f}  unrealized {snapshot.unrealized_pnl:+.2f}  '
        f'pnl {snapshot.total_pnl:+.2f}  roi {_roi(snapshot.roi_pct)}{tag}'
    )


def _performance_total_line(totals: dict[str, object]) -> str:
    return (
        f'TOTAL  value {_money(totals.get("market_value"))}  '
        f'realized {_money(totals.get("realized_pnl"), signed=True)}  '
        f'unrealized {_money(totals.get("unrealized_pnl"), signed=True)}  '
        f'pnl {_money(totals.get("total_pnl"), signed=True)}  roi {_roi(totals.get("roi_pct"))}'
    )


def _performance_history_line(record: dict[str, object]) -> str:
    quote = _quote(str(record.get('symbol', '')))
    return (
        f'{record.get("symbol")}  realized {_money(record.get("realized_pnl"), signed=True)} {quote}  '
        f'fees {_money(record.get("fees_paid"))}  pos {record.get("position_qty")}  '
        f'({record.get("fill_count")} fills)'
    )


def _roi(value: object) -> str:
    return 'n/a' if not isinstance(value, (int, float)) else f'{value:+.2f}%'


def _money(value: object, *, signed: bool = False) -> str:
    if not isinstance(value, (int, float)):
        return 'n/a'
    return f'{value:+.2f}' if signed else f'{value:.2f}'


def _format_last(last_at: str | None, days_since: float | None) -> str:
    if not last_at:
        return 'never'
    if days_since is None:
        return last_at
    return f'{last_at} ({days_since:.1f}d ago)'


def _analyze_line(snapshot: IndicatorSnapshot) -> str:
    flag = ' [stale]' if snapshot.stale else ''
    zone = f' ({snapshot.rsi_zone})' if snapshot.rsi_zone else ''
    return (
        f'  {snapshot.timeframe}  close {_fmt(snapshot.close)}  rsi {_fmt(snapshot.rsi)}{zone}  '
        f'macd {_fmt(snapshot.macd)}/{_fmt(snapshot.macd_signal)}  atr {_fmt(snapshot.atr)}  '
        f'vol {_fmt(snapshot.volume)}/{_fmt(snapshot.volume_ma)}  as_of {snapshot.as_of}{flag}'
    )


def _fmt(value: float | None) -> str:
    return 'n/a' if value is None else f'{value:g}'


def _quote(symbol: str) -> str:
    parts = symbol.split('/')
    return parts[1] if len(parts) == 2 else ''
