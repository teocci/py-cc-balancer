# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 0: project scaffold — `pyproject.toml`, `src/ccbalancer/` package skeleton,
  `__version__`, stderr logging, `version` command, and the docs/orchestration set.
- Phase 1: domain primitives — `exceptions`, `constants` (exit codes, `CCB_PREFIX`),
  `enums` (`OrderSide`, `SkipReason`, `OutputFormat`), and frozen+slots `models`.
- Phase 2: configuration — `config.py` (env→TOML→default precedence, `~/.ccbalancer`
  discovery, secret masking), `config.example.toml`, `.env.example`, `config show`/`config init`.
- Phase 3: portfolio store + `pair` commands — `stores/portfolio_store.py` (validated
  CRUD over `portfolio.json`) and `pair list/add/set/remove` CLI.
- Phase 4: exchange store — `stores/exchange.py`, a thin lazily-built ccxt wrapper
  (`load_markets`, `fetch_balance`, `fetch_ticker`, `fetch_open_orders`, `create_order`,
  `cancel_order`) with sandbox toggle and ccxt→domain error translation; `FakeExchangeStore`
  test double in `conftest.py`. Only module that touches the network.
- Phase 5: state store + portfolio snapshots — `stores/state_store.py` (per-pair upsert
  into `state.json`, append-only `history.jsonl`, atomic writes, `StateError` on corrupt
  files), `utils/timeutil.py` (UTC ISO-8601 `now_iso`/`parse_iso`/`hours_between`),
  `utils/money.py` (Decimal-backed `precision_to_decimals`/`round_amount`/`notional`), and
  `managers/portfolio_manager.py` (balances + tickers + state → `PairSnapshot`, batched fetch).
- Phase 6: rebalance decision logic — `managers/rebalance_manager.py`, a pure
  `RebalanceManager.decide(pair, snapshot)` (no I/O, no mocks) with ordered guards
  (`ABNORMAL_PRICE` → `MARKET_UNAVAILABLE` → optional `TOO_SOON` → `WITHIN_BAND` →
  `BELOW_MIN_NOTIONAL` → `INSUFFICIENT_BALANCE` → max-trade clamp → `OK`), signed
  `drift_pct` sizing for BUY/SELL, passive limit-price offset, and precision-aware
  amount rounding; `from_config` wires the three relevant settings from `AppConfig`.
- Phase 7: read-only CLI — `utils/render.py` (single stable-JSON/text serialization
  path: fixed key order, enum-string reasons, `schema_version` envelope) and the
  `status`/`plan` commands wired over `PortfolioManager.snapshots` → `RebalanceManager.decide`,
  with `--pair` filtering and an `_exchange_store` seam for network-free tests;
  `SCHEMA_VERSION` constant. `plan --json` emits the stable contract incl `days_since_last`;
  balanced holdings → all `within_band`, exit 0.
- Phase 8: market intelligence — `utils/indicators.py` (pure, hand-rolled `sma`, `ema`, `rsi`
  (Wilder), `macd`, `bollinger`, `atr`, `fib_levels`; None-padded aligned series),
  `models/IndicatorSnapshot` (frozen+slots; RSI value/thresholds/zone, EMA map, Bollinger,
  ATR, volume + volume MA, Fib), `stores/exchange.py` `fetch_ohlcv`, `stores/market_cache.py`
  (cached OHLCV under `~/.ccbalancer/ohlcv/{symbol}/{tf}.jsonl`, timeframe-based freshness +
  offline fallback), and `managers/indicators_manager.py` (multi-timeframe snapshots resolving
  fresh-cache-hit → refetch → stale fallback → offline-none).
  - **Introspectable registry** (`utils/indicator_registry.py`): the catalog of indicators and
    their parameters (name/type/default/description) — the single source agents query to discover
    and validate the config surface. Indicator *parameters/thresholds* live in their own
    `indicators.toml` (kept out of `config.toml`), resolved over registry defaults; RSI thresholds
    yield a deterministic `rsi_zone` fact (CLI computes the comparison, agent judges).
  - Commands: `indicator list` (read — serializes the registry + current values) and
    `indicator set <name> KEY=VALUE…` (write — registry-validated, atomic `indicators.toml`
    rewrite); `analyze <pair> [--timeframe ...] [--require-fresh]` (stable `schema_version`
    envelope; `data_exchange` may differ from the trading exchange).
  - Config: `data_exchange`/`decision_timeframes`/`analysis_timeframes`/`ohlcv_limit`;
    `PairConfig` cost-basis baselines (`entry_price`/`entry_ts`/`invested_capital`/
    `target_set_price`/`target_set_ts`) with `pair add/set` flags.
  - RSI verified against the StockCharts reference (70.53); cache hit/miss/stale/offline and the
    discover→set→analyze loop covered, no network in tests.
