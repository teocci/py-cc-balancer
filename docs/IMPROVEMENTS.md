# IMPROVEMENTS

Enhancement backlog (non-blocking, deferred). Promote to a phase when scheduled.

| ID | Idea | Notes |
|----|------|-------|
| I-1 | Sub-accounts per pair | True balance isolation. Multi-account now exists via auth profiles (`--profile`); sub-accounts within one account still future. |
| I-2 | Additional exchanges | OKX added (Bybit/Binance/OKX). ccxt supports many more; extend `SUPPORTED_EXCHANGES` + a quirks row per venue. |
| I-3 | Market-order mode | Alternative to limit orders for immediate fills. |
| I-4 | Multi-machine state sync | Reconcile `state.json` from exchange order history. |
| I-5 | PyPI / pipx publish | Distribute beyond portable bundle. |
