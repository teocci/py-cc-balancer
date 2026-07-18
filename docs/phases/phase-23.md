# Phase 23 — External-target backtest — simulation run --targets

- **Phase ID:** 23
- **Version:** 0.6.0
- **Date:** 2026-07-19
- **Tests:** 589
- **Status:** ✅ DONE (589 tests; live-verified).

## Objective

Let `simulation run` replay a per-decision target schedule (a forward-filled step function) instead of the pair's static target, so an external brain can backtest a moving volatile/stable ratio while the CLI keeps applying its own band / min-cost / fee mechanics at each bar. Purely additive; the pure RebalanceManager.decide is reused unchanged.

## What was built

I-17 — `simulation run --targets schedule.jsonl`: a forward-filled target schedule replayed per
decision bar, the pure `RebalanceManager.decide` reused unchanged (a per-bar `PairConfig` is derived),
with the schedule folded into the run's determinism digest and `run.json`. See [I-17](../improvements/I-17.md).

## Files changed

| File | Change |
|---|---|
| `stores/target_schedule.py` | New schedule loader/validation/lookup/digest |
| `managers/simulation_run_manager.py` | Thread the schedule through `replay`/`run`/`_run_id`/`_write_run` |
| `cli.py` | `--targets` flag + handler (start-coverage warning) |
| `docs/backtest.md`, `tests/*` | Workflow docs; loader, replay, and CLI e2e tests |

## Verification

`.venv/Scripts/python -m pytest tests/ -v` (all green). A scheduled run yields a distinct `run_id` and
a different fill count than the static run; an invalid schedule exits with a config error.
