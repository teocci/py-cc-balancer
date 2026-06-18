# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 6 — Rebalance decision logic

## Phase status

| Phase | Title | Status |
|---|---|---|
| 0 | Environment, scaffold & docs | done |
| 1 | Domain primitives | done |
| 2 | Configuration (settings + secrets) | done |
| 3 | Portfolio store + `pair` commands | done |
| 4 | Exchange store (ccxt wrapper) | done |
| 5 | State store + portfolio snapshots | done |
| 6 | Rebalance decision logic | pending |
| 7 | Read-only CLI (`status`, `plan`) | pending |
| 8 | Execution (`rebalance`, `orders`, `cancel`) | pending |
| 9 | Hardening & docs finalize | pending |
| 10 | Packaging, portable bundle & release CI | pending |

## Next action

Implement Phase 6: `managers/rebalance_manager.py` — a pure `decide(pair, snapshot) -> RebalanceDecision`
with ordered guards (`ABNORMAL_PRICE` → `MARKET_UNAVAILABLE` → optional `TOO_SOON` → `WITHIN_BAND` →
`BELOW_MIN_NOTIONAL` → `INSUFFICIENT_BALANCE` → max-trade clamp → `OK`), each guard a helper ≤30 lines.
See `docs/phases/phase-6.md`. DoD: full decision matrix green (band, BUY/SELL sizing, min-notional,
insufficient balance, abnormal price, clamp, precision rounding); function pure (no mocks).
