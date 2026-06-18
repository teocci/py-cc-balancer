# DESIGN

Durable architecture for `ccbalancer`. (Full rationale + rubric in the approved plan.)

## Purpose

Keep a target volatile/stablecoin ratio per pair (e.g. `BTC/USDT` 80/20). An AI agent owns cadence and
invokes the CLI; the tool answers "what's the plan?" and executes limit orders when told. Rebalance
only when drift exceeds a no-trade band (avoids churn/fees).

## Key decisions

- **Exchange:** `ccxt`, default **Bybit** (Binance switchable). Trade-only API keys. Testnet supported.
- **Account:** single account, per-pair logical partitioning (no sub-accounts).
- **Orders:** limit, with cancel-and-replace ownership via `clientOrderId` prefix (`CCB_PREFIX`).
- **Scheduling:** agent-driven; no internal timer.
- **Three concerns:** settings (`config.toml`) vs portfolio (`portfolio.json`, CLI-managed) vs state (`state.json` + `history.jsonl`).

## File layout (`src/ccbalancer/`)

| Module | Owns |
|---|---|
| `config.py` | `AppConfig`; discovery (`--config`→`CCB_CONFIG`→`./ccbalancer.toml`→`~/.ccbalancer/config.toml`); env→TOML→default; secrets env-only |
| `constants.py` | Default band/floors, timeouts, exit codes, env keys, `CCB_PREFIX`, file names |
| `exceptions.py` | `AppError` → `ConfigError`, `ExchangeError`, `InsufficientBalanceError`, `SanityCheckError`, `OrderRejectedError`, `PortfolioError`, `StateError` |
| `enums/` | `OrderSide`, `SkipReason`, `OutputFormat` |
| `models/` | `PairConfig`, `AssetBalance`, `PairSnapshot`, `ProposedOrder`, `RebalanceDecision`, `RebalanceState`, `HistoryEvent`, `ExecutionResult` (frozen+slots) |
| `stores/exchange.py` | ONLY network code: thin ccxt wrapper (sandbox toggle) |
| `stores/portfolio_store.py` | read/write `portfolio.json` (pair CRUD + validation) |
| `stores/state_store.py` | read/write `state.json`; append `history.jsonl` |
| `managers/portfolio_manager.py` | balances + tickers + state → `PairSnapshot` |
| `managers/rebalance_manager.py` | pure `decide(pair, snapshot) -> RebalanceDecision` (guards) |
| `managers/execution_manager.py` | cancel stale, place limit orders, persist state + history |
| `utils/` | `logging` (stderr), `money` (Decimal/precision), `render` (text+JSON), `timeutil` (UTC) |

Managers receive stores via constructor injection; managers never import ccxt directly.

## Files & locations (`~/.ccbalancer/`)

| File | Kind | Edited by |
|---|---|---|
| `config.toml` | settings (exchange, testnet, sanity %, limit offset, timeouts, defaults) | human |
| `.env` | secrets (`CCB_API_KEY`, `CCB_API_SECRET`) | human (never committed, 600) |
| `portfolio.json` | pairs + per-pair target/band/notionals | CLI `pair` commands |
| `state.json` | last rebalance event per pair | tool (on `rebalance`) |
| `history.jsonl` | append-only event log | tool (on `rebalance`) |

## Decision logic (pure)

`drift_pct = (base_qty*price - total*target_volatile%) / total * 100`. `>0` → SELL base; `<0` → BUY.
Ordered guards, first failure wins: `ABNORMAL_PRICE` → `MARKET_UNAVAILABLE` → `TOO_SOON` (optional) →
`WITHIN_BAND` → `BELOW_MIN_NOTIONAL` → `INSUFFICIENT_BALANCE` → max-trade clamp → `OK`.

## Execution (cancel-and-replace)

`load_markets` → cancel open `CCB_PREFIX` orders → snapshot → `decide` → place limit (BUY at bid / SELL
at ask ± `limit_offset_pct`) tagged with `CCB_PREFIX` → persist `state.json` + append `history.jsonl`.
Idempotent: re-run cancels its own leftovers and re-places.

## Command taxonomy

`status` · `plan` · `rebalance` · `orders` · `cancel` · `pair (list/add/set/remove)` ·
`config (show/init)` · `version`. Global flags: `--json`, `--dry-run`, `--pair`, `--exchange`,
`--testnet/--no-testnet`, `--config`.

JSON → stdout (stable key order, enum-string reasons); logs → stderr. Exit codes: `0` ok/no-op,
`2` config/portfolio, `3` exchange/network, `4` order rejected, `5` partial failure.
