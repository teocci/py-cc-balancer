'''Custom exception hierarchy for ccbalancer.

All application errors derive from :class:`AppError` so callers can catch the
whole family. Specific subclasses carry domain meaning and map to CLI exit codes
in :mod:`ccbalancer.cli`.
'''

from __future__ import annotations

__all__ = [
    'AppError',
    'ConfigError',
    'PortfolioError',
    'StateError',
    'ExchangeError',
    'InsufficientBalanceError',
    'SanityCheckError',
    'OrderRejectedError',
]


class AppError(Exception):
    '''Base class for all ccbalancer errors.'''


class ConfigError(AppError):
    '''Invalid, missing, or unreadable configuration or secrets.'''


class PortfolioError(AppError):
    '''Invalid portfolio data or a rejected pair mutation.'''


class StateError(AppError):
    '''Corrupt or unreadable local state/history files.'''


class ExchangeError(AppError):
    '''A failure talking to the exchange (network, auth, API error).'''


class InsufficientBalanceError(AppError):
    '''Not enough free balance to perform a proposed order.'''


class SanityCheckError(AppError):
    '''A market datum failed a sanity check (e.g. abnormal price).'''


class OrderRejectedError(AppError):
    '''The exchange rejected an order placement.'''
