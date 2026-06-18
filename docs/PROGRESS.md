# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 7 — Read-only CLI (`status`, `plan`)

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
| 7 | Read-only CLI (`status`, `plan`) | pending |
| 8 | Market intelligence (OHLCV, indicators, `analyze`) | pending |
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

Implement Phase 7: the agent's read path. Add `utils/render.py` (text + JSON; stable key order,
enum-string reasons) and wire `status` + `plan` in `cli.py` over the existing managers
(`PortfolioManager.snapshots` → `RebalanceManager.decide`). See `docs/phases/phase-7.md`. DoD:
`plan --json` emits the stable contract incl `days_since_last`; a no-drift re-run is all
`WITHIN_BAND` with exit 0; `status` shows current vs target + `last_rebalance_at`.
