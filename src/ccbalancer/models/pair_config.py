'''Per-pair portfolio configuration.

A :class:`PairConfig` is the user's desired target for one trading pair, stored
in ``portfolio.json`` and managed via the ``pair`` CLI commands.
'''

from __future__ import annotations

from dataclasses import dataclass

from ccbalancer.constants import RATIO_TOTAL_PCT
from ccbalancer.exceptions import PortfolioError

__all__ = ['PairConfig']

_RATIO_TOLERANCE = 1e-6


@dataclass(slots=True, frozen=True)
class PairConfig:
    '''Desired target for a single pair (volatile base vs stable quote).

    Attributes:
        symbol: Trading pair as ``BASE/QUOTE`` (e.g. ``'BTC/USDT'``).
        target_volatile_pct: Desired share of value held in the base asset.
        target_stable_pct: Desired share of value held in the quote asset.
        band_pct: No-trade band; rebalance only if drift exceeds this.
        min_notional: Configured floor (quote terms) below which no trade.
        max_trade_notional: Optional per-trade cap (quote terms); 0 = no cap.
        entry_price: Price (quote terms) when the position was first opened.
        entry_ts: UTC ISO-8601 of the entry, or ``None``.
        invested_capital: Quote-terms capital committed to the pair, or ``None``.
        target_set_price: Price when the current target ratio was chosen, or ``None``.
        target_set_ts: UTC ISO-8601 of when the target was set, or ``None``.
    '''

    symbol: str
    target_volatile_pct: float
    target_stable_pct: float
    band_pct: float
    min_notional: float
    max_trade_notional: float = 0.0
    entry_price: float | None = None
    entry_ts: str | None = None
    invested_capital: float | None = None
    target_set_price: float | None = None
    target_set_ts: str | None = None

    def __post_init__(self) -> None:
        self._validate_symbol()
        self._validate_ratio()
        self._validate_non_negative()
        self._validate_baselines()

    @property
    def base(self) -> str:
        '''Base (volatile) asset, e.g. ``'BTC'``.'''
        return self.symbol.split('/', 1)[0]

    @property
    def quote(self) -> str:
        '''Quote (stable) asset, e.g. ``'USDT'``.'''
        return self.symbol.split('/', 1)[1]

    def _validate_symbol(self) -> None:
        parts = self.symbol.split('/')
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise PortfolioError(f'Invalid symbol {self.symbol!r}; expected BASE/QUOTE')

    def _validate_ratio(self) -> None:
        total = self.target_volatile_pct + self.target_stable_pct
        if abs(total - RATIO_TOTAL_PCT) > _RATIO_TOLERANCE:
            raise PortfolioError(
                f'{self.symbol}: target ratio must sum to {RATIO_TOTAL_PCT}, got {total}'
            )

    def _validate_non_negative(self) -> None:
        if min(self.band_pct, self.min_notional, self.max_trade_notional) < 0:
            raise PortfolioError(f'{self.symbol}: band/notional values must be non-negative')

    def _validate_baselines(self) -> None:
        baselines = (self.entry_price, self.invested_capital, self.target_set_price)
        if any(value is not None and value < 0 for value in baselines):
            raise PortfolioError(f'{self.symbol}: entry/invested/target-set values must be non-negative')
