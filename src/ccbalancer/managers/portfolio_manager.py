'''Assemble per-pair snapshots from exchange data and local state.

The manager is the read-side orchestrator: it pulls balances and tickers from the
injected exchange store, reads each pair's last rebalance time from the state
store, and combines them into immutable :class:`PairSnapshot` objects. It performs
no network calls of its own beyond delegating to the store, and never imports ccxt.
'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ccbalancer.models import PairSnapshot
from ccbalancer.utils.money import precision_to_decimals

if TYPE_CHECKING:
    from ccbalancer.models import PairConfig
    from ccbalancer.stores.exchange import ExchangeStore
    from ccbalancer.stores.state_store import StateStore

__all__ = ['PortfolioManager']


@dataclass(slots=True)
class PortfolioManager:
    '''Builds :class:`PairSnapshot` objects from balances, tickers, and state.

    Attributes:
        exchange: Exchange store providing balances, tickers, and markets.
        state_store: State store providing each pair's last rebalance time.
    '''

    exchange: ExchangeStore
    state_store: StateStore

    def snapshot(
        self,
        pair: PairConfig,
        *,
        balance: dict[str, object] | None = None,
        market: dict[str, object] | None = None,
    ) -> PairSnapshot:
        '''Build a snapshot for a single pair.

        Args:
            pair: The pair configuration to snapshot.
            balance: Prefetched balance structure; fetched when omitted.
            market: Prefetched market entry; precision and active status default
                to unknown/active when omitted.
        '''
        if balance is None:
            balance = self.exchange.fetch_balance()
        ticker = self.exchange.fetch_ticker(pair.symbol)
        base_free, base_total = _holdings(balance, pair.base)
        stable_free, stable_total = _holdings(balance, pair.quote)
        price = _num(ticker.get('last'))
        return PairSnapshot(
            symbol=pair.symbol,
            base_total=base_total,
            base_free=base_free,
            stable_total=stable_total,
            stable_free=stable_free,
            price=price,
            bid=_num(ticker.get('bid'), price),
            ask=_num(ticker.get('ask'), price),
            amount_precision=_amount_precision(market),
            market_active=_market_active(market),
            last_rebalance_at=self.state_store.last_rebalance_at(pair.symbol),
        )

    def snapshots(self, pairs: list[PairConfig]) -> list[PairSnapshot]:
        '''Build snapshots for many pairs with a single balance/markets fetch.'''
        balance = self.exchange.fetch_balance()
        markets = self.exchange.load_markets()
        return [
            self.snapshot(pair, balance=balance, market=markets.get(pair.symbol))
            for pair in pairs
        ]


def _holdings(balance: dict[str, object], asset: str) -> tuple[float, float]:
    free = _num((balance.get('free') or {}).get(asset))
    total = _num((balance.get('total') or {}).get(asset))
    return free, total


def _num(value: object, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _amount_precision(market: dict[str, object] | None) -> int | None:
    if not market:
        return None
    precision = market.get('precision') or {}
    return precision_to_decimals(precision.get('amount'))


def _market_active(market: dict[str, object] | None) -> bool:
    if not market:
        return True
    active = market.get('active')
    return True if active is None else bool(active)
