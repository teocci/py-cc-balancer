# ccbalancer

Agent-driven crypto portfolio rebalancer CLI. Keeps a target volatile/stablecoin ratio per pair on a
CEX (via `ccxt`, default Bybit), rebalancing with limit orders when drift exceeds a no-trade band.
Single-user, distributed as a portable one-dir bundle.

## How to Resume Implementation

Work flows through the **`phase-*` skill family** — a **phase** is one context-window-sized
iteration; a **release** bundles one or more phases; a phase bundles one or more items (`I-N`/`F-N`).
Lifecycle:

1. **Plan approved** → `phase-start` scaffolds the phases, items, dependency DAG, and release
   grouping into `docs/PLAN.md` (and stubs + index rows).
2. **Where are we?** → `phase-status` reports the cursor, unblocked/parallelizable phases, and drift.
3. **NEXT** → `phase-flow` re-derives the cursor from `docs/PLAN.md` and picks the next unblocked
   phase (independent phases can run in parallel sessions).
4. **Implement** the phase in `src/ccbalancer/`, tests in `tests/`; run
   `.venv/Scripts/python -m pytest tests/ -v` (all must pass).
5. **Finalize** → `phase-complete` finalizes the phase and, when it closes its release group, cuts
   the release (version bump, CHANGELOG roll, `docs/RELEASE.md` index, commit, tag, push).

Conventions: base in `.claude/skills/phase-flow/references/conventions.md`, project overrides in
`docs/conventions/tracking.md`. Architecture + command taxonomy: `docs/DESIGN.md`.

## Quick Commands

> Per project rule `python-environment`: do NOT `activate` — call the venv binary directly.

```bash
py -3.11 -m venv .venv                                              # once, if missing
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest tests/ -v
.venv/Scripts/python -m pytest tests/ --cov=ccbalancer --cov-report=term-missing
.venv/Scripts/python -m ccbalancer --help
.venv/Scripts/python -m ccbalancer version
.venv/Scripts/python -m ccbalancer pair list --json
.venv/Scripts/python -m ccbalancer plan --json
```

### Packaging (portable bundle)

```bash
.venv/Scripts/python -m pip install -e ".[packaging]"
.venv/Scripts/python -m PyInstaller packaging/ccbalancer.spec   # → dist/ccbalancer/
dist/ccbalancer/ccbalancer version                              # smoke-test
```

Tagging `vX.Y.Z` runs `.github/workflows/release.yml` (build + smoke on Win/Linux/macOS, publish
portable zips to a GitHub Release). The spec collects `ccxt` + `keyring` (incl. backend metadata).

## Layout

- `src/ccbalancer/` — package (`config`, `constants`, `exceptions`, `enums/`, `models/`, `stores/`, `managers/`, `utils/`, `cli`).
- `tests/` — pytest suites (mock the exchange; never hit the network).
- `docs/` — `DESIGN.md`, `PROGRESS.md`, `phases/`, `fixes/`, `improvements/`, `cctx/`, `IMPROVEMENTS.md`, `FIXES.md`, `RELEASE.md`.
- User data at `~/.ccbalancer/` — `config.toml`, `portfolio.json`, `state.json`, append-only `*.jsonl`
  logs, the `ohlcv/` cache, the `STOP` kill-switch. A project-local `ccbalancer.toml` in the CWD takes
  precedence over the base-dir config. Every filename and `CCB_*` env-var name is defined in
  `constants.py` — the single source of truth; don't restate them elsewhere (rule `14-file-locations`).
