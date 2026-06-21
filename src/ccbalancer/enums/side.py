'''Order side enumeration.'''

from __future__ import annotations

from enum import Enum

__all__ = ['OrderSide']


class OrderSide(Enum):
    '''Side of a spot order (values match ccxt's expected strings).'''

    BUY = 'buy'
    SELL = 'sell'
