# Phase 7 — Read-only CLI (`status`, `plan`)

- **Objective:** The agent's read path — see state/decisions without executing.
- **Deliverables:** `utils/render.py` (text + JSON; stable key order, enum-string reasons); wire `status` and `plan` in `cli.py`.
- **Definition of Done:** `plan --json` emits the stable contract incl `days_since_last`; idempotent re-run with no drift = all `WITHIN_BAND`, exit 0; `status` shows current vs target + `last_rebalance_at`.
- **Out of scope:** Order placement.
