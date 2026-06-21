# ccbalancer

Agent-driven crypto portfolio rebalancer CLI. It keeps a target **volatile/stablecoin** ratio per pair
on a centralized exchange (via [`ccxt`](https://github.com/ccxt/ccxt); default **Bybit**, with Binance and
OKX switchable), rebalancing with **limit orders** only when allocation drift exceeds a no-trade band.

It is built to be consumed primarily by an **AI agent** (but equally by a human or a web backend): the CLI
**computes facts and executes decisions deterministically**, and the brain **judges**. Same inputs → same
output; no LLM inside the tool; every read command emits a stable JSON contract.

## Mental model: CLI computes, agent judges

- **Layer 1 — the CLI (this tool):** deterministic arithmetic + fixed rules. It computes drift, P&L, and
  regime facts, and *proposes/executes* orders. It never decides whether a trade or a strategy change is
  wise.
- **Layer 2 — the brain (agent / human / web backend):** reads the facts and makes the judgment calls —
  whether/when to trade, whether to change a target ratio, which milestones matter.

The CLI has **no internal timer**: the agent owns cadence.

## Install & run

> Requires **Python 3.11**. Per the project rule, call the venv binary directly — do not `activate`.

```bash
py -3.11 -m venv .venv                                  # once, if missing
.venv/Scripts/python -m pip install -e ".[dev]"         # Windows; use .venv/bin on Linux/macOS
.venv/Scripts/python -m ccbalancer --help
.venv/Scripts/python -m ccbalancer version
.venv/Scripts/python -m ccbalancer config init          # scaffold ~/.ccbalancer with templates
```

Configuration lives in `~/.ccbalancer/` (`config.toml`, `portfolio.json`, `auth.json`, append-only logs).
See `config.example.toml` for every `[global]`/`[defaults]`/`[safety]` key, and **Configuration** below.

## Command taxonomy (three categories)

Commands are grouped by side effect — visible in `--help` so an agent can tell them apart:

| Category | Side effects | Commands |
|---|---|---|
| **read** | live data, **no writes** | `status` · `plan` · `analyze` · `indicator list` · `performance` · `regime` · `orders` · `version` |
| **write** | mutate state / place orders (dry-run by default, guarded) | `rebalance` · `cancel` · `pair` · `indicator set` · `flag` · `config` · `auth` |
| **audit** | local logs only, **no network** | `decisions` · `history` · `performance --history` · `export` |

Global flags: `--json` · `--pair SYMBOL` (repeatable) · `--profile NAME` · `--exchange` ·
`--testnet/--no-testnet` · `--config PATH`.

## The agent workflow

A full decision loop chains read → write → audit. Every step takes `--json` for machine consumption.

```bash
# 1. ANALYZE — read-only market intelligence (self-computed indicators across timeframes)
ccbalancer analyze BTC/USDT --json
ccbalancer regime --json            # price-variance since the target ratio was set → review flag + scenarios

# 2. PLAN — deterministic decisions + a confirm-token (no orders placed; appends to decision_log.jsonl)
ccbalancer plan --json              # → {"confirm_token": "ab12cd34ef56", "pairs": [...]}

# 3. REBALANCE — dry-run by default; execution requires the token from step 2
ccbalancer rebalance --json                                   # dry-run preview (re-issues the token)
ccbalancer rebalance --execute --confirm ab12cd34ef56 --json  # places limit orders (guarded)

# 4. PERFORMANCE — realized/unrealized P&L and ROI via true cost-basis
ccbalancer performance --json

# 5. DECISIONS / HISTORY — replay the offline memory (zero network)
ccbalancer decisions --json
ccbalancer history --json
```

### Three distinct signals (kept separate)

1. **Allocation drift** — current allocation vs the **target ratio** → triggers a rebalance trade
   (`status`, `plan`, `rebalance`).
2. **Performance / P&L** — current value vs **invested capital** via true cost-basis → is the strategy
   working? (`performance`).
3. **Regime** — price now vs price when the target was set → a **review flag + suggested ratio(s) +
   what-if scenarios** so the brain can decide whether to de-risk (`regime`). The CLI never auto-changes
   the ratio.

Plus **agent-defined milestones** (`flag add|list|remove`): persistent watch-conditions the agent
registers; the CLI evaluates them deterministically and reports hit/miss/unknown.

## Stable JSON contract

`--json` writes **machine output to stdout**; all logs go to **stderr**. Every read response is a stable
envelope:

- **`schema_version`** — an integer on every response. Bumped only on a breaking shape change, so an agent
  can pin and detect drift.
- **Stable key order**, **enum-string** reasons (e.g. `"within_band"`, `"abnormal_price"`), and
  fixed field names.
- **Exit code** carries the outcome class (see below) — branch on it, not on parsing stderr.

```jsonc
// ccbalancer plan --json
{
  "schema_version": 1,
  "command": "plan",
  "exchange": "bybit",
  "testnet": true,
  "generated_at": "2026-06-21T12:00:00Z",
  "confirm_token": "ab12cd34ef56",
  "pairs": [
    {
      "symbol": "BTC/USDT",
      "rebalance": true,
      "reason": "ok",
      "drift_pct": 10.91,
      "target_volatile_pct": 80.0,
      "current_volatile_pct": 90.91,
      "proposed_order": {"side": "sell", "amount": 0.12, "limit_price": 50010.0, "notional": 5995.0}
    }
  ]
}
```

### Exit codes

| Code | Meaning | Raised by |
|---|---|---|
| `0` | OK / no-op | success, or nothing actionable |
| `2` | config / portfolio / auth / state / flag error | bad settings, unknown pair, corrupt local file |
| `3` | exchange / network failure | unreachable venue, timeout after retries, API error |
| `4` | order rejected | exchange refused every placed order |
| `5` | partial failure | some orders placed, some rejected |
| `6` | safety blocked | kill-switch present, session cap exceeded, or missing/stale confirm-token |

## Safety guardrails (write path)

`rebalance` is **dry-run by default**. Execution (`--execute`) is gated by, in order:

- a **confirm-token** issued by `plan`/dry-run (digests the *set + direction* of trades and the exchange
  context — stable across small price moves, changes only when the trades change);
- a per-run **session notional cap** (`[safety].max_session_notional_usd`, default `1000`; `0` = unlimited);
- a **kill-switch** file (`~/.ccbalancer/STOP`) that blocks all placement (`cancel` is never blocked);
- **trade-only API keys** (DESIGN expects scoped credentials).

A missing/stale token or a tripped guard exits `6` and places nothing.

## Hardening & resilience

- **Timeouts** — every exchange call uses `[global].http_timeout_ms` (default `10000`).
- **Bounded retries** — transient failures (`RequestTimeout`, `DDoSProtection`, `ExchangeNotAvailable`)
  on **idempotent** calls (reads and `cancel`) are retried `[global].http_retries` times (default `2`)
  with exponential backoff (`[global].retry_backoff_ms`, default `500` → 500ms, 1000ms, …). After the
  budget is exhausted the call fails with exit `3`.
- **Order placement never auto-retries.** A timed-out `create_order` leaves the outcome unknown — the
  order may already rest on the book — so a blind retry could double-fill. Re-run `rebalance` instead:
  cancel-and-replace is idempotent (it cancels our own leftover `ccb-`-tagged orders first).
- **Sanity check** — a ticker whose `last` deviates more than `[global].quote_sanity_pct` (default `15`)
  from the bid/ask mid, or a crossed/non-positive book, is rejected as `abnormal_price` (the pair is
  skipped, not traded). Tune the threshold per venue liquidity.

## Offline & cached-data paths

- **Indicators** (`analyze`) read OHLCV through a local cache at `~/.ccbalancer/ohlcv/`. When the cache is
  fresh it is reused; when it is stale (older than `CACHE_STALE_FACTOR` timeframes) the tool refreshes
  from the exchange and **falls back to the stale cache** if the network is unavailable — so analysis
  degrades gracefully rather than failing.
- **`analyze --require-fresh`** opts out of that fallback: a timeframe whose cache is stale and cannot be
  refreshed **fails** instead of returning stale candles. Use it when a decision must not run on old data.
- **Audit commands** (`decisions`, `history`, `performance --history`, `export`) read only local logs and
  make **zero network calls** — they work fully offline.

## Configuration & credentials

- **Settings** (`~/.ccbalancer/config.toml`): exchange, testnet, sanity %, limit offset, timeouts, retries,
  per-pair defaults, and `[safety]`. Resolution precedence: **CLI flag → auth profile → env → TOML →
  built-in default**.
- **Credentials** are managed `gh`-style by `auth login` into named **profiles** (one active at a time,
  overridable with `--profile`). Secrets default to the OS **keyring**, with a best-effort `0600`
  plaintext file fallback (`--no-keyring`). Legacy `CCB_API_KEY`/`CCB_API_SECRET` env vars remain a
  no-profile fallback for CI. Secrets are always masked in output.

```bash
ccbalancer auth login --name bybit-main --exchange bybit          # prompts for key/secret (+passphrase on OKX)
ccbalancer auth list                                              # profiles, active marked, secrets masked
ccbalancer auth use bybit-main
ccbalancer pair add BTC/USDT --target 80/20 --band 5 --entry-price 50000 --invested 10000
```

## Development

```bash
.venv/Scripts/python -m pytest tests/ -v
.venv/Scripts/python -m pytest tests/ --cov=ccbalancer --cov-report=term-missing
```

Tests **mock the exchange and never hit the network** (`FakeExchangeStore`). See `docs/DESIGN.md` for the
architecture and `docs/PROGRESS.md` for phase status.
