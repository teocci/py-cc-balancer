# Phase 21 — Backtest docs + live smoke-test runbook

- **Phase ID:** 21
- **Version:** 0.5.0
- **Date:** 2026-07-18
- **Tests:** 526
- **Status:** ✅ DONE (526 tests; live-verified).

## Objective

Document the backtest honestly. Update DESIGN.md (the backtest engine + the network-only-in-stores
invariant), add a backtest-limitations / how-to-read-results guide (bar-fill assumption, look-ahead,
cycle/overfitting, fees, gaps), and a capped **live smoke-test runbook** covering the residual risk
no backtest removes — auth, real fills, real rejections. References deferred fix F-6. Delivers I-16;
closes release R3.

## What was built

Documentation only — no code. Documents the backtest engine honestly and captures the residual live
risk no backtest removes:

- **`DESIGN.md`** gains a *Backtest engine (offline)* section covering the three stages (fetch →
  replay → report), the dedicated deterministic replay loop, `--fill-timeframe` alignment, and the
  **network-only-in-stores invariant** (ccxt pager + Binance REST fallback both in `stores/`; managers
  and the replay loop never touch the network or the clock). The `simulation` commands are added to
  the command taxonomy.
- **`docs/backtest.md`** — how to read a result (headline ROI vs the per-year split, fills vs orders,
  rejects as a never-converges red flag, determinism) and the honest limitations (bar-fill
  approximation, look-ahead scope, cycle dependence/overfitting, fee realism, gaps + cross-venue
  provenance, strategy-only scope). Frames the backtest as **research, not execution validation**.
- **`docs/live-smoke-test.md`** — a capped live runbook that validates auth, a real fill, and real
  rejection with the smallest possible amount, safety rails armed throughout. It calls out
  reproducing [F-6](../fixes/F-6.md) (fills booked on submission without order-status reconciliation)
  as the specific divergence to watch for.

## Files changed

| File | Change |
|---|---|
| `docs/DESIGN.md` | Backtest engine section + network-only-in-stores invariant + `simulation` in the taxonomy. |
| `docs/backtest.md` | New — how-to-read-results + honest limitations guide. |
| `docs/live-smoke-test.md` | New — capped live smoke-test runbook (refs F-6). |

## Verification

- Docs cross-link cleanly and every runbook command/flag was verified against the live CLI.
- Docs-only — no code changed; suite remains **526 passed, 4 deselected**.
- Closes release R3 (batched with P-20).
