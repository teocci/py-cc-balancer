# ccbalancer

Agent-driven crypto portfolio rebalancer CLI. Keeps a target volatile/stablecoin ratio per pair on a
CEX (via `ccxt`, default Bybit), rebalancing with limit orders when drift exceeds a no-trade band.
Single-user, distributed as a portable one-dir bundle.

## How to Resume Implementation

1. Read `docs/PROGRESS.md` — current version, phase status, and what comes next.
2. Read `docs/DESIGN.md` — architecture decisions and command taxonomy.
3. Open `docs/phases/phase-<N>.md` for the next pending phase's exact scope.
4. Say **NEXT** to implement the next pending phase.

Each phase follows this pattern:
- Implement in `src/ccbalancer/` per the file layout in `docs/DESIGN.md`.
- Write tests in `tests/`.
- Run `.venv/Scripts/python -m pytest tests/ -v` — all must pass.
- Run the `phase-complete` skill to finalize (version bump, CHANGELOG, commit).

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

## Layout

- `src/ccbalancer/` — package (`config`, `constants`, `exceptions`, `enums/`, `models/`, `stores/`, `managers/`, `utils/`, `cli`).
- `tests/` — pytest suites (mock the exchange; never hit the network).
- `docs/` — `DESIGN.md`, `PROGRESS.md`, `phases/`, `IMPROVEMENTS.md`, `FIXES.md`, `RELEASE.md`.
- User data at `~/.ccbalancer/`: `config.toml`, `.env`, `portfolio.json`, `state.json`, `history.jsonl`.
