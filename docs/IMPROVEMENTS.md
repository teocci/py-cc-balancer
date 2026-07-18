# IMPROVEMENTS

Enhancement backlog (non-blocking, deferred). Promote to a phase when scheduled.

| ID | Idea | Notes |
|----|------|-------|
| [I-1](improvements/I-1.md) | Sub-accounts per pair | True balance isolation. Multi-account now exists via auth profiles (`--profile`); sub-accounts within one account still future. |
| [I-2](improvements/I-2.md) | Additional exchanges | OKX added (Bybit/Binance/OKX). ccxt supports many more; extend `SUPPORTED_EXCHANGES` + a quirks row per venue. |
| [I-3](improvements/I-3.md) | Market-order mode | Alternative to limit orders for immediate fills. |
| [I-4](improvements/I-4.md) | Multi-machine state sync | Reconcile `state.json` from exchange order history. |
| [I-5](improvements/I-5.md) | Command-scoped CLI flags | Split `_common_flags()` into composable parents so each subcommand's `--help` shows only the flags it uses (stops `--profile`/`--pair` leaking onto `auth login`, `pair`, `config`, `analyze`, `indicator`). ✅ Done in v0.2.0. |
| [I-6](improvements/I-6.md) | `--fields` output projection | Global `--fields a,b,c` projects `--json` payloads to the named top-level keys (agent token savings); `--json` stays compact. ✅ Done in v0.2.0. |
| [I-7](improvements/I-7.md) | `profile` → `account` rename | Rename the credential entity everywhere (`Account` model, store, config, render, env `CCB_ACCOUNT` with deprecated `CCB_PROFILE` fallback) + `auth.json` `profiles`→`accounts` migration; `auth` command name unchanged; adds `auth rename`. ✅ Done in v0.2.0. |
| [I-8](improvements/I-8.md) | Per-account data isolation + stable identity | Each account owns an `accounts/<id>/` book keyed by an immutable local id (rename/key-rotation-safe); best-effort exchange `account_ref` captured at login enables reattach + a rotation guard. Delivers the [F-5](fixes/F-5.md) fix. ✅ Done in v0.2.0. |
| [I-9](improvements/I-9.md) | Add ADX/+DI/-DI to the indicator registry, computed per timeframe. | ✅ Done in v0.3.0. |
| [I-10](improvements/I-10.md) | Emit supports[]/resistances[] per timeframe via clustered fractal swing pivots. | ✅ Done in v0.3.0. |
| [I-11](improvements/I-11.md) | Surface the CLI-computes/agent-judges model, complete the command taxonomy, and document analyze's timeframe + indicator surface. | ✅ Done in v0.3.0. |
