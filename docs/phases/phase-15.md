# Phase 15 — Market intelligence II — ADX & Support/Resistance indicators

- **Phase ID:** 15
- **Version:** 0.3.0
- **Date:** 2026-07-18
- **Tests:** 445
- **Status:** ✅ DONE (445 tests; live-verified).

## Objective

Extend the Phase 8 indicator engine with two deterministic reads the agent lacked: **ADX**
(Wilder trend strength + directional +DI/-DI + threshold, I-9) and a **support/resistance** level
detector emitting `supports[]`/`resistances[]` per timeframe (I-10). Both plug into the existing
introspectable registry and surface through `analyze` — no new architecture, no strategy layer.

## What was built

Two new registry indicators computed per timeframe and surfaced in `analyze`:

- **I-9 — ADX:** Wilder ADX with +DI/-DI and a trend-strength threshold; a deterministic
  `adx_trend` (trending/ranging) label mirrors the existing `rsi_zone` pattern.
- **I-10 — Support/Resistance:** a fractal swing-pivot detector, clustered within a percent
  tolerance and split by the latest close into `supports[]`/`resistances[]` (nearest first, capped).

Both plug into the existing introspectable registry (auto-flowing into `indicator list`/`set`) with
no new architecture. The `analyze` JSON contract grew (`adx{}`, `supports[]`, `resistances[]`), so
`SCHEMA_VERSION` bumped to 2.

## Files changed

| File | Change |
|---|---|
| `src/ccbalancer/utils/indicators.py` | Pure `adx()` and `support_resistance()` + helpers. |
| `src/ccbalancer/constants.py` | ADX + S/R defaults, ADX trend labels, `SCHEMA_VERSION` → 2. |
| `src/ccbalancer/utils/indicator_registry.py` | `adx` and `sr` specs. |
| `src/ccbalancer/models/indicators.py` | Snapshot ADX + S/R fields. |
| `src/ccbalancer/managers/indicators_manager.py` | Compute both; `_adx_trend()` label. |
| `src/ccbalancer/utils/render.py` | `analyze` JSON + text for ADX and levels. |
| `tests/…` | ADX/SR math, manager, registry, model, and analyze-contract tests. |

## Verification

- `.venv/Scripts/python -m pytest tests/ -v` — 445 passed, 4 deselected.
- Coverage: `indicators.py` 96%, `models/indicators.py` 100%, `indicator_registry.py` 97%.
- `ccbalancer indicator list --json` lists `adx` and `sr` with their default parameters.
