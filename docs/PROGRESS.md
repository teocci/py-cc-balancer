# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 5 — State store + portfolio snapshots

## Phase status

| Phase | Title | Status |
|---|---|---|
| 0 | Environment, scaffold & docs | done |
| 1 | Domain primitives | done |
| 2 | Configuration (settings + secrets) | done |
| 3 | Portfolio store + `pair` commands | done |
| 4 | Exchange store (ccxt wrapper) | done |
| 5 | State store + portfolio snapshots | pending |
| 6 | Rebalance decision logic | pending |
| 7 | Read-only CLI (`status`, `plan`) | pending |
| 8 | Execution (`rebalance`, `orders`, `cancel`) | pending |
| 9 | Hardening & docs finalize | pending |
| 10 | Packaging, portable bundle & release CI | pending |

## Next action

Implement Phase 5: `stores/state_store.py` (`state.json` + `history.jsonl`), `utils/timeutil.py`,
`utils/money.py`, and `managers/portfolio_manager.py` (balances + tickers + state → `PairSnapshot`).
See `docs/phases/phase-5.md`. DoD: `test_state_store` + `test_portfolio_manager` green; snapshot math
and `last_rebalance_at` wiring verified; state round-trips.
