# Phase 20 — Sub-daily timeframes + Binance fallback fetcher

- **Phase ID:** 20
- **Version:** 0.5.0
- **Date:** 2026-07-18
- **Tests:** 526
- **Status:** ✅ DONE (526 tests; live-verified).

## Objective

Extend the backtest to sub-daily timeframes (1m/5m/15m). Build the Binance REST klines fallback
fetcher (`stores/history_fetch.py`, adapted from the prototype, constants centralized) for deep 1m/5m
backfill where ccxt pagination is impractical, and wire multi-timeframe alignment (decision timeframe
vs finer fill-resolution timeframe). Network stays in the stores layer. Delivers I-15.

## What was built

- **`stores/history_fetch.py` (`BinanceHistoryFetch`)** — a paginated public Binance
  `/api/v3/klines` fetcher for deep 1m/5m backfill where ccxt pagination is impractical. Requests
  1000 rows/call, advances the cursor past each page's last open (no re-download), drops the
  still-forming candle, and normalizes to ccxt's `[t,o,h,l,c,v]`. The HTTP call is an injected seam,
  so 429/418 backoff, the HTTP-451 → `data.binance.vision` archive note, and pagination are tested
  offline. Its `fetch_ohlcv_range` mirrors `ExchangeStore` so the manager routes either source
  uniformly. Along with `ExchangeStore` it is the only module that touches the network.
- **Per-timeframe fetch routing** — `SimulationManager` gains an optional `history_fetch` and
  `_source_for(timeframe)`: 1m/5m (`SIM_LTF_TIMEFRAMES`) → Binance REST fallback, every other
  timeframe → the ccxt pager. Falls back to ccxt when no fetcher is injected.
- **Multi-timeframe fill alignment** — `replay()` takes an optional finer `fill_candles` series; a
  resting order decided at a decision bar's close now resolves against the finer bars *within the
  next decision interval* (first crossing bar fills, at its own timestamp) via a bisect-indexed
  window. The load-bearing invariants hold: no look-ahead (never the decision bar's own interval) and
  determinism. With no finer series the original next-decision-bar behavior is byte-identical.
- **`simulation run --fill-timeframe`** threads the finer timeframe through `SimulationRunManager.run`
  (guarded read, `run_id` + run-meta include it) into the engine; `SimRunResult.fill_timeframe` and
  the render surface expose it.
- **`SIM_DEFAULT_TIMEFRAMES` now leads with `15m`** so the coarsest execution timeframe is fetched by
  default (it paginates comfortably via ccxt; only 1m/5m need the REST fallback).

## Files changed

| File | Change |
|---|---|
| `src/ccbalancer/stores/history_fetch.py` | New — `BinanceHistoryFetch` paginated REST klines fetcher (injected HTTP seam, backoff, 451 archive note). |
| `src/ccbalancer/constants.py` | `SIM_LTF_TIMEFRAMES`, `BINANCE_KLINES_*`, `BINANCE_ARCHIVE_URL`; `SIM_DEFAULT_TIMEFRAMES` leads with `15m`. |
| `src/ccbalancer/managers/simulation_manager.py` | `history_fetch` field + `_source_for` per-timeframe routing. |
| `src/ccbalancer/managers/simulation_run_manager.py` | `replay(fill_candles)` + `_FineIndex`/`_resolve` alignment; `run(fill_timeframe)`; run-id/meta. |
| `src/ccbalancer/models/sim_run.py` | `SimRunResult.fill_timeframe`. |
| `src/ccbalancer/utils/render.py` | Emit `fill_timeframe`; annotate the run line `fill@<tf>`. |
| `src/ccbalancer/cli.py` | `simulation run --fill-timeframe`; inject `BinanceHistoryFetch`; fetch default help. |
| `tests/test_history_fetch.py` | New — fetcher pagination/normalization/trim/routing/backoff/451/errors. |
| `tests/test_simulation_manager.py` | Per-timeframe routing. |
| `tests/test_simulation_replay.py` | Aligned-fill invariants. |
| `tests/test_simulation_run_manager.py` | `fill_timeframe` run wiring. |
| `tests/test_cli_simulation*.py` | `--fill-timeframe` passthrough; new default set. |

## Verification

- `.venv/Scripts/python -m pytest tests/ -v` — **526 passed, 4 deselected** (network-marked `live`).
- `simulation run --help` shows `--fill-timeframe`; `simulation fetch --help` shows the
  `15m, 1h, 4h, 1d` default. Changed modules byte-compile clean.
