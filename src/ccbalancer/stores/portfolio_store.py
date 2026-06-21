'''Portfolio persistence: CRUD over ``portfolio.json``.

The portfolio is user data (pairs and per-pair targets) managed exclusively
through the ``pair`` CLI commands. This store is the only code that reads or
writes ``portfolio.json``; it validates entries and forbids duplicates.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.exceptions import PortfolioError
from ccbalancer.models import PairConfig

__all__ = ['PortfolioStore', 'pair_to_dict']


def _opt_float(value: object) -> float | None:
    '''Coerce an optional numeric field to ``float``, preserving ``None``.'''
    return None if value is None else float(value)


def _opt_str(value: object) -> str | None:
    '''Coerce an optional text field to ``str``, preserving ``None``.'''
    return None if value is None else str(value)


def pair_to_dict(pair: PairConfig) -> dict[str, object]:
    '''Serialize a :class:`PairConfig` to a plain dict.'''
    return {
        'symbol': pair.symbol,
        'target_volatile_pct': pair.target_volatile_pct,
        'target_stable_pct': pair.target_stable_pct,
        'band_pct': pair.band_pct,
        'min_notional': pair.min_notional,
        'max_trade_notional': pair.max_trade_notional,
        'entry_price': pair.entry_price,
        'entry_ts': pair.entry_ts,
        'invested_capital': pair.invested_capital,
        'target_set_price': pair.target_set_price,
        'target_set_ts': pair.target_set_ts,
    }


@dataclass(slots=True)
class PortfolioStore:
    '''Read/write access to the portfolio file.

    Attributes:
        path: Location of ``portfolio.json``.
    '''

    path: Path

    def load(self) -> list[PairConfig]:
        '''Return all configured pairs (empty list if the file is absent).

        Raises:
            PortfolioError: If the file is unreadable or contains bad entries.
        '''
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise PortfolioError(f'Cannot read portfolio {self.path}: {exc}') from exc
        pairs = [self._from_dict(entry) for entry in data.get('pairs', [])]
        self._check_duplicates(pairs)
        return pairs

    def save(self, pairs: list[PairConfig]) -> None:
        '''Write all pairs atomically to the portfolio file.'''
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {'pairs': [pair_to_dict(pair) for pair in pairs]}
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def get(self, symbol: str) -> PairConfig | None:
        '''Return the pair for ``symbol`` (case-insensitive) or ``None``.'''
        target = symbol.upper()
        return next((pair for pair in self.load() if pair.symbol == target), None)

    def add(self, pair: PairConfig) -> None:
        '''Append a new pair.

        Raises:
            PortfolioError: If the symbol already exists.
        '''
        pairs = self.load()
        if any(existing.symbol == pair.symbol for existing in pairs):
            raise PortfolioError(f'Pair {pair.symbol} already exists; use `pair set`')
        pairs.append(pair)
        self.save(pairs)

    def replace(self, pair: PairConfig) -> None:
        '''Replace an existing pair (matched by symbol).

        Raises:
            PortfolioError: If the symbol is not present.
        '''
        pairs = self.load()
        updated = [pair if existing.symbol == pair.symbol else existing for existing in pairs]
        if all(existing.symbol != pair.symbol for existing in pairs):
            raise PortfolioError(f'Pair {pair.symbol} not found; use `pair add`')
        self.save(updated)

    def remove(self, symbol: str) -> None:
        '''Remove a pair by symbol.

        Raises:
            PortfolioError: If the symbol is not present.
        '''
        target = symbol.upper()
        pairs = self.load()
        remaining = [pair for pair in pairs if pair.symbol != target]
        if len(remaining) == len(pairs):
            raise PortfolioError(f'Pair {target} not found')
        self.save(remaining)

    def _from_dict(self, entry: dict[str, object]) -> PairConfig:
        try:
            return PairConfig(
                symbol=str(entry['symbol']).upper(),
                target_volatile_pct=float(entry['target_volatile_pct']),
                target_stable_pct=float(entry['target_stable_pct']),
                band_pct=float(entry['band_pct']),
                min_notional=float(entry['min_notional']),
                max_trade_notional=float(entry.get('max_trade_notional', 0.0)),
                entry_price=_opt_float(entry.get('entry_price')),
                entry_ts=_opt_str(entry.get('entry_ts')),
                invested_capital=_opt_float(entry.get('invested_capital')),
                target_set_price=_opt_float(entry.get('target_set_price')),
                target_set_ts=_opt_str(entry.get('target_set_ts')),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PortfolioError(f'Invalid pair entry {entry!r}: {exc}') from exc

    def _check_duplicates(self, pairs: list[PairConfig]) -> None:
        seen: set[str] = set()
        for pair in pairs:
            if pair.symbol in seen:
                raise PortfolioError(f'Duplicate pair {pair.symbol} in {self.path}')
            seen.add(pair.symbol)
