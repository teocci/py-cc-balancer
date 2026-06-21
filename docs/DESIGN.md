# DESIGN

Durable architecture for `ccbalancer`. (Full rationale + rubric in the approved plan.)

## Purpose

`ccbalancer` is a CLI consumed primarily by **AI agents** (but equally by humans or a web backend —
interface-agnostic) that provides **read-only market intelligence**, executes the brain's **write**
decisions deterministically, and keeps an **offline memory** of performance, decisions, and
agent-defined milestones. The base strategy: keep a target volatile/stablecoin ratio per pair
(e.g. `BTC/USDT` 80/20), rebalancing with limit orders only when allocation drift exceeds a no-trade
band (avoids churn/fees). The agent owns cadence; the CLI has no internal timer.

## Mental model: CLI computes, agent judges

- **Layer 1 — the CLI: deterministic, not intelligent.** Arithmetic + fixed rules; same inputs → same
  output (auditable, testable, no LLM). It computes facts and *proposes/executes*; it never judges
  whether a trade or a strategy change is wise.
- **Layer 2 — the brain: AI agent / human / web backend**, outside the CLI. Reads the facts and makes
  the judgment calls (whether/when to trade, whether to change a target ratio, what milestones matter).

## Three distinct signals (keep separate)

1. **Allocation drift** — current allocation vs the **target ratio** → triggers a rebalance trade to
   restore the ratio (the `decide()` core).
2. **Performance / P&L** — current value vs **invested capital**, via **true cost-basis** (entry price,
   every fill price, fees) → realized P&L per rebalance + unrealized P&L now → is the strategy working?
3. **Regime / price-variance-since-target-set** — price now vs price when the target ratio was chosen →
   raises a **flag + heuristic-suggested ratio(s) + what-if scenarios** so the brain can decide whether
   to change the target ratio (de-risk after a big run). The CLI never auto-changes the ratio.

Plus **agent-defined flags/milestones**: persistent watch-conditions the agent/user registers; the CLI
evaluates them deterministically and reports hits (Layer-2 defines, Layer-1 computes).

## Market intelligence (read-only)

- **Self-calculate** indicators from exchange OHLCV — no TradingView (no sanctioned API). `ccxt`'s
  `fetch_ohlcv` returns `[time,o,h,l,c,v]` in one uniform shape across Bybit/Binance/OKX; public OHLCV
  is free, no API key. The indicator math never knows which exchange supplied candles → **exchange-
  agnostic**; a `data_exchange` config key picks the source (may differ from the trading exchange).
- **v1 indicators** (a code **registry**, not a hardcoded set): RSI, MACD(12/26/9), EMA 12/26/200,
  Bollinger Bands, ATR, Volume MA, Fibonacci retracement levels. Adding an indicator = a pure
  function + a registry entry. The registry is **introspectable** — `indicator list` serializes each
  indicator's parameters (name, type, default, current value, description) so an agent can discover
  the configuration surface, and `indicator set` writes registry-validated overrides.
- **Indicator settings vs registry vs storage** (three separate things): the *registry* (which
  indicators exist + their math) is code; *parameters/thresholds* (RSI period + overbought/oversold,
  EMA periods, Volume MA window, …) live in their own `indicators.toml` (kept out of `config.toml`),
  resolved over the registry defaults. RSI thresholds yield a deterministic `rsi_zone` fact in the
  snapshot — the CLI computes the comparison; the agent still judges. Scaling path to many indicators:
  `[[indicators]]` instance arrays + an agent-managed file, adopted when count actually grows.
- **Multi-timeframe:** `decision_timeframes = ['1m','5m','15m']` (cadence) and
  `analysis_timeframes = ['1h','4h','1d','1w']` (strategy). Indicators compute per requested timeframe;
  Fibonacci picks its swing high/low from a per-timeframe lookback.

## Key decisions

- **Exchange:** `ccxt`, default **Bybit** (Binance + OKX switchable; OKX needs a passphrase, handled
  generically via `requiredCredentials`). Trade-only API keys. Testnet supported.
