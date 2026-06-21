# Phase 0 — Environment, scaffold & docs

- **Objective:** Installable empty package on the right interpreter, plus the orchestration scaffold.
- **Deliverables:** Ensure `.venv/` (else `py -3.11 -m venv .venv`); use `.venv/Scripts/python` (never system Python). `pyproject.toml`, `src/ccbalancer/` dirs + `__init__`s, `__main__.py`, `utils/logging.py` (stderr), `__version__`, `version` command. Docs set: `CLAUDE.md`, `CHANGELOG.md`, `docs/{DESIGN,PROGRESS,IMPROVEMENTS,FIXES,RELEASE}.md`, `docs/phases/phase-0..10.md`.
- **Definition of Done:** `.venv/Scripts/python -m pip install -e ".[dev]"` ok; `... -m ccbalancer --help` and `... version` work; `docs/PROGRESS.md` shows P0 done, P1 pending.
- **Out of scope:** Any business logic or network call.
