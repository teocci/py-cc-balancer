# Private API — Canceling Orders

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 62 lines · ~541 tokens · 2,165 chars
> **See also**: [Index](./README.md)

---

### Canceling Orders

To cancel an existing order use

- `cancelOrder ()` for a single order
- `cancelOrders ()` for multiple orders
- `cancelAllOrders ()` for all open orders
- `cancelAllOrdersAfter ()` for all open orders after the given timeout


Parameters

- **id** (String) *required* Order id (e.g. `1645807945000`)
- **symbol** (String) Unified CCXT market symbol **required** on some exchanges (e.g. `"BTC/USDT"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- An [order structure](#order-structure)


Parameters

- **ids** (\[String\]) *required* Order ids (e.g. `1645807945000`)
- **symbol** (String) Unified CCXT market symbol **required** on some exchanges (e.g. `"BTC/USDT"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- An array of [order structures](#order-structure)


Parameters

- **symbol** (String) Unified CCXT market symbol **required** on some exchanges (e.g. `"BTC/USDT"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- An array of [order structures](#order-structure)


Parameters

- **timeout** (number) countdown time in milliseconds **required** on some exchanges, 0 represents cancel the timer (e.g. ``10``\ )
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. ``{"type": "spot"}``\ )

Returns

- An object

#### Exceptions Upon Canceling Orders

The `cancelOrder()` is usually used on open orders only. However, it may happen that your order gets executed (filled and closed)
before your cancel-request comes in, so a cancel-request might hit an already-closed order.

A cancel-request might also throw a `OperationFailed` indicating that the order might or might not have been canceled successfully and whether you need to retry or not. Consecutive calls to `cancelOrder()` may hit an already canceled order as well.

As such, `cancelOrder()` can throw an `OrderNotFound` exception in these cases:
- canceling an already-closed order
- canceling an already-canceled order
