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

from ccbalancer.constants import SCHEMA_VERSION

if TYPE_CHECKING:
    from ccbalancer.models import (
        IndicatorSnapshot,
        PairSnapshot,
        ProposedOrder,
        RebalanceDecision,
    )

__all__ = [
    'order_to_dict',
    'decision_to_dict',
    'status_to_dict',
    'indicator_to_dict',
    'plan_response',
    'status_response',
    'analyze_response',
    'indicator_catalog_response',
    'plan_lines',
    'status_lines',
    'analyze_lines',
    'indicator_catalog_lines',
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


def plan_response(decisions: list[RebalanceDecision], meta: dict[str, object]) -> dict[str, object]:
    '''Build the `plan` JSON envelope from per-pair decisions.'''
    return _envelope('plan', meta, {'pairs': [decision_to_dict(d) for d in decisions]})


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


def plan_lines(decisions: list[RebalanceDecision]) -> list[str]:
    '''Render `plan` decisions as one text line per pair.'''
    return [_plan_line(decision) for decision in decisions]


def status_lines(rows: list[StatusRow]) -> list[str]:
    '''Render `status` rows as one text line per pair.'''
    return [_status_line(snapshot, decision) for snapshot, decision in rows]


def indicator_catalog_response(catalog: list[dict[str, object]], generated_at: str) -> dict[str, object]:
    '''Build the `indicator list` JSON envelope from the registry catalog.

    Local command (no exchange context), so the envelope is the registry
    description plus ``schema_version`` for the agent's discovery.
    '''
    return {
        'schema_version': SCHEMA_VERSION,
        'command': 'indicator list',
        'generated_at': generated_at,
        'indicators': catalog,
    }


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


def _envelope(command: str, meta: dict[str, object], body: dict[str, object]) -> dict[str, object]:
    return {
        'schema_version': SCHEMA_VERSION,
        'command': command,
        'exchange': meta['exchange'],
        'testnet': meta['testnet'],
        'generated_at': meta['generated_at'],
        **body,
    }


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
