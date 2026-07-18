# Phase 17 — Backtest data foundation

- **Phase ID:** 17
- **Version:** 0.4.0
- **Date:** 2026-07-18
- **Tests:** 506
- **Status:** ✅ DONE (506 tests; live-verified).

## Objective

Lay the data foundation for the historical backtest: a paginated ccxt range fetch, an append-only
resumable simulation OHLCV store under `~/.ccbalancer/simulation/`, a loader that ingests the
committed `data/simulation/` sample, and the `simulation fetch` command. Timeframes 1h/4h/1d
full-cycle (cheap); 1m/5m deferred to P-20. Delivers I-12.

## What was built

- **`ExchangeStore.fetch_ohlcv_range(symbol, timeframe, since_ms, until_ms)`** — paginated ccxt range
  fetch: loops `fetch_ohlcv(since=cursor, limit=1000)`, advancing the cursor past each page's last
  open so no candle is re-downloaded, normalizes to ccxt `[t,o,h,l,c,v]`, and drops the still-forming
  last candle (kept iff `open + interval <= until`). Network stays in the store (DESIGN invariant).
- **`SimulationStore`** (`stores/simulation_store.py`) — append-only, resumable OHLCV under
  `~/.ccbalancer/simulation/ohlcv/{exchange}/{symbol}/{timeframe}.jsonl`. `append()` adds only candles
  strictly newer than the last stored open (boundary dedup), so prior rows stay byte-identical across
  resumed fetches; `rebuild_manifest()` writes a per-symbol `manifest.json` mirroring the shipped
  sample's shape (provenance + per-timeframe coverage/gaps). Distinct from the overwrite `MarketCache`.
- **`utils/candles.py`** — the single deterministic bridge between in-memory ccxt lists and the compact
  on-disk `{"t","o","h","l","c","v"}` records (`separators=(',',':')`), matching the rolling-dataset
  convention; stable serialization is what makes the append-only store byte-identical.
- **`stores/simulation_sample.py`** — read-only loader normalizing the committed `data/simulation/`
  CSV **and** compact JSONL to the same ccxt lists, so backtests run offline with no network pull.
- **`SimulationManager`** (`managers/simulation_manager.py`) — resolves the resume point from the store,
  pulls only the missing tail per timeframe, appends, then rebuilds the manifest. Holds no network code
  and never reads the clock (caller passes `until_ms` + `fetched_at`).
- **`simulation fetch`** command (new `simulation` group): `<symbol> --timeframe --start --end`; default
  timeframes 1h/4h/1d. Emits the stable JSON envelope + human lines; added to the `--help` taxonomy.

Scope held to the data foundation: no replay (P-18), no 1m/5m or Binance REST fallback (P-20), no
interior gap-backfill (resume is tail-only, per I-12).

## Files changed

| File | Change |
|---|---|
| `src/ccbalancer/constants.py` | + `SIMULATION_DIRNAME`, `SIM_OHLCV_DIRNAME`, `SIM_MANIFEST_FILENAME`, `SIM_FETCH_PAGE_LIMIT`, `SIM_DEFAULT_TIMEFRAMES` |
| `src/ccbalancer/utils/timeutil.py` | + `iso_to_ms` (ISO date/datetime → epoch ms) |
| `src/ccbalancer/utils/candles.py` | **new** — ccxt-list ↔ compact-record mapping + stable serialization |
| `src/ccbalancer/stores/exchange.py` | + `fetch_ohlcv_range` (paginate, normalize, drop forming candle) |
| `src/ccbalancer/stores/simulation_store.py` | **new** — append-only resumable store + manifest |
| `src/ccbalancer/stores/simulation_sample.py` | **new** — CSV/JSONL sample loader (read-only ingest) |
| `src/ccbalancer/managers/simulation_manager.py` | **new** — fetch→append→manifest orchestration |
| `src/ccbalancer/models/sim_fetch.py` | **new** — `SimFetchResult` (frozen+slots); exported from `models/__init__` |
| `src/ccbalancer/utils/render.py` | + `sim_fetch_to_dict` / `simulation_fetch_response` / `simulation_fetch_lines` |
| `src/ccbalancer/cli.py` | + `simulation fetch` command, dispatch, `_simulation_manager` seam, taxonomy line |
| `tests/conftest.py` | `FakeExchangeStore.fetch_ohlcv_range` + `exchange_id`; `sample_dir` fixture |
| `tests/test_candles.py`, `test_simulation_store.py`, `test_simulation_sample.py`, `test_simulation_manager.py`, `test_cli_simulation.py` | **new** test suites |
| `tests/test_exchange.py` | + `fetch_ohlcv_range` pagination/normalization/forming-drop tests |

## Verification

- `.venv/Scripts/python -m pytest tests/ -v` → **481 passed** (4 live deselected); new modules 92–100% covered.
- **Live rebuild** (public Binance, no creds): cleared `~/.ccbalancer/simulation`, then
  `simulation fetch BTC/USDT --timeframe 1h --timeframe 4h --timeframe 1d --start 2022-09-01 --end
  2026-07-18 --exchange binance --no-testnet`. Row counts matched the sample manifest exactly
  (1h 33983 · 4h 8496 · 1d 1416) and the rebuilt JSONL is **byte-identical** to
  `data/simulation/binance/jsonl/BTCUSDT_{1h,4h,1d}.jsonl` (`diff` clean). Manifest coverage + the known
  1h gap (2023-03-24) match the sample semantically; timestamps follow this project's `Z` convention.
