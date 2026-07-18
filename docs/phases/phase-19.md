# Phase 19 — Backtest reporting

- **Phase ID:** 19
- **Version:** 0.4.0
- **Date:** 2026-07-18
- **Tests:** 506
- **Status:** ✅ DONE (506 tests; live-verified).

## Objective

Turn a completed run's sim ledger into a performance report by reusing the existing
`PerformanceManager` (cost-basis P&L, realized/unrealized, ROI, per-trade timeline), marked to market
at the final candle's close, plus a per-year (or per-regime) breakdown that blunts the
cycle/overfitting false-confidence trap. Emit JSON + text. Delivers I-14; closes release R2.

## What was built

- **`build_report(meta, fills)`** (`managers/simulation_report_manager.py`) — a pure, offline P&L report
  over a run's sim ledger. It reuses the average-cost `PerformanceManager.walk_fills` unchanged (no
  accounting rebuilt) and **marks the residual position to the run's final candle close** (recorded in
  `run.json`) in place of a live ticker. Emits realized / unrealized / total P&L, ROI (vs the starting
  `--capital`), fees, the per-trade timeline, and a **per-year breakdown** — bucketing the trade timeline
  by calendar year so a single headline ROI can't hide cycle dependence (a 2017→now window is
  BTC-bull-dominated). By construction the per-year realized + fees sum back to the totals.
- **`SimulationReportManager`** — loads `simulation/runs/{run_id}/` (`run.json` + `ledger.jsonl`) and
  builds the report; raises `StateError` for an unknown run.
- **`simulation report <run_id>`** command — offline audit-category read (`--json`/`--fields`), local
  envelope. Added to the `--help` taxonomy under audit.
- **P-18 `run.json` extended** with `final_base` / `final_stable` / `final_close` so the report marks to
  market without re-reading candles (a small forward-looking addition to the still-unreleased writer).

## Files changed

| File | Change |
|---|---|
| `src/ccbalancer/managers/simulation_report_manager.py` | **new** — `build_report` + `SimulationReportManager` (reuses `walk_fills`; per-year breakdown) |
| `src/ccbalancer/managers/simulation_run_manager.py` | `run.json` now records `final_base`/`final_stable`/`final_close` for offline marking |
| `src/ccbalancer/utils/render.py` | + `simulation_report_response` / `simulation_report_lines` |
| `src/ccbalancer/cli.py` | + `simulation report` subcommand, dispatch, `_simulation_report_manager` seam, taxonomy; `_add_simulation_command` refactored to pass `base`/`venue` (report is local-only) |
| `tests/test_simulation_report_manager.py`, `tests/test_cli_simulation_report.py` | **new** test suites |

## Verification

- `.venv/Scripts/python -m pytest tests/ -v` → **506 passed** (4 live deselected).
- A hand-checked toy ledger pins realized 19.58 / unrealized 59.70 / ROI 7.928%; the per-year realized
  and fees sum back to the totals.
- **Live report** on the real 2022→2026 daily run: realized 3010.97 + unrealized 13487.79 = total
  16498.76 → **ROI 164.99%**; `total_pnl == final_value − capital` and the per-year realized sums to the
  total, both exact. The breakdown surfaces the cycle dependence (2024 +2291, 2023 +720 realized).
