# Phase 3 — Portfolio store + `pair` commands

- **Objective:** User-managed portfolio (pairs/ratios) via CLI, persisted to `portfolio.json`.
- **Deliverables:** `stores/portfolio_store.py` (CRUD + validation: ratio sums to 100, `BASE/QUOTE` symbol, no duplicates); wire `pair list/add/set/remove` in `cli.py`.
- **Definition of Done:** `test_portfolio_store` green (add/set/remove, ratio≠100 → `PortfolioError`, dup rejected); `pair add`/`pair list --json` round-trip.
- **Out of scope:** Pricing / decisions.
