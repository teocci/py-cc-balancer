'''Lifecycle status of a tracked outstanding order.'''

from __future__ import annotations

from enum import Enum

__all__ = ['OrderStatus']


class OrderStatus(Enum):
    '''State of an order in the open-orders store, from placement to terminal.

    ``UNCONFIRMED`` is the write-ahead state (recorded before ``create_order``, or
    left after a placement timeout — the exchange id is not yet known).
    ``OPEN``/``PARTIAL`` are live on the book; ``CLOSED``/``CANCELED`` are terminal
    (the reconciler drops the record once it books the final fill).
    '''

    UNCONFIRMED = 'unconfirmed'
    OPEN = 'open'
    PARTIAL = 'partial'
    CLOSED = 'closed'
    CANCELED = 'canceled'
