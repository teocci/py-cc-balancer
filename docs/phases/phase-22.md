# Phase 22 — Live order-status reconciliation (F-6)

- **Phase ID:** 22
- **Version:** 0.5.1
- **Date:** 2026-07-19
- **Tests:** 551
- **Status:** ✅ DONE (v0.5.1; 551 tests). Tested end-to-end offline via `cli.main` + fake exchange;
  real-order behavior validated only via the live smoke-test runbook.

## Objective

Fix F-6: live `rebalance --execute` books a fabricated full fill at the limit price on submission,
diverging `ledger.jsonl`/`state.json` from reality. Replace submission-time booking with two-phase
reconciliation — record placements as pending (write-ahead, keyed by client-order-id), and book only
real fills from exchange order status via a new `reconcile` command that also auto-runs at the start
of the next `rebalance`. Handles resting orders, partial fills, and the create-timeout ambiguity. See
the approved design in [`docs/fixes/F-6.md`](../fixes/F-6.md).

## What was built

Two-phase order-status reconciliation, replacing the fabricated submission-time fill (F-6):

- **Write-ahead placement.** `ExecutionManager._place` records each order in a new per-account
  `OrderStore` (`open_orders.json`, keyed by the deterministic client-order-id) *before*
  `create_order`, and books **no** fill on submission. A reject removes the record; a network/timeout
  leaves it `unconfirmed` (result status `unconfirmed`) for later resolution.
- **Reconciliation.** New `ReconciliationManager.reconcile()` reads real status (`ExchangeStore.fetch_order`,
  new; plus `find_order_by_client_id` to resolve unconfirmed placements), books only the *delta* since
  the last reconciled fill (partial-safe, no double-booking), updates state/history/ledger, and drops
  terminal records. Idempotent. `last_rebalance_at` advances on a real fill, not on placement.
- **Auto + on-demand.** `execute()` reconciles first (before cancel-and-replace, so a partial is booked
  before the remainder is cancelled); a new `reconcile [--pair …]` command runs it standalone (write
  category; places no orders; not kill-switch-blocked) — the smoke-test's "verify the fill" command.

Full approved design and limitations in [`docs/fixes/F-6.md`](../fixes/F-6.md).

## Files changed

| File | Change |
|---|---|
| `stores/order_store.py`, `models/open_order.py`, `models/reconcile.py`, `enums/order_status.py` | New — pending-order store + `OpenOrder`/`ReconcileResult`/`OrderStatus`. |
| `managers/reconciliation_manager.py` | New — the reconcile logic. |
| `stores/exchange.py` | `fetch_order` + `find_order_by_client_id`. |
| `managers/execution_manager.py` | Write-ahead `_place`, no fabricated fill, auto-reconcile in `execute`. |
| `utils/render.py`, `cli.py`, `constants.py` | `reconcile` command + render + `OPEN_ORDERS_FILENAME`. |
| `docs/DESIGN.md` | Execution + reconciliation; taxonomy. |
| `tests/` | New store/manager/CLI suites; rewritten execution + exchange suites; fake gains `fetch_order`. |

## Verification

- `.venv/Scripts/python -m pytest tests/ -v` — **551 passed, 4 deselected**.
- End-to-end through `cli.main` against a fake exchange (the regression — a resting order books
  nothing — is asserted directly); real orders validated only via the capped live smoke-test runbook.
- Closes release R1 of this plan → v0.5.1 (fix-only → patch).
