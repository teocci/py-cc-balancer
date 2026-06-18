# Phase 5 — State store + portfolio snapshots

- **Objective:** Persist/read rebalance state + history; assemble per-pair snapshots.
- **Deliverables:** `stores/state_store.py` (`state.json` last event per pair + append `history.jsonl`); `utils/timeutil.py` (UTC ISO-8601); `utils/money.py` (Decimal/precision); `managers/portfolio_manager.py` (balances + tickers + state → `PairSnapshot`).
- **Definition of Done:** `test_state_store` + `test_portfolio_manager` green; snapshot math + `last_rebalance_at` wiring verified; state round-trips.
- **Out of scope:** Deciding / placing orders.
