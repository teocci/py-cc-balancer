'''Append-only fill ledger.

Every executed order writes one fill record to ``ledger.jsonl`` under the app
directory: the side, price, quantity, and fee at execution time. The ledger is the
source of truth for cost-basis and realized/unrealized P&L (consumed by the
performance command in a later phase). This store is the only code that reads or
writes the file; the exchange is never touched here. Corrupt lines raise
:class:`StateError`.
'''

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccbalancer.exceptions import StateError
from ccbalancer.models import Fill

__all__ = ['LedgerStore', 'fill_to_dict']


def fill_to_dict(fill: Fill) -> dict[str, object]:
    '''Serialize a :class:`Fill` to a plain dict with a fixed key order.'''
    return {
        'ts': fill.ts,
        'symbol': fill.symbol,
        'side': fill.side,
        'price': fill.price,
        'qty': fill.qty,
        'fee': fill.fee,
        'fee_currency': fill.fee_currency,
        'order_id': fill.order_id,
    }


@dataclass(slots=True)
class LedgerStore:
    '''Append-only read/write access to ``ledger.jsonl``.

    Attributes:
        ledger_path: Location of ``ledger.jsonl``.
    '''

    ledger_path: Path

    def append_fill(self, fill: Fill) -> None:
        '''Append one fill as a JSON line to ``ledger.jsonl``.'''
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(fill_to_dict(fill), separators=(',', ':'), default=str) + '\n'
        with open(self.ledger_path, 'a', encoding='utf-8') as handle:
            handle.write(line)

    def load(self) -> list[dict[str, object]]:
        '''Return all fill records in append order (empty if the file is absent).

        Raises:
            StateError: If the file is unreadable or contains a malformed line.
        '''
        if not self.ledger_path.is_file():
            return []
        try:
            text = self.ledger_path.read_text(encoding='utf-8')
        except OSError as exc:
            raise StateError(f'Cannot read ledger {self.ledger_path}: {exc}') from exc
        return [self._parse_line(line) for line in text.splitlines() if line.strip()]

    def _parse_line(self, line: str) -> dict[str, object]:
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise StateError(f'Corrupt fill record in {self.ledger_path}: {exc}') from exc
