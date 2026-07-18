# Phase 16 — CLI --help discoverability polish

- **Phase ID:** 16
- **Version:** 0.3.0
- **Date:** 2026-07-18
- **Tests:** 445
- **Status:** ✅ DONE (445 tests; live-verified).

## Objective

Make the tool's purpose and market-intelligence surface discoverable from `--help` (I-11): expand
the root description with the two-layer "CLI computes, agent judges" model, complete the epilog
command taxonomy (add `auth`, split read/write sub-commands), and document `analyze`'s valid
timeframes while pointing to `indicator list` dynamically so future indicators need no help edits.

## What was built

**I-11 — `--help` discoverability.** Surgical edits to the argparse help so the tool's purpose and
market-intelligence surface are discoverable without reading `DESIGN.md`:

- Root `description` now states the two-layer "CLI computes deterministic facts, never judges;
  agent/human decides" model.
- The `_COMMAND_TAXONOMY` epilog gained the previously-absent `auth` command and split live reads
  from local reads and state writes from credential writes.
- `analyze` help enumerates the valid timeframes and default set and points to `indicator list` for
  the computed-indicator catalog — referenced dynamically, so the new `adx`/`sr` indicators needed
  no help edit.
- Minor: `regime` verb "Flag"→"Report" (disambiguated from the `flag` command); explicit `pair
  add`/`set` help; fixed a stale registry docstring.

## Files changed

| File | Change |
|---|---|
| `src/ccbalancer/cli.py` | Root description, epilog taxonomy, `analyze`/`regime`/`pair` help. |
| `src/ccbalancer/utils/indicator_registry.py` | Stale docstring `ccbalancer indicators` → `indicator list`. |

## Verification

- `ccbalancer --help` / `ccbalancer analyze --help` render the new model, taxonomy, and timeframe docs.
- `.venv/Scripts/python -m pytest tests/ -v` — 445 passed (no help assertions regressed).
