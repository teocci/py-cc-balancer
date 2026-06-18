# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 4 — Exchange store (ccxt wrapper)

## Phase status

| Phase | Title | Status |
|---|---|---|
| 0 | Environment, scaffold & docs | done |
| 1 | Domain primitives | done |
| 2 | Configuration (settings + secrets) | done |
| 3 | Portfolio store + `pair` commands | done |
| 4 | Exchange store (ccxt wrapper) | pending |
| 5 | State store + portfolio snapshots | pending |
| 6 | Rebalance decision logic | pending |
| 7 | Read-only CLI (`status`, `plan`) | pending |
| 8 | Execution (`rebalance`, `orders`, `cancel`) | pending |
| 9 | Hardening & docs finalize | pending |
| 10 | Packaging, portable bundle & release CI | pending |

## Next action

Implement Phase 4: `stores/exchange.py` (thin ccxt wrapper, sandbox toggle) + `conftest.FakeExchangeStore`.
See `docs/phases/phase-4.md`. DoD: unit tests run fully on the fake (no network); manual testnet smoke
lists balances.
