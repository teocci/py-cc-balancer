# IMPROVEMENTS

Enhancement backlog (non-blocking, deferred). Promote to a phase when scheduled.

| ID | Idea | Notes |
|----|------|-------|
| I-1 | Sub-accounts per pair | True balance isolation; `ExchangeStore` already takes key/secret. |
| I-2 | Additional exchanges | ccxt supports many; add config-driven selection beyond Bybit/Binance. |
| I-3 | Market-order mode | Alternative to limit orders for immediate fills. |
| I-4 | Multi-machine state sync | Reconcile `state.json` from exchange order history. |
| I-5 | PyPI / pipx publish | Distribute beyond portable bundle. |