- **Account:** single active account; multiple named **auth profiles** (`gh`-style), one active at a
  time, overridable with `--profile <slug>`. A profile owns its exchange + testnet + credentials.
  Per-pair logical partitioning within an account (no sub-accounts).
- **Credentials:** managed by `auth login`; secrets default to the OS **keyring** (metadata-only
  `auth.json`), with a best-effort `0600` plaintext file fallback (`--no-keyring`/`CCB_AUTH_BACKEND`).
  Legacy `CCB_API_KEY`/`CCB_API_SECRET` env vars remain a no-profile fallback for CI.
- **Orders:** limit, with cancel-and-replace ownership via `clientOrderId` prefix (`CCB_PREFIX`).
- **Scheduling:** agent-driven; no internal timer.
- **Three concerns:** settings (`config.toml`) vs portfolio (`portfolio.json`, CLI-managed) vs state (`state.json` + `history.jsonl`).

## File layout (`src/ccbalancer/`)

| Module | Owns |
|---|---|
| `config.py` | `AppConfig`; discovery (`--config`→`CCB_CONFIG`→`./ccbalancer.toml`→`~/.ccbalancer/config.toml`); creds via active/`--profile` profile then env; precedence flag→profile→env→TOML→default |
| `stores/auth_store.py` | `auth.json` profiles + active pointer; slug validation; file/keyring secret backends |
| `constants.py` | Default band/floors, timeouts, exit codes, env keys, `CCB_PREFIX`, file names |
| `exceptions.py` | `AppError` → `ConfigError`, `ExchangeError`, `InsufficientBalanceError`, `SanityCheckError`, `OrderRejectedError`, `PortfolioError`, `StateError` |
| `enums/` | `OrderSide`, `SkipReason`, `OutputFormat` |
| `models/` | `PairConfig`, `AssetBalance`, `PairSnapshot`, `ProposedOrder`, `RebalanceDecision`, `RebalanceState`, `HistoryEvent`, `ExecutionResult` (frozen+slots) |
| `stores/exchange.py` | ONLY network code: thin ccxt wrapper (sandbox toggle, timeout); bounded retries of transient failures on idempotent calls (reads + cancel; placement never auto-retries); + `fetch_ohlcv` |
| `stores/portfolio_store.py` | read/write `portfolio.json` (pair CRUD + validation); + entry/target-set baselines |
| `stores/state_store.py` | read/write `state.json`; append `history.jsonl` |
| `stores/market_cache.py` | cached OHLCV under `~/.ccbalancer/ohlcv/`; TTL/staleness, offline fallback |
| `stores/ledger_store.py` | append-only `ledger.jsonl` of fills (price, qty, fee, side) — cost-basis source |
| `stores/decision_store.py` | append-only `decision_log.jsonl`; one record per `decide()` |
| `stores/flags_store.py` | `flags.json` — agent/user milestones & watch-conditions |
| `managers/portfolio_manager.py` | balances + tickers + state → `PairSnapshot` |
| `managers/rebalance_manager.py` | pure `decide(pair, snapshot) -> RebalanceDecision` (guards) |
| `managers/indicators_manager.py` | OHLCV (via cache) → multi-timeframe `IndicatorSnapshot`s |
| `managers/performance_manager.py` | ledger + tickers → realized/unrealized/ROI per pair |
| `managers/regime_manager.py` | price-variance-since-target-set → flag + heuristic ratio(s) + scenarios |
| `managers/flags_manager.py` | evaluate milestones against current snapshots, report hits |
| `managers/execution_manager.py` | cancel stale, place limit orders, persist state + history + fills |
| `utils/` | `logging` (stderr), `money` (Decimal/precision), `render` (text+JSON), `timeutil` (UTC), `indicators` (pure RSI/MACD/EMA/Bollinger/ATR/Fib) |

Managers receive stores via constructor injection; managers never import ccxt directly.
New models (frozen+slots): `IndicatorSnapshot`, `PerformanceSnapshot`, `RegimeSignal`, `Fill`, `Milestone`.

