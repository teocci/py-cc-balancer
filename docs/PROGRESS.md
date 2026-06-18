# PROGRESS

**Current version:** 0.1.0 (unreleased)
**Active phase:** Phase 8 — Market intelligence (OHLCV, indicators, `analyze`)

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

Implement Phase 8: market intelligence (the agent's "eyes"). Add `utils/indicators.py` (pure
`ema`/`rsi`/`macd`/`bollinger`/`atr`/`fib_levels`), `stores/exchange.py` `fetch_ohlcv`,
`stores/market_cache.py` (cached OHLCV under `~/.ccbalancer/ohlcv/`, TTL/offline fallback),
`managers/indicators_manager.py` (multi-timeframe `IndicatorSnapshot`s), the `IndicatorSnapshot`
model, `data_exchange`/`decision_timeframes`/`analysis_timeframes` config, and wire `analyze <pair>
[--timeframe ...]` in `cli.py`. See `docs/phases/phase-8.md`. DoD: each indicator verified against
fixed OHLCV fixtures; cache hit/miss/stale/offline paths tested; `analyze BTC/USDT --timeframe 1h
--json` returns a stable, versioned multi-timeframe snapshot; no network in tests.
