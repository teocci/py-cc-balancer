'''Result of a backtest replay run.'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['SimRunResult']


@dataclass(frozen=True, slots=True)
class SimRunResult:
    '''Summary of one deterministic ``simulation run`` over a candle series.

    Attributes:
        symbol: The pair replayed, as ``BASE/QUOTE``.
        timeframe: Decision timeframe driving the replay (e.g. ``'1d'``).
        fill_timeframe: Finer timeframe resolving fills within each decision
            interval, or ``None`` when fills resolve on the decision bar itself.
        run_id: Deterministic id (hash of the run inputs); names the run directory.
        start_ms: First candle open time replayed (epoch ms).
        end_ms: Exclusive end of the replayed range (epoch ms).
        capital: Starting capital in quote terms (seeded all-stable).
        fee_rate: Maker fee rate applied to each fill's notional.
        bars: Number of candles replayed.
        orders_placed: Actionable orders that entered the resting book.
        fills: Orders that crossed a later bar and filled.
        rejects: Orders rejected below the exchange min-cost floor.
        final_base: Base asset held at the final candle.
        final_stable: Quote asset held at the final candle.
        final_value: Portfolio value at the final candle's close (quote terms).
        ledger_path: Location of the isolated sim ledger written for the run.
    '''

    symbol: str
    timeframe: str
    fill_timeframe: str | None
    run_id: str
    start_ms: int
    end_ms: int
    capital: float
    fee_rate: float
    bars: int
    orders_placed: int
    fills: int
    rejects: int
    final_base: float
    final_stable: float
    final_value: float
    ledger_path: str
