# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 10 — Execution + safety guardrails + Binance

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
| 9 | Decision memory + audit category | done |
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

Implement Phase 10: execution + safety guardrails + Binance. Add `managers/execution_manager.py`
(cancel stale `CCB_PREFIX` orders, price limits from bid/ask + offset, place tagged orders, persist
`state.json` + append `history.jsonl`) and `stores/ledger_store.py` (`ledger.jsonl` fills). Add the
DoD-blocking safety guardrails (`rebalance` dry-run by default, per-run `max_session_notional_usd`
cap, confirm-token issued by `plan` and required by `rebalance`, kill-switch file, trade-only key
scoping), enable Binance alongside Bybit with a per-exchange quirks matrix, and wire
`rebalance`/`orders`/`cancel` in `cli.py`. See `docs/phases/phase-10.md`. DoD: `rebalance --dry-run`
writes nothing and is the default; execution refuses without explicit flag/confirm-token; session cap
+ kill-switch block; testnet `rebalance` places/cancels exactly the planned orders and updates state +
history + ledger; re-run idempotent; both exchanges pass the quirks matrix; exit codes correct.

> Phase 9 (done): `stores/decision_store.py` append-only `decision_log.jsonl` (one jq-queryable record
> per decision: inputs + drift + guard ladder + order, `schema_version`); `plan` appends per pair while
> `status` does not write; `StateStore.load_history()`; audit commands `decisions`/`history`/`export`
> (local logs only, zero network); `--help` grouped read/write/audit. `GUARD_ORDER` in
> `rebalance_manager` is the single source of truth the log ladder mirrors.
