'''Shared pytest fixtures.'''

from __future__ import annotations

import pytest

from ccbalancer import config as config_mod
from ccbalancer.constants import (
    ENV_API_KEY,
    ENV_API_SECRET,
    ENV_CONFIG,
    ENV_EXCHANGE,
    ENV_TESTNET,
)


@pytest.fixture
def appdir(tmp_path, monkeypatch):
    '''Isolate the app dir and CWD; clear ccbalancer env vars.'''
    directory = tmp_path / '.ccbalancer'
    monkeypatch.setattr(config_mod, 'resolve_app_dir', lambda: directory)
    monkeypatch.chdir(tmp_path)
    for key in (ENV_API_KEY, ENV_API_SECRET, ENV_EXCHANGE, ENV_TESTNET, ENV_CONFIG):
        monkeypatch.delenv(key, raising=False)
    return directory
