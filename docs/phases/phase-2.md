# Phase 2 — Configuration (settings + secrets)

- **Objective:** Resolve settings from `~/.ccbalancer` with discovery + precedence.
- **Deliverables:** `config.py` (discovery `--config`→`CCB_CONFIG`→`./ccbalancer.toml`→`~/.ccbalancer/config.toml`; precedence env→TOML→default; secrets env-only via python-dotenv); `config.example.toml` (settings only — NO pairs); `.env.example`; `config show` / `config init`.
- **Definition of Done:** `test_config` green; `config show --json` masks secrets, exit 0; `config init` creates `~/.ccbalancer/`; missing secret → `ConfigError` (exit 2).
- **Out of scope:** Pairs (Phase 3), exchange.
