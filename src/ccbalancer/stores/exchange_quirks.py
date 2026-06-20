'''Per-exchange behavioral quirks consumed by the execution path.

`ccxt` unifies most of the exchange API, but a few behaviors still differ between
venues and the order placement/cancel code needs to branch on them. Centralizing
those differences here keeps :class:`~ccbalancer.stores.exchange.ExchangeStore`
exchange-agnostic and gives the quirks a single, testable source of truth (the
"quirks matrix" in the tests). Precision and min-notional are *not* quirks: they
are read per-market from ``load_markets`` and handled uniformly by the decision
guards, so they are validated by the matrix rather than encoded here.
'''

from __future__ import annotations

from dataclasses import dataclass

from ccbalancer import constants as c
from ccbalancer.exceptions import ExchangeError

__all__ = ['ExchangeQuirks', 'quirks_for']


@dataclass(slots=True, frozen=True)
class ExchangeQuirks:
    '''Execution-relevant differences for one exchange.

    Attributes:
        exchange_id: ccxt exchange id the quirks apply to.
        client_order_id_param: ccxt ``params`` key carrying our ``CCB_PREFIX`` tag
            when placing an order.
        cancel_requires_symbol: Whether ``cancel_order`` must be passed the symbol
            (true for both v1 CEXes; kept explicit so a future venue can opt out).
        max_client_order_id_len: Maximum accepted clientOrderId length; tags are
            truncated to fit.
    '''

    exchange_id: str
    client_order_id_param: str
    cancel_requires_symbol: bool
    max_client_order_id_len: int


# The quirks matrix. ccxt accepts the unified ``clientOrderId`` param and maps it
# to each venue's native field (Bybit ``orderLinkId``, Binance ``newClientOrderId``),
# so the param key is uniform; the lengths reflect each venue's documented limit.
_QUIRKS: dict[str, ExchangeQuirks] = {
    'bybit': ExchangeQuirks('bybit', 'clientOrderId', True, 36),
    'binance': ExchangeQuirks('binance', 'clientOrderId', True, 36),
    # OKX maps the unified clientOrderId to its native clOrdId, which accepts
    # alphanumerics up to 32 chars; cancel requires the symbol like the others.
    'okx': ExchangeQuirks('okx', 'clientOrderId', True, 32),
}


def quirks_for(exchange_id: str) -> ExchangeQuirks:
    '''Return the quirks for ``exchange_id``.

    Raises:
        ExchangeError: If the exchange has no quirks entry (unsupported for trading).
    '''
    try:
        return _QUIRKS[exchange_id]
    except KeyError as exc:
        supported = ', '.join(sorted(_QUIRKS))
        raise ExchangeError(
            f'No execution quirks for {exchange_id!r}; supported: {supported}'
        ) from exc


# Sanity: every tradable exchange must have a quirks entry.
assert set(_QUIRKS) == set(c.SUPPORTED_EXCHANGES)
