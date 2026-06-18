'''Logging configuration for the ccbalancer CLI.

Logs are written to stderr so stdout stays reserved for machine-readable output
(JSON consumed by an AI agent). Library modules must use
``logging.getLogger(__name__)`` and never configure logging themselves; only the
CLI entry point calls :func:`configure_logging`.
'''

from __future__ import annotations

import logging
import sys

__all__ = ['configure_logging']

_LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


def configure_logging(level: int = logging.INFO) -> None:
    '''Configure root logging to emit to stderr.

    Args:
        level: Minimum level to emit (e.g. ``logging.DEBUG``).
    '''
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
