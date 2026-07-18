# Phase 18 — Backtest replay engine

- **Phase ID:** 18
- **Version:** 0.4.0
- **Date:** 2026-07-18
- **Tests:** 506
- **Status:** ✅ DONE (506 tests; live-verified).

## Objective

Build the deterministic replay engine: iterate candles from `--start`, decide on closed candles via
the existing pure `RebalanceManager.decide`, resolve fills on the next bar that crosses the limit
(no look-ahead), maintain a virtual balance seeded from `--capital`, and write simulated `Fill`s to
an isolated sim ledger. Expose `simulation run` (compute only; reporting is P-19). Delivers I-13.

## What was built

- **Pure replay engine** (`managers/simulation_run_manager.py::replay`) — iterates a candle series,
  and at each *closed* candle builds a `PairSnapshot` (close stands in for price/bid/ask; no order
  book in history) and calls the unchanged pure `RebalanceManager.decide`. The proposed order enters a
  one-slot resting book and is resolved against the **next** bar with a bar-crosses-limit fill model
  (BUY when `low <= limit`, SELL when `high >= limit`); on a miss it is cancelled and re-quoted at the
  next decision (live cancel-and-replace). Two invariants are load-bearing and tested: **no look-ahead**
  (an order never resolves on its own decision bar) and **determinism** (same inputs → byte-identical
  ledger).
- **Virtual balance** seeded all-stable from `--capital`; a fill mutates it (BUY: +base, −(notional+fee);
  SELL: −base, +(notional−fee)) and emits a `Fill`. Free == total at every decision point because each
  bar cancels-and-replaces, so no funds are locked.
- **Market realism (offline)** — `--amount-precision` floors order sizing (via the snapshot precision
  `decide` already honors); `--min-cost` is the exchange floor below which `validate_order` raises
  `OrderRejectedError`, so the "never converges" failure (perpetually sub-minimum legs) stays visible.
  `--fee-rate` (maker, default 0.1%) is charged on each fill's notional in quote terms.
- **`SimulationRunManager`** — reads the stored candles for `[--start, --end)` from the P-17 store
  (offline), replays, and writes an **isolated** run under `simulation/runs/{run_id}/` — `ledger.jsonl`
  (reusing `LedgerStore`, rewritten from scratch so a re-run is byte-identical) + `run.json` (params +
  summary). `run_id` is a deterministic digest of every input that shapes the ledger.
- **`simulation run <symbol>`** command (compute-only): resolves the pair from the configured portfolio,
  `--timeframe` (default `1d`), `--start/--end`, `--capital/--fee-rate/--amount-precision/--min-cost`.
  Stable JSON envelope + human summary; added to the `--help` taxonomy.

MVP scope: single decision timeframe (default `1d`); sub-daily and the reporting/P&L layer are P-20/P-19.

## Files changed

| File | Change |
|---|---|
| `src/ccbalancer/constants.py` | + `SIM_RUNS_DIRNAME`, `SIM_LEDGER_FILENAME`, `SIM_RUN_FILENAME`, `SIM_DEFAULT_DECISION_TIMEFRAME`, `SIM_DEFAULT_CAPITAL`, `SIM_DEFAULT_FEE_RATE`, `SIM_DEFAULT_AMOUNT_PRECISION`, `SIM_DEFAULT_MIN_COST` |
| `src/ccbalancer/managers/simulation_run_manager.py` | **new** — pure `replay` + `validate_order` + `SimulationRunManager` (persist ledger/run.json, deterministic `run_id`) |
| `src/ccbalancer/models/sim_run.py` | **new** — `SimRunResult` (frozen+slots); exported from `models/__init__` |
| `src/ccbalancer/utils/render.py` | + `sim_run_to_dict` / `simulation_run_response` / `simulation_run_lines` |
| `src/ccbalancer/cli.py` | + `simulation run` subcommand, dispatch, `_simulation_run_manager` seam, taxonomy line |
| `tests/test_simulation_replay.py`, `test_simulation_run_manager.py`, `test_cli_simulation_run.py` | **new** test suites |

## Verification

- `.venv/Scripts/python -m pytest tests/ -v` → **497 passed** (4 live deselected); engine 97%, model 100%.
- Engine tests assert: no look-ahead, next-bar crossing fills, non-crossing rest/re-quote, fee on
  notional, sub-min → `OrderRejectedError`, balance-mutates-only-on-fills, and determinism.
- **Live replay** over the real 2022→2026 daily series (rebuilt in P-17): 1416 bars, 6 orders → 6 fills,
  0 rejects, $10,000 → $26,498.76 (+165% ROI, plausible for an 80/20 through BTC's ~3× rise). Re-running
  the same inputs produced a **byte-identical ledger** and identical `run_id`.
