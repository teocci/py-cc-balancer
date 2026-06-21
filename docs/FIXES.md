# FIXES

Bug-fix log. One row per fix.

| ID | Symptom | Root cause | Fix | Phase |
|----|---------|-----------|-----|-------|
| F-1 | All authenticated Bybit calls fail with `retCode 10002` (server timestamp / `recv_window`) when the local clock drifts past 5 s; `status`/`orders`/`cancel`/`performance`/`rebalance` exit 3. | `ExchangeStore._build_client` built the ccxt client without `adjustForTimeDifference`, so requests were signed with the unsynced local clock. | Set `options.adjustForTimeDifference = True` on the ccxt client; ccxt syncs to the exchange clock during `load_markets` (invoked by every unified private call). | 11 |
