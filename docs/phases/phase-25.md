# Phase 25 — Paper account integration + funding + reset

- **Phase ID:** 25
- **Version:** 0.6.0
- **Date:** 2026-07-19
- **Tests:** 589
- **Status:** ✅ DONE (589 tests; live-verified).

## Objective

Wire the paper backend into the account/auth/config plumbing so every live command runs unchanged against a paper account. Add a `paper` flag to Account/AppConfig (real underlying exchange id retained for public data — no fake 'paper' venue), persist it in both auth backends, exempt paper accounts from require_credentials, route _exchange_store/_account_exchange_store to PaperExchangeStore (bridging data_dir), add `auth login --paper --paper-capital` funding and a `paper reset`, plus a runbook + DESIGN update + auth and full plan→rebalance→reconcile e2e tests.

## What was built

I-19 — paper account integration: `Account`/`AppConfig` gain a `paper` flag (persisted, credential-exempt),
`auth login --paper` funds a book, `_exchange_store`/`_account_exchange_store` route to the
`PaperExchangeStore`, and a `paper reset` command re-seeds it — so every live command runs unchanged
against a paper account. See [I-19](../improvements/I-19.md).

## Files changed

| File | Change |
|---|---|
| `models/account.py`, `stores/auth_store.py`, `config.py` | `paper` flag: model, persistence, config + credential exemption, public `account_data_dir` |
| `cli.py` | `auth login --paper`, store routing, `paper reset` command |
| `docs/paper-account.md`, `docs/DESIGN.md` | Runbook + architecture updates |
| `tests/test_cli_paper.py` | Login/seed, simulated status, full rehearsal, reset, non-paper guard |

## Verification

`.venv/Scripts/python -m pytest tests/ -v` (589 passed). **Live-verified** against Binance public prices:
`auth login --paper` → `pair add` → `status`/`plan` → `rebalance --execute` (placed, filled, booked with
a real maker fee) → `orders` → `reconcile` → `performance` → `paper reset`.
