# RELEASE

Internal release index — one row per cut release, newest first, mapping a version to the phases
and items it shipped. Public, human-facing notes live in `CHANGELOG.md`; this file is the terse
index for agents. Pushing a `vX.Y.Z` tag triggers `.github/workflows/release.yml` (build + smoke
on Win/Linux/macOS, publish portable zips). Written by `phase-complete` (Part B).

| Release | Date | Phases | Theme |
|---------|------|--------|-------|
| v0.5.1 | 2026-07-19 | P-22 | live order-status reconciliation — book only real fills, nev |
| v0.5.0 | 2026-07-18 | P-20, P-21 | backtest sub-daily timeframes + Binance REST fallback, multi |
| v0.4.0 | 2026-07-18 | P-17, P-18, P-19 | backtest engine — historical data foundation, deterministic  |
| v0.3.0 | 2026-07-18 | P-15, P-16 | ADX + support/resistance indicators; --help discoverability |
| v0.2.0 | 2026-07-17 | I-5, I-6, I-7, I-8, F-5 | Account-CLI overhaul: command-scoped flags, `--fields`, `profile`→`account`, per-account isolation |
| v0.1.3 | 2026-07-16 | F-4 | OKX `load_markets` preopen crash (ccxt 4.5.65) |
| v0.1.2 | 2026-07-16 | F-3 | OKX passphrase on `auth login` |
| v0.1.1 | 2026-06-21 | F-2 | `auth login` testnet precedence; CI action bumps |
| v0.1.0 | 2026-06-21 | 0–14, Auth | Initial release: phased build (0–14) + multi-profile auth; portable bundles |
