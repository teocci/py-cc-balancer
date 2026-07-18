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
  Bollinger Bands, ATR, ADX (+DI/-DI, threshold), support/resistance levels (`sr`), Volume MA,
  Fibonacci retracement levels. Adding an indicator = a pure function + a registry entry. The
  registry is **introspectable** — `indicator list` serializes each indicator's parameters (name,
  type, default, current value, description) so an agent can discover the configuration surface, and
  `indicator set` writes registry-validated overrides. ADX yields a deterministic `adx_trend` fact
  (trending/ranging vs threshold); `sr` emits per-timeframe `supports[]`/`resistances[]` from
  clustered swing pivots — both computed by the CLI, judged by the agent.
- **Indicator settings vs registry vs storage** (three separate things): the *registry* (which
  indicators exist + their math) is code; *parameters/thresholds* (RSI period + overbought/oversold,
  EMA periods, Volume MA window, …) live in their own `indicators.toml` (kept out of `config.toml`),
  resolved over the registry defaults. RSI thresholds yield a deterministic `rsi_zone` fact in the
  snapshot — the CLI computes the comparison; the agent still judges. Scaling path to many indicators:
  `[[indicators]]` instance arrays + an agent-managed file, adopted when count actually grows.
- **Multi-timeframe:** `decision_timeframes = ['1m','5m','15m']` (cadence) and
  `analysis_timeframes = ['1h','4h','1d','1w']` (strategy). Indicators compute per requested timeframe;
  Fibonacci picks its swing high/low from a per-timeframe lookback. The per-timeframe **roles**
  (1W/1D macro & bias, 4H/1H intermediate, 15Min/5Min execution) and the multi-timeframe alignment
  strategy are documented in [`trading/timeframes.md`](trading/timeframes.md) (+
  `trading/timeframe_strategy_map.json`) as the reference for a future MTFA strategy layer — the
  indicators above are the deterministic inputs it would consume.

## Key decisions

- **Exchange:** `ccxt`, default **Bybit** (Binance + OKX switchable; OKX needs a passphrase, handled
  generically via `requiredCredentials`). Trade-only API keys. Testnet supported.
- **Account:** multiple named **auth accounts** (`gh`-style), one active at a time, overridable
  with `--account <slug>` (`CCB_ACCOUNT`; legacy `CCB_PROFILE` still honored). An account owns its
  exchange + testnet + credentials, plus its own isolated book (see per-account data dirs, I-8). A
  **paper account** (`auth login --paper`, name via `--account`; I-18/I-19) is the same shape with a `paper` flag and
  no credentials: it keeps a real exchange id for **public** market data but simulates balances/orders
  in a per-account book, so every live command runs against it unchanged (a live-execution rehearsal,
  not a backtest — see [`paper-account.md`](paper-account.md)).
- **Credentials:** managed by `auth login`; secrets default to the OS **keyring** (metadata-only
  `auth.json`), with a best-effort `0600` plaintext file fallback (`--no-keyring`/`CCB_AUTH_BACKEND`).
  Legacy `CCB_API_KEY`/`CCB_API_SECRET` env vars remain a no-account fallback for CI.
- **Orders:** limit, with cancel-and-replace ownership via `clientOrderId` prefix (`CCB_PREFIX`).
- **Scheduling:** agent-driven; no internal timer.
- **Three concerns:** settings (`config.toml`) vs portfolio (`portfolio.json`, CLI-managed) vs state (`state.json` + `history.jsonl`).

## File layout (`src/ccbalancer/`)

| Module | Owns |
|---|---|
| `config.py` | `AppConfig`; discovery (`--config`→`CCB_CONFIG`→`./ccbalancer.toml`→`~/.ccbalancer/config.toml`); creds via active/`--account` then env; precedence flag→account→env→TOML→default |
| `stores/auth_store.py` | `auth.json` accounts + active pointer; slug validation; file/keyring secret backends |
| `constants.py` | Default band/floors, timeouts, exit codes, env keys, `CCB_PREFIX`, file names |
| `exceptions.py` | `AppError` → `ConfigError`, `ExchangeError`, `InsufficientBalanceError`, `SanityCheckError`, `OrderRejectedError`, `PortfolioError`, `StateError` |
| `enums/` | `OrderSide`, `SkipReason`, `OutputFormat` |
| `models/` | `PairConfig`, `AssetBalance`, `PairSnapshot`, `ProposedOrder`, `RebalanceDecision`, `RebalanceState`, `HistoryEvent`, `ExecutionResult` (frozen+slots) |
| `stores/exchange.py` | ONLY network code: thin ccxt wrapper (sandbox toggle, timeout); bounded retries of transient failures on idempotent calls (reads + cancel; placement never auto-retries); + `fetch_ohlcv` |
| `stores/paper_exchange.py` | drop-in `ExchangeStore` for a paper account: real public prices (via a wrapped `ExchangeStore`) + a simulated book; reconcile-driven fills (a resting limit fills once the live ticker crosses it) |
| `stores/paper_book.py` | persistent `paper_book.json` — a paper account's simulated balances + orders + id counter (atomic write, no network) |
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