## Files & locations (`~/.ccbalancer/`)

| File | Kind | Edited by |
|---|---|---|
| `config.toml` | settings (exchange, testnet, sanity %, limit offset, timeouts, defaults) | human |
| `indicators.toml` | indicator parameter overrides (registry-validated; own concern, not in `config.toml`) | human + `indicator set` |
| `auth.json` | auth profiles (metadata + active pointer; secrets inline only on the file backend) | CLI `auth` commands (600) |
| `.env` | legacy/fallback secrets (`CCB_API_KEY`, `CCB_API_SECRET`) | human (never committed, 600) |
| `portfolio.json` | pairs + per-pair target/band/notionals + entry & target-set baselines | CLI `pair` commands |
| `state.json` | last rebalance event per pair | tool (on `rebalance`) |
| `history.jsonl` | append-only event log | tool (on `rebalance`) |
| `ledger.jsonl` | append-only fills (price, qty, fee) — cost-basis source | tool (on `rebalance`) |
| `decision_log.jsonl` | append-only `decide()` rationale (inputs + guards + order) | tool (on `plan`/`rebalance`) |
| `ohlcv/{symbol}/{timeframe}.jsonl` | cached candles for indicators | tool (on `analyze`) |
| `flags.json` | agent/user milestones & watch-conditions | CLI `flag` commands |

## Decision logic (pure)

`drift_pct = (base_qty*price - total*target_volatile%) / total * 100`. `>0` → SELL base; `<0` → BUY.
Ordered guards, first failure wins: `ABNORMAL_PRICE` → `MARKET_UNAVAILABLE` → `TOO_SOON` (optional) →
`WITHIN_BAND` → `BELOW_MIN_NOTIONAL` → `INSUFFICIENT_BALANCE` → max-trade clamp → `OK`.

## Execution (cancel-and-replace)

`load_markets` → cancel open `CCB_PREFIX` orders → snapshot → `decide` → place limit (BUY at bid / SELL
at ask ± `limit_offset_pct`) tagged with `CCB_PREFIX` → persist `state.json` + append `history.jsonl`.
Idempotent: re-run cancels its own leftovers and re-places.

## Command taxonomy (three categories)

- **read** (live data, no side effects): `status` · `plan` · `analyze <pair> [--timeframe ...]` ·
  `indicator list` · `performance [--pair]` · `regime [--pair]` · `orders` · `version`
- **write** (mutate state / place orders; dry-run by default, guarded): `rebalance` · `cancel` ·
  `pair (list/add/set/remove)` · `indicator set` · `flag (add/list/remove)` · `config (show/init)` ·
  `auth (login/logout/list/use/status/whoami)`
- **audit** (local logs only, no network, no side effects): `decisions` · `history` ·
  `performance --history` · `export`

Global flags: `--json`, `--dry-run`, `--pair`, `--profile`, `--exchange`, `--testnet/--no-testnet`, `--config`.

JSON → stdout (stable key order, enum-string reasons, every response carries `schema_version`); logs →
stderr. Exit codes: `0` ok/no-op, `2` config/portfolio/auth/state/flag, `3` exchange/network, `4` order
rejected, `5` partial failure, `6` safety blocked.

## Interface & scope decisions

- **Interface:** CLI + stable JSON now; **MCP server later** (thin transport over the same
  managers/stores). No importable-library coupling (would break a Go/Rust web backend).
- **Exchange scope:** CEX-first (Bybit + Binance via ccxt); **DEX later via a separate adapter** — DEX
  breaks core assumptions (hot wallet key vs trade-only API key = far larger blast radius, no
  `clientOrderId` cancel-replace, gas/slippage/MEV), so it is post-v1 with its own security review.
- **Safety guardrails** (prerequisite for autonomous write): `rebalance` dry-run by default, per-run
  notional cap (`max_session_notional_usd`), confirm-token issued by `plan`, kill-switch file, key
  scoping (trade-only).
