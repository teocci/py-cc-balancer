'''Outcome reason for a rebalance decision.

``OK`` means a rebalance is warranted; every other value explains why the tool
chose not to trade this pair on this run.
'''

from __future__ import annotations

from enum import Enum

__all__ = ['SkipReason']


class SkipReason(Enum):
    '''Why a pair was or was not rebalanced.'''

    OK = 'ok'
    WITHIN_BAND = 'within_band'
    BELOW_MIN_NOTIONAL = 'below_min_notional'
    INSUFFICIENT_BALANCE = 'insufficient_balance'
    ABNORMAL_PRICE = 'abnormal_price'
    MARKET_UNAVAILABLE = 'market_unavailable'
    TOO_SOON = 'too_soon'
