# Phase 8 — Execution (`rebalance`, `orders`, `cancel`)

- **Objective:** Place/cancel limit orders + persist state/history.
- **Deliverables:** `managers/execution_manager.py` (cancel-stale by `CCB_PREFIX`, limit pricing from bid/ask + offset, place tagged orders, write `state.json` + append `history.jsonl`); wire `rebalance`/`orders`/`cancel` in `cli.py`.
- **Definition of Done:** `rebalance --dry-run` writes nothing; testnet `rebalance` places/cancels exactly the planned orders and updates state + history; re-run idempotent; exit codes correct.
- **Out of scope:** Retry/backoff hardening (Phase 9).
