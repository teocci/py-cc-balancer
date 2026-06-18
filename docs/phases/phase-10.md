# Phase 10 — Packaging, portable bundle & release CI

- **Objective:** Distributable single-user tool + automated cross-OS GitHub Releases.
- **Deliverables:** `packaging/ccbalancer.spec` (PyInstaller one-dir; `collect_all('ccxt')`); `.github/workflows/release.yml` (build Win/Linux/macOS, read `ccbalancer.__version__`, smoke `version`/`--help`/`pair --help`, zip per OS, publish on `v*` tag); portable-bundle install docs (download → extract → run) in README/CLAUDE.md.
- **Definition of Done:** `pyinstaller packaging/ccbalancer.spec` builds `dist/ccbalancer/`; bundle smoke passes locally; pushing a `vX.Y.Z` tag produces a GitHub Release with portable Windows/Linux/macOS zips.
- **Out of scope (future work):** PyPI/pipx publish, Homebrew/winget, code signing, sub-accounts, more exchanges, market orders, multi-machine state sync.
