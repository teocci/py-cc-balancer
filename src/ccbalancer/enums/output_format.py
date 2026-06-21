'''Output format enumeration for CLI rendering.'''

from __future__ import annotations

from enum import Enum

__all__ = ['OutputFormat']


class OutputFormat(Enum):
    '''How command output is rendered.'''

    TEXT = 'text'
    JSON = 'json'
