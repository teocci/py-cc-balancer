# Phase 8 — Market intelligence (OHLCV, indicators, `analyze`)

- **Objective:** Read-only market intelligence so the agent (Layer 2) can reason — the agent's "eyes",
  online before order execution.
- **Deliverables:**
  - `utils/indicators.py` — pure functions over candle lists: `ema`, `rsi` (Wilder), `macd`,
    `bollinger`, `atr`, `fib_levels(high, low)`. Hand-rolled (no `TA-Lib` C dep); extensible registry.
  - `stores/exchange.py` — add `fetch_ohlcv(symbol, timeframe, limit)`.
  - `stores/market_cache.py` — cached OHLCV under `~/.ccbalancer/ohlcv/{symbol}/{timeframe}.jsonl`,
    TTL/staleness, `--require-fresh`, offline fallback.
  - `managers/indicators_manager.py` — injected `exchange_store` + `market_cache`; multi-timeframe
    `IndicatorSnapshot`s; returns `None` on offline-with-no-cache.
  - `models/` — `IndicatorSnapshot` (frozen+slots).
  - Extend portfolio model + `pair add` to capture `entry_price`, `entry_ts`, `invested_capital`,
    `target_set_price`, `target_set_ts` (foundation for Phases 11–12).
  - `config.py`/`constants.py` — `data_exchange`, `decision_timeframes`, `analysis_timeframes`.
  - Wire `analyze <pair> [--timeframe ...]` in `cli.py` (JSON carries `schema_version`).
- **Definition of Done:** each indicator verified against fixed OHLCV fixtures (known RSI/MACD/EMA/BB/
  ATR/Fib values); cache hit/miss/stale/offline paths tested; `analyze BTC/USDT --timeframe 1h --json`
  returns a stable, versioned multi-timeframe snapshot; no network in tests.
- **Out of scope:** Order placement; P&L; regime signal.