**Global / shared** (app-dir root):

| File | Kind | Edited by |
|---|---|---|
| `config.toml` | settings (exchange, testnet, sanity %, limit offset, timeouts, defaults) | human |
| `indicators.toml` | indicator parameter overrides (registry-validated; own concern, not in `config.toml`) | human + `indicator set` |
| `auth.json` | auth accounts (metadata + active pointer + per-account stable `id`/`account_ref`; secrets inline only on the file backend) | CLI `auth` commands (600) |
| `.env` | legacy/fallback secrets (`CCB_API_KEY`, `CCB_API_SECRET`) | human (never committed, 600) |
| `ohlcv/{symbol}/{timeframe}.jsonl` | cached candles for indicators (keyed by public `data_exchange`) | tool (on `analyze`) |
| `STOP` | kill-switch (presence blocks order placement) | human |

**Per-account book** — under `accounts/<account-id>/` (the active account's `id`, or `default` for the no-account env path; F-5 / I-8 isolate these so switching accounts across venues never mixes state):

| File | Kind | Edited by |
|---|---|---|
| `portfolio.json` | pairs + per-pair target/band/notionals + entry & target-set baselines | CLI `pair` commands |
| `state.json` | last rebalance event per pair | tool (on `rebalance`) |
| `history.jsonl` | append-only event log | tool (on `rebalance`) |
| `ledger.jsonl` | append-only fills (price, qty, fee) — cost-basis source | tool (on `rebalance`) |
| `decision_log.jsonl` | append-only `decide()` rationale (inputs + guards + order) | tool (on `plan`/`rebalance`) |
| `flags.json` | agent/user milestones & watch-conditions | CLI `flag` commands |

The `id` is minted once at first save and is stable across `auth rename` and credential
rotation, so an account's book is never stranded. A best-effort `account_ref` (hashed exchange
account id, captured online at login) guards rotation: a renewed key resolving to a *different*
exchange account is refused (`--force` overrides). A one-time migration moves any pre-0.2.0
root-level book files into the active account's directory.

## Decision logic (pure)

`drift_pct = (base_qty*price - total*target_volatile%) / total * 100`. `>0` → SELL base; `<0` → BUY.
Ordered guards, first failure wins: `ABNORMAL_PRICE` → `MARKET_UNAVAILABLE` → `TOO_SOON` (optional) →
`WITHIN_BAND` → `BELOW_MIN_NOTIONAL` → `INSUFFICIENT_BALANCE` → max-trade clamp → `OK`.

## Execution (cancel-and-replace) + reconciliation

`load_markets` → **reconcile outstanding orders** → cancel open `CCB_PREFIX` orders → snapshot →
`decide` → place limit (BUY at bid / SELL at ask ± `limit_offset_pct`) tagged with `CCB_PREFIX`.
Idempotent: re-run reconciles, cancels its own leftovers, and re-places.

**Fills are booked from real order status, never on submission** (F-6). A maker limit order usually
*rests* (`open`, `filled:0`), so booking it as a full fill at the limit price the moment it is placed
fabricates a trade and diverges the local books. Instead placement is recorded *write-ahead* in
`stores/order_store.py` (`open_orders.json`, keyed by the deterministic client-order-id, so a
`create_order` timeout is never lost), and `managers/reconciliation_manager.py` books only the *delta*
of what actually filled — reading `fetch_order`, handling partial fills without double-booking, and
resolving an unconfirmed placement by its client-order-id. Reconciliation runs at the start of each
`rebalance` (before cancel-and-replace, so a partial is booked before the remainder is cancelled) and
on demand via the `reconcile` command. `last_rebalance_at` advances on a real fill, not on placement.

## Backtest engine (offline)

