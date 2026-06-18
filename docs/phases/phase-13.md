# Phase 13 — Hardening & docs finalize

- **Objective:** Resilience + agent-usable guide.
- **Deliverables:** store retries/timeouts, sanity-check tuning, `README.md`, finalize `docs/DESIGN.md`,
  verify `CLAUDE.md` quick commands; document the full agent workflow (`analyze` → `plan` → `regime` →
  `rebalance` → `performance` → `decisions`) and the stable JSON contract (`schema_version`).
- **Definition of Done:** forced-error tests hit exit codes 3/4/5; README documents the agent
  read/write/audit workflow + stable JSON contract; offline/`--require-fresh` paths documented.
- **Out of scope:** Packaging/distribution (Phase 14).
