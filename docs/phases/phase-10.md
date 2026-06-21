# Phase 10 — Execution + safety guardrails + Binance

- **Objective:** Place/cancel limit orders safely across CEXs + persist state/history/fills.
- **Deliverables:**
  - `managers/execution_manager.py` — cancel-stale by `CCB_PREFIX`, limit pricing from bid/ask +
    offset, place tagged orders, write `state.json` + append `history.jsonl`; append fills to
    `stores/ledger_store.py` (`ledger.jsonl`: price, qty, fee, side, ts).
  - **Safety guardrails (DoD-blocking):** `rebalance` dry-run by default; per-run notional cap
    (`max_session_notional_usd` in a `SafetyConfig`); confirm-token issued by `plan` and required by
    `rebalance`; kill-switch file; trade-only key scoping.
  - Enable **Binance** alongside Bybit; per-exchange quirks test matrix (precision, min-notional,
    `clientOrderId` param, cancel semantics).
  - Wire `rebalance`/`orders`/`cancel` in `cli.py`.
- **Definition of Done:** `rebalance --dry-run` writes nothing and is the default; execution refuses
  without explicit flag/confirm-token; session cap + kill-switch block as designed; testnet `rebalance`
  places/cancels exactly the planned orders and updates state + history + ledger; re-run idempotent;
  Binance and Bybit both pass the quirks matrix; exit codes correct.
- **Out of scope:** Retry/backoff hardening (Phase 13); DEX (post-v1).