- Phase 9: decision memory + audit category — `stores/decision_store.py`, an append-only
  `~/.ccbalancer/decision_log.jsonl` (one compact, jq-queryable JSON line per decision carrying
  inputs, signed drift, the full guard pass/fail ladder, and the proposed order, each with
  `schema_version`); `guard_ladder()` reconstructs every guard's status from the decision reason
  via `GUARD_ORDER` (single source of truth in `rebalance_manager`, so the log mirrors the runtime
  guard chain). `plan` appends one record per pair; `status`'s display-only `decide()` does not write.
  - `StateStore.load_history()` reads `history.jsonl` back as raw dicts (tolerant of older schemas).
  - **Audit command group** (local logs only — zero network, no exchange access): `decisions` and
    `history` replay their logs (stable envelope, `--pair` filter, text or `--json`); `export` bundles
    both as one JSON document (always JSON). Top-level `--help` now groups commands by read/write/audit.
  - Audit network-freeness enforced in tests via an `_exchange_store` seam that raises if touched.
- Phase 10: execution + safety guardrails + Binance — `managers/execution_manager.py` runs the
  cancel-and-replace flow (cancel our own stale `CCB_PREFIX` orders → place one tagged limit order
  per actionable decision → persist `state.json` + append `history.jsonl` + `ledger.jsonl` + a
  `rebalance` decision-log record); re-runs are idempotent. `stores/ledger_store.py` and the
  frozen+slots `Fill` model own the append-only `~/.ccbalancer/ledger.jsonl` (the cost-basis source).
  - **Safety guardrails:** `rebalance` is dry-run by default (writes nothing) and only executes with
    `--execute`; an intent-level **confirm-token** (digest of exchange + testnet + each actionable
    pair's `symbol:side`, stable across price drift) is issued by `plan`/dry-run and required by
    `--execute --confirm`; a per-run `[safety].max_session_notional_usd` cap (default 1000, `0` =
    unlimited) bounds total placed notional; a `~/.ccbalancer/STOP` **kill-switch** file blocks
    placement (never `cancel`); execution requires trade-only credentials. New `SafetyConfig`,
    `SafetyError`, and exit code `SAFETY_BLOCKED` (6).
  - **Binance** enabled alongside Bybit via `stores/exchange_quirks.py` (a tested per-exchange matrix
    for the clientOrderId param, tag-length limit, and cancel semantics), consulted by `ExchangeStore`.
  - New CLI: `rebalance` (write, guarded), `orders` (read, flags our open orders), `cancel`
    (write, dry-run by default, kill-switch-exempt). Exit codes: `OK`/`PARTIAL_FAILURE`/
    `ORDER_REJECTED` from execution results, `SAFETY_BLOCKED` from a tripped guardrail.
- Phase 11: performance & cost-basis — `managers/performance_manager.py` walks the append-only
  `ledger.jsonl` with the **average-cost** method (all money math via `Decimal`, exact to the cent) and
  marks the held position to market with live tickers, computing realized P&L per sell, unrealized P&L
  of the open position, fees, and ROI — per pair and across the portfolio (`portfolio_totals`). The
  frozen+slots `models/PerformanceSnapshot` carries each pair's P&L. Fees are normalized to quote terms
  (a base-denominated fee is valued at its fill price; a quote/None/other fee is taken as-is) so
  accounting is deterministic with no extra price lookups.
  - **Baseline fallback:** a pair with no fills falls back to its `entry_price`/`invested_capital`
    baseline (synthesizing a position) so unrealized P&L is still meaningful on an empty ledger; ROI's
    denominator is the pinned `invested_capital` when set, otherwise cumulative gross buy cost.
  - Commands: `performance [--pair]` (read — live tickers, per-pair + portfolio totals in a stable
    `schema_version` envelope) and `performance --history` (audit — replays realized P&L per symbol
    from the ledger only, with the per-fill trade timeline; zero network). Top-level `--help` taxonomy
    updated. Network-freeness of `--history` enforced in tests via the raising `_exchange_store` seam.
