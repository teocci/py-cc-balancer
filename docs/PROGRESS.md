# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 14 — Packaging, portable bundle & release CI

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
| 10 | Execution + safety guardrails + Binance | done |
| 11 | Performance & cost-basis (`performance`) | done |
| Auth | Multi-profile credentials (`gh`-style) + OKX | done |
| 12 | Regime signal + agent flags/milestones | done |
| 13 | Hardening & docs finalize | done |
| 14 | Packaging, portable bundle & release CI | pending |

> **Redefinition (2026-06-18):** the project was re-scoped from a pure rebalancer into an agent
> decision-support tool (read-only market intelligence + deterministic execution + offline memory).
> Phases 6–7 are unchanged; 8–9 and 11–12 are new; old Execution/Hardening/Packaging moved to 10/13/14.
> Deferred post-v1: MCP server, DEX adapter. See `docs/DESIGN.md` and the approved plan.

## Next action

Implement Phase 14: packaging, portable bundle & release CI.

> Phase 13 (done): hardening & docs finalize. `ExchangeStore._request` (replacing the `_translate`
> context manager) retries transient ccxt failures (`NetworkError`/`RequestTimeout`/`DDoSProtection`/
> `ExchangeNotAvailable`) on idempotent calls (reads + `cancel_order`) with exponential backoff, then
> raises `ExchangeError` (exit 3) once the budget is spent; `create_order` is exempt (`retries=0`) since a
> timed-out placement may have landed — re-run the idempotent cancel-and-replace instead. New `[global]`
> keys `http_retries` (default 2) + `retry_backoff_ms` (default 500), threaded through `AppConfig`/
> `config show`/templates. The `quote_sanity_pct` → `abnormal_price` guard (existing) is verified and
> documented. New `README.md` documents the agent read/write/audit workflow (`analyze`→`plan`→`regime`→
> `rebalance`→`performance`→`decisions`), the stable JSON contract (`schema_version`), the exit-code
> table (0/2/3/4/5/6), safety guardrails, retry/timeout hardening, and offline/`--require-fresh` cache
> paths. New `tests/test_cli_errors.py` drives `cli.main` to exit codes 3/4/5. `docs/DESIGN.md` finalized
> (exit code 6 + retry note); `CLAUDE.md` quick commands verified. See `docs/phases/phase-13.md`.

> Phase 12 (done): regime signal (DESIGN.md #3) + agent flags/milestones — Layer-2 defines, Layer-1
> computes. `managers/regime_manager.py` compares price now vs `target_set_price` and, once the move
> exceeds `target_review_band_pct` (default 20%, new `[global]` key), raises a flag + a deterministic
> suggested ratio + what-if scenarios (value/risk under each candidate). Suggestion and scenarios share
> one mechanism — a fixed volatile-share ladder (`REGIME_SCENARIO_VOLATILE_PCTS` 80/50/25 with the
> pair's current target always injected as a rung); a run-up steps one rung toward less risk, a drop
> toward more, within-band holds. Pure; never auto-changes the ratio. `models/RegimeSignal` +
> `RegimeScenario` (frozen+slots). New read command `regime [--pair]`. `stores/flags_store.py` over
> `flags.json` + `managers/flags_manager.py` + `models/Milestone` register and evaluate watch-conditions
> (`<symbol> <metric> <op> <threshold>` over `price`/`drift_pct`/`volatile_pct`/`value`; word-form ops
> `ge|le|gt|lt|eq`) against live snapshots, reporting hit/miss/unknown. New write commands
> `flag add|list|remove` (`add`/`remove` local; `list` live, fetching only configured milestone pairs).
> New `FlagError` (exit 2). See `docs/phases/phase-12.md`.

> Auth (done, inserted before packaging): `gh`-style multi-profile credentials. New `auth` group
> (`login/logout/list/use/status/whoami`) + global `--profile <slug>`; `stores/auth_store.py`
> (`AuthStore` over `auth.json`, slug-validated profile names, file + OS-keyring secret backends,
> `backend_for` honoring the recorded backend). `config.load_config` resolves creds from the
> active/selected profile (precedence flag→profile→env→TOML→default); a profile owns its
> exchange/testnet/key/secret/passphrase, legacy `CCB_API_KEY`/`CCB_API_SECRET` retained for CI.
> OKX added to `SUPPORTED_EXCHANGES` (passphrase via `requiredCredentials`, quirks row). `keyring`
> default with best-effort `0600` file fallback. Secrets always masked in output. See
> `docs/phases/phase-auth.md`. Packaging caveat: keyring + PyInstaller for Phase 14.

> Phase 11 (done): `managers/performance_manager.py` walks the append-only `ledger.jsonl` with the
> average-cost method (Decimal math) and marks the held position to market via live tickers, computing
> realized P&L per sell, unrealized P&L of the open position, fees (normalized to quote terms;
> base-denominated fees valued at fill price), and ROI — per pair and across the portfolio
> (`portfolio_totals`). `models/PerformanceSnapshot` (frozen+slots) carries the per-pair P&L.
> Empty-ledger pairs fall back to the `entry_price`/`invested_capital` baseline so unrealized stays
> meaningful. `performance [--pair]` (read, live) and `performance --history` (audit, ledger-only,
> zero network) wired in `cli.py`; stable `schema_version` envelope. ROI exact to the cent.

> Phase 10 (done): `managers/execution_manager.py` runs cancel-and-replace (cancel own stale
> `CCB_PREFIX` orders → place one tagged limit order per actionable decision → persist `state.json` +
> append `history.jsonl` + `ledger.jsonl` + a `rebalance` decision-log record); idempotent re-runs.
> `stores/ledger_store.py` + `Fill` model own the cost-basis ledger. Safety guardrails: `rebalance`
> dry-run by default, intent-level confirm-token (issued by `plan`, required by `--execute --confirm`),
> `[safety].max_session_notional_usd` cap (default 1000, 0 = unlimited), `STOP` kill-switch (exempts
> `cancel`), trade-only creds; `SafetyConfig`/`SafetyError`/`SAFETY_BLOCKED` (exit 6). Binance enabled
> via `stores/exchange_quirks.py` (tested matrix). New CLI: `rebalance`/`orders`/`cancel`.

> Phase 9 (done): `stores/decision_store.py` append-only `decision_log.jsonl` (one jq-queryable record
> per decision: inputs + drift + guard ladder + order, `schema_version`); `plan` appends per pair while
> `status` does not write; `StateStore.load_history()`; audit commands `decisions`/`history`/`export`
> (local logs only, zero network); `--help` grouped read/write/audit. `GUARD_ORDER` in
> `rebalance_manager` is the single source of truth the log ladder mirrors.
