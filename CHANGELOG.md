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
