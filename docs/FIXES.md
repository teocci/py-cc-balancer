# FIXES

Bug-fix log. One row per fix.

| ID | Symptom | Root cause | Fix | Phase |
|----|---------|-----------|-----|-------|
| F-1 | All authenticated Bybit calls fail with `retCode 10002` (server timestamp / `recv_window`) when the local clock drifts past 5 s; `status`/`orders`/`cancel`/`performance`/`rebalance` exit 3. | `ExchangeStore._build_client` built the ccxt client without `adjustForTimeDifference`, so requests were signed with the unsynced local clock. | Set `options.adjustForTimeDifference = True` on the ccxt client; ccxt syncs to the exchange clock during `load_markets` (invoked by every unified private call). | 11 |
| F-2 | `auth login` saves the profile but the credential check fails (`retCode 10003 "API key is invalid"`, exit 3) for valid **mainnet** keys; `auth status` reports `valid:null`. Could only be worked around with an explicit `--no-testnet`. | `_cmd_auth_login` hardcoded `testnet = DEFAULT_TESTNET if args.testnet is None else args.testnet`, ignoring `CCB_TESTNET` and TOML `[global] testnet` — unlike every other command. A mainnet key thus always landed in a sandbox profile and was verified against the testnet, which rejects it. | Added `config.resolve_login_testnet()` applying the app-wide precedence (flag > `CCB_TESTNET` env > TOML `[global] testnet` > default); `auth login` now calls it. The safety default (testnet) is unchanged when nothing is configured. | Auth |
