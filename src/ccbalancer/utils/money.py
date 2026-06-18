'''Money and precision helpers backed by :class:`~decimal.Decimal`.

Float arithmetic is unsafe for order sizing, so amount/price math is routed
through :class:`Decimal` here. Exchange precision is normalized to a count of
decimal places so the rest of the app reasons in whole decimals regardless of the
exchange's precision mode (decimal-places vs tick-size).
'''

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

__all__ = ['to_decimal', 'precision_to_decimals', 'round_amount', 'notional']


def to_decimal(value: float | int | str) -> Decimal:
    '''Convert a value to :class:`Decimal` via ``str`` to avoid float noise.'''
    return Decimal(str(value))


def precision_to_decimals(value: float | int | None) -> int | None:
    '''Normalize a ccxt amount precision to a count of decimal places.

    An integer is already a decimal-place count and is returned as-is. A
    fractional step size (e.g. ``0.001``) is converted to its place count
    (``3``). Step sizes of one or greater map to ``0``. Unknown precision
    (``None``) returns ``None``.
    '''
    if value is None:
        return None
    if isinstance(value, int):
        return value
    exponent = to_decimal(value).normalize().as_tuple().exponent
    if isinstance(exponent, int) and exponent < 0:
        return -exponent
    return 0


def round_amount(amount: float, decimals: int | None) -> float:
    '''Floor ``amount`` to ``decimals`` places (never round up past balance).'''
    if decimals is None:
        return amount
    quantum = Decimal(1).scaleb(-decimals)
    return float(to_decimal(amount).quantize(quantum, rounding=ROUND_DOWN))


def notional(amount: float, price: float) -> float:
    '''Order value in quote terms (``amount * price``), computed via Decimal.'''
    return float(to_decimal(amount) * to_decimal(price))
