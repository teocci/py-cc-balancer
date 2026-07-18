# PROGRESS

**Current version:** 0.4.0
**Active phase:** `v0.4.0` backtest engine — I-12 (historical data foundation), I-13 (deterministic
replay engine), I-14 (P&L reporting). 506 tests. R3 (P-20 sub-daily + Binance fetcher, P-21 docs)
remains. See `docs/phases/phase-17.md`…`phase-19.md`, `docs/improvements/I-12.md`…`I-14.md`.

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
| 14 | Packaging, portable bundle & release CI | done |
| 15 | Market intelligence II — ADX & Support/Resistance indicators | done |
| 16 | CLI --help discoverability polish | done |
| 17 | Backtest data foundation | done |
| 18 | Backtest replay engine | done |
| 19 | Backtest reporting | done |
| 20 | Sub-daily timeframes + Binance fallback fetcher | planned |
| 21 | Backtest docs + live smoke-test runbook | planned |

> **Redefinition (2026-06-18):** the project was re-scoped from a pure rebalancer into an agent
> decision-support tool (read-only market intelligence + deterministic execution + offline memory).
> Phases 6–7 are unchanged; 8–9 and 11–12 are new; old Execution/Hardening/Packaging moved to 10/13/14.
> Deferred post-v1: MCP server, DEX adapter. See `docs/DESIGN.md` and the approved plan.

## Next action

`v0.4.0` cut (backtest engine — data foundation + replay + reporting; R2 = P-17/P-18/P-19). Plan
continues: R3 is **P-20** (sub-daily 1m/5m + Binance REST fallback fetcher, I-15) and **P-21**
(backtest docs + live smoke-test runbook, I-16) — independent, runnable in parallel. Deferred: the
multi-timeframe MTFA strategy layer (see `docs/trading/`), MCP server, DEX adapter.

> Phase 19 (done): backtest reporting (I-14). New `simulation report <run_id>` marks a completed run to
> its final candle close and reports realized/unrealized/total P&L, ROI (vs starting `--capital`), fees,
> the per-trade timeline, and a **per-year breakdown** — reusing the average-cost
> `PerformanceManager.walk_fills` unchanged (no accounting rebuilt). The per-year split keeps a headline
> ROI from hiding cycle dependence; realized + fees sum back to the totals. Offline/audit-category read;
> P-18's `run.json` gained `final_base`/`final_stable`/`final_close` for marking without a candle re-read.
> Verified live on the real 2022→2026 daily run: total P&L 16498.76 (ROI 164.99%) ties out exactly to
> `final_value − capital`, per-year realized sums to the total (2024 +2291, 2023 +720). 506 tests.
> Closes R2 (v0.4.0 with P-17, P-18). See `docs/phases/phase-19.md`, `docs/improvements/I-14.md`.

> Phase 18 (done): backtest replay engine (I-13). New `simulation run <pair> --start --end --capital`
> replays stored candles deterministically: it decides on each *closed* bar via the unchanged pure
> `RebalanceManager.decide` and resolves the order on the **next** bar that crosses the limit (BUY
> `low<=limit` / SELL `high>=limit`; no look-ahead), else rests and re-quotes (live cancel-and-replace).
> A virtual balance seeded all-stable from `--capital` mutates only on fills; `--fee-rate` (maker,
> default 0.1%) and `--min-cost`/precision enforce market realism (sub-min → `OrderRejectedError`, so
> the "never converges" failure stays visible). Each run writes an isolated ledger + `run.json` under
> `simulation/runs/{run_id}/`; identical inputs → byte-identical ledger. Verified live on the real
> 2022→2026 daily series (1416 bars, 6 fills, +165% ROI, deterministic re-run). 497 tests. Batched into
> R2 (releases with P-17, P-19). See `docs/phases/phase-18.md`, `docs/improvements/I-13.md`.

> Phase 17 (done): backtest data foundation (I-12). New `simulation fetch <pair> --timeframe --start
> --end` downloads historical OHLCV into an append-only, resumable store under
> `~/.ccbalancer/simulation/` — `ExchangeStore.fetch_ohlcv_range` paginates ccxt and drops the
> still-forming candle; `SimulationStore` appends only the missing tail since the last closed candle
> (prior rows byte-identical) and writes a per-symbol `manifest.json` (coverage/gaps) mirroring the
> shipped `data/simulation/` sample; a CSV/JSONL loader ingests that sample so backtests run offline.
> Verified live against public Binance: a clean rebuild reproduced the sample byte-for-byte
> (1h 33983 / 4h 8496 / 1d 1416 rows). 481 tests. Batched into R2 (releases with P-18, P-19). See
> `docs/phases/phase-17.md`, `docs/improvements/I-12.md`.

> Phase 16 (done): CLI `--help` discoverability polish (I-11). The root `description` now states the
> two-layer "CLI computes deterministic facts, never judges; agent/human decides" model; the
> `_COMMAND_TAXONOMY` epilog gained the previously-missing `auth` command and split live reads from
> local reads and state writes from credential writes; `analyze --help` enumerates the valid
> timeframes + default set and points to `indicator list` (dynamically, so new indicators need no
> help edit); `regime` "Flag"→"Report" and explicit `pair add`/`set` help; a stale registry
> docstring (`ccbalancer indicators`→`indicator list`) fixed. No behavior change; full suite green.
> See `docs/phases/phase-16.md`.

> Phase 15 (done): market intelligence II — two registry indicators computed per timeframe and
> surfaced in `analyze` (I-9, I-10). ADX adds Wilder trend strength with +DI/-DI and a threshold,
> plus a deterministic `adx_trend` (trending/ranging) label mirroring `rsi_zone`; support/resistance
> (`sr`) detects fractal swing pivots, clusters them within a percent tolerance, and splits by the
> latest close into nearest-first, capped `supports[]`/`resistances[]`. Both plug into the existing
> introspectable registry (auto-flowing into `indicator list`/`set`) — no new architecture. The
> `analyze` JSON contract grew, so `SCHEMA_VERSION` bumped to 2. 445 tests; `indicators.py` 96%
> covered. See `docs/phases/phase-15.md`, `docs/improvements/I-9.md`, `I-10.md`.

> Phase 14 (done): packaging, portable bundle & release CI. `packaging/ccbalancer.spec` builds a
> PyInstaller one-dir bundle (`dist/ccbalancer/`, launcher + `_internal/`) shipping its own Python —
> entry is `ccbalancer/__main__.py`, paths anchored to `SPECPATH` so `pyinstaller packaging/ccbalancer.spec`
> from the repo root works. `collect_all('ccxt')` pulls the per-exchange data + lazy submodules;
> `collect_all('keyring')` + `copy_metadata('keyring')` + pinned per-OS backends
> (`Windows`/`macOS`/`SecretService`/`chainer`/`fail`) resolve the keyring-via-entry-points caveat so the
> credential store still works frozen (file fallback regardless); `pytest`/`PyInstaller` excluded from the
> bundle. `.github/workflows/release.yml` builds on Win/Linux/macOS (`bash` shell unified), reads
> `ccbalancer.__version__`, smoke-tests `version`/`--help`/`pair --help`/`analyze --help`, zips via
> `shutil.make_archive`, and on `v*` tags publishes the three portable zips with
> `softprops/action-gh-release@v2` (`contents: write`). README gained portable-bundle/build-locally/
> CI-on-tag install docs; CLAUDE.md gained a Packaging quick-commands block. Verified: local build +
> bundle smoke (incl. `auth list` keyring path) green; full suite passes. See `docs/phases/phase-14.md`.

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
