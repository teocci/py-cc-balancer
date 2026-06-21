# Public API — Auto De Leverage

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 19 lines · ~111 tokens · 446 chars
> **See also**: [Index](./README.md)

---

## Auto De Leverage

*contract only*

Use the `fetchADLRank` method to get the public details of a symbols auto de leverage rank from the exchange.


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "futures"}`)

Returns

- An [auto de leverage structure](#auto-de-leverage)

### Auto De Leverage Stucture

