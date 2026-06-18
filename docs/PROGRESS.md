# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 9 — Decision memory + audit category

## Phase status

| Phase | Title | Status |
|---|---|---|
| 0 | Environment, scaffold & docs | done |
| 1 | Domain primitives | done |
| 2 | Configuration (settings + secrets) | done |
| 3 | Portfolio store + `pair` commands | done |
| 4 | Exchange store (ccxt wrapper) | done |
| 5 | State store + portfolio snapshots | done |
| 6 | Rebalance decision logic | done |
| 7 | Read-only CLI (`status`, `plan`) | done |
| 8 | Market intelligence (OHLCV, indicators, `analyze`) | done |
| 9 | Decision memory + audit category | pending |
| 10 | Execution + safety guardrails + Binance | pending |
| 11 | Performance & cost-basis (`performance`) | pending |
| 12 | Regime signal + agent flags/milestones | pending |
| 13 | Hardening & docs finalize | pending |
| 14 | Packaging, portable bundle & release CI | pending |

> **Redefinition (2026-06-18):** the project was re-scoped from a pure rebalancer into an agent
> decision-support tool (read-only market intelligence + deterministic execution + offline memory).
> Phases 6–7 are unchanged; 8–9 and 11–12 are new; old Execution/Hardening/Packaging moved to 10/13/14.
> Deferred post-v1: MCP server, DEX adapter. See `docs/DESIGN.md` and the approved plan.

## Next action

Implement Phase 9: decision memory + audit category. Add `stores/decision_store.py` (append-only
`~/.ccbalancer/decision_log.jsonl`; one record per `decide()` call with inputs + drift + each guard
pass/fail + proposed/executed order), hook `plan`/`decide()` to append a decision record, and wire
the **audit** command group in `cli.py` (`decisions`, `history`, `export` — local logs only, no
network, no side effects) with `--help` grouped by read/write/audit. See `docs/phases/phase-9.md`.
DoD: every `decide()` appends exactly one record; `decisions`/`history` read it back; records are
append-only and jq-queryable; JSON carries `schema_version`; audit commands make zero network calls.
