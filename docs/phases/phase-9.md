# Phase 9 — Decision memory + audit category

- **Objective:** Persist *why* the tool decided, queryable offline; formalize the three-category
  taxonomy (read / write / audit).
- **Deliverables:**
  - `stores/decision_store.py` — append-only `~/.ccbalancer/decision_log.jsonl`; one record per
    `decide()` call: inputs + drift + each guard pass/fail + proposed/executed order.
  - Wire the **audit** command group in `cli.py`: `decisions`, `history`, `export` (local logs only —
    no network, no side effects); group `--help` by read/write/audit.
  - Hook `plan`/`decide()` to append a decision record.
- **Definition of Done:** every `decide()` appends exactly one decision record; `decisions`/`history`
  read it back; records are append-only and jq-queryable; JSON carries `schema_version`; audit commands
  make zero network calls.
- **Out of scope:** Order placement (Phase 10); P&L attribution (Phase 11).
