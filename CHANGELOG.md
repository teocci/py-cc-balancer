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