A three-stage backtest simulator (`simulation` command) for **strategy research**, not execution
validation — read [`backtest.md`](backtest.md) for how to read results and the honest limitations.

- **Data foundation** (`simulation fetch`, I-12/I-15): downloads historical OHLCV into an append-only,
  resumable store under `~/.ccbalancer/simulation/{exchange}/{symbol}/{timeframe}.jsonl` + a
  coverage/gap `manifest.json`. A range is never re-downloaded — only the missing tail since the last
  closed candle is appended, so prior rows stay byte-identical across resumed fetches. Per-timeframe
  source routing: **1m/5m → a Binance public REST klines fallback** (`stores/history_fetch.py`, deep
  backfill where ccxt pagination is impractical); every other timeframe (15m/1h/4h/1d) → the ccxt
  pager (`ExchangeStore.fetch_ohlcv_range`). Both drop the still-forming candle and normalize to
  `[t,o,h,l,c,v]`.
- **Replay** (`simulation run`, I-13/I-15): a dedicated deterministic replay loop decides on each
  *closed* candle via the **unchanged pure `RebalanceManager.decide`** and resolves the resulting
  limit order on the **next** bar that crosses it (BUY when a later low ≤ limit, SELL when a later
  high ≥ limit) — never the decision bar (**no look-ahead**). With `--fill-timeframe` a finer series
  resolves fills *within* each decision interval (first crossing finer bar, at its own timestamp).
  Fills mutate a virtual balance and land in an isolated per-run ledger keyed by a hash of all
  inputs; identical inputs → a byte-identical ledger (**determinism**).
- **Report** (`simulation report`, I-14): marks a completed run to its final candle close and emits
  realized/unrealized/total P&L, ROI, fees, the per-trade timeline, and a **per-year breakdown** (so
  a headline ROI can't hide cycle dependence). Reuses the average-cost `PerformanceManager` unchanged.

**Network-only-in-stores invariant:** all network access — the ccxt pager *and* the Binance REST
fallback — lives in the `stores/` layer (`exchange.py`, `history_fetch.py`); managers and the replay
loop never touch the network or the clock. The replay engine consumes only offline candles, which is
what makes it deterministic and testable without hitting an exchange.

## Command taxonomy (three categories)

- **read** (live data, no side effects): `status` · `plan` · `analyze <pair> [--timeframe ...]` ·
  `indicator list` · `performance [--pair]` · `regime [--pair]` · `orders` · `version`
- **write** (mutate state / place orders / fetch data; dry-run by default where it places orders,
  guarded): `rebalance` · `cancel` · `reconcile` (book real fills; places no orders) ·
  `pair (list/add/set/remove)` · `indicator set` · `flag (add/list/remove)` · `config (show/init)` ·
  `auth (login/logout/list/use/status/whoami)` · `paper reset` (re-seed a paper book) ·
  `simulation fetch` (network → data store) ·
  `simulation run` (local backtest, compute only; `--targets` replays a moving target schedule)
- **audit** (local logs only, no network, no side effects): `decisions` · `history` ·
  `performance --history` · `export` · `simulation report`

Flags are command-scoped (composable parents): universal `--json`, `--fields`, `--config`;
credential/venue commands add `--account`, `--exchange`, `--testnet/--no-testnet`; pair-filtering
commands add `--pair`. Each command's `--help` lists only the flags its handler reads.

JSON → stdout (stable key order, enum-string reasons, every response carries `schema_version`); logs →
stderr. Exit codes: `0` ok/no-op, `2` config/portfolio/auth/state/flag, `3` exchange/network, `4` order
rejected, `5` partial failure, `6` safety blocked.

## Interface & scope decisions

- **Interface:** CLI + stable JSON now; **MCP server later** (thin transport over the same
  managers/stores). No importable-library coupling (would break a Go/Rust web backend).
- **Exchange scope:** CEX-first (Bybit + Binance + OKX via ccxt; OKX needs a passphrase, handled
  generically via `requiredCredentials`); **DEX later via a separate adapter** — DEX
  breaks core assumptions (hot wallet key vs trade-only API key = far larger blast radius, no
  `clientOrderId` cancel-replace, gas/slippage/MEV), so it is post-v1 with its own security review.
- **Safety guardrails** (prerequisite for autonomous write): `rebalance` dry-run by default, per-run
  notional cap (`max_session_notional_usd`), confirm-token issued by `plan`, kill-switch file, key
  scoping (trade-only).
