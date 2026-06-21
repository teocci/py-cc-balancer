# Private API — intro → Order Structure

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 149 lines · ~2,992 tokens · 11,969 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [intro](#intro)
- [Querying Orders](#querying-orders)
- [Order Structure](#order-structure)

---

## Orders


### Querying Orders

Most of the time you can query orders by an id or by a symbol, though not all exchanges offer a full and flexible set of endpoints for querying orders. Some exchanges might not have a method for fetching recently closed orders, the other can lack a method for getting an order by id, etc. The ccxt library will target those cases by making workarounds where possible.

The list of methods for querying orders consists of the following:

- `fetchCanceledOrders (symbol = undefined, since = undefined, limit = undefined, params = {})`
- `fetchClosedOrder (id, symbol = undefined, params = {})`
- `fetchClosedOrders (symbol = undefined, since = undefined, limit = undefined, params = {})`
- `fetchOpenOrder (id, symbol = undefined, params = {})`
- `fetchOpenOrders (symbol = undefined, since = undefined, limit = undefined, params = {})`
- `fetchOrder (id, symbol = undefined, params = {})`
- `fetchOrders (symbol = undefined, since = undefined, limit = undefined, params = {})`

Note that the naming of those methods indicates if the method returns a single order or multiple orders (an array/list of orders). The `fetchOrder()` method requires a mandatory order id argument (a string). Some exchanges also require a symbol to fetch an order by id, where order ids can intersect with various trading pairs. Also, note that all other methods above return an array (a list) of orders. Most of them will require a symbol argument as well, however, some exchanges allow querying with a symbol unspecified (meaning *all symbols*).

The library will throw a NotSupported exception if a user calls a method that is not available from the exchange or is not implemented in ccxt.

To check if any of the above methods are available, look into the `.has` property of the exchange:



```python
import ccxt
id = 'binance'
exchange = getattr(ccxt, id)()
print(exchange.has)
```

A typical structure of the `.has` property usually contains the following flags corresponding to order API methods for querying orders:


The meanings of boolean `true` and `false` are obvious. A string value of `emulated` means that particular method is missing in the exchange API and ccxt will workaround that where possible on the client-side.

#### Understanding The Orders API Design

The exchanges' order management APIs differ by design. The user has to understand the purpose of each specific method and how they're combined together into a complete order API:

- `fetchCanceledOrders()`- fetches a list of canceled orders
- `fetchClosedOrder()`- fetches a single closed order by order id
- `fetchClosedOrders()` – fetches a list of closed (or canceled) orders.
- `fetchMyTrades()` – though not a part of the orders' API, it is closely related, since it provides the history of settled trades.
- `fetchOpenOrder()`- fetches a single open order by order id
- `fetchOpenOrders()` – fetches a list of open orders.
- `fetchOrder()` – fetches a single order (open or closed) by order `id`.
- `fetchOrders()` – fetches a list of all orders (either open or closed/canceled).
- `createOrder()` – used for placing orders
- `createOrders()` – used for placing multiple orders within the same request
- `cancelOrder()` – used for canceling a single order
- `cancelOrders()` - used for canceling multiple orders
- `cancelAllOrders()` - used for canceling all orders
- `cancelAllOrdersAfter()` - used for canceling all orders after the given timeout

The majority of the exchanges will have a way of fetching currently-open orders. Thus, the `exchange.has['fetchOpenOrders']`. If that method is not available, then most likely the `exchange.has['fetchOrders']` that will provide a list of all orders. The exchange will return a list of open orders either from `fetchOpenOrders()` or from `fetchOrders()`. One of the two methods is usually available from any exchange.

Some exchanges will provide the order history, other exchanges will not. If the underlying exchange provides the order history, then the `exchange.has['fetchClosedOrders']` or the `exchange.has['fetchOrders']`. If the underlying exchange does not provide the order history, then `fetchClosedOrders()` and `fetchOrders()` are not available. In the latter case, the user is required to build a local cache of orders and track the open orders using `fetchOpenOrders()` and `fetchOrder()` for order statuses and for marking them as closed locally in the userland (when they're not open anymore).

If the underlying exchange does not have methods for order history (`fetchClosedOrders()` and `fetchOrders()`), then it will provide `fetchOpenOrders` + the trade history with `fetchMyTrades` (see [How Orders Are Related To Trades](#how-orders-are-related-to-trades)). That set of information is in many cases enough for tracking in a live-trading robot. If there's no order history – you have to track your live orders and restore historical info from open orders and historical trades.

In general, the underlying exchanges will usually provide one or more of the following types of historical data:

- `fetchClosedOrders()`
- `fetchOrders()`
- `fetchMyTrades()`

Any of the above three methods may be missing, but the exchanges APIs will usually provide at least one of the three methods.

If the underlying exchange does not provide historical orders, the CCXT library will not emulate the missing functionality – it has to be added on the user side where necessary.

**Please, note, that a certain method may be missing either because the exchange does not have a corresponding API endpoint, or because CCXT has not implemented it yet (the library is also a work in progress). In the latter case, the missing method will be added as soon as possible.**

#### Querying Multiple Orders And Trades

All methods returning lists of trades and lists of orders, accept the second `since` argument and the third `limit` argument:

- `fetchTrades()` (public)
- `fetchMyTrades()` (private)
- `fetchOrders()`
- `fetchOpenOrders()`
- `fetchClosedOrders()`
- `fetchCanceledOrders()`

The second  argument `since` reduces the array by timestamp, the third `limit` argument reduces by number (count) of returned items.

If the user does not specify `since`, the `fetchTrades()/fetchOrders()` methods will return the default set of results from the exchange. The default set is exchange-specific, some exchanges will return trades or recent orders starting from the date of listing a pair on the exchange, other exchanges will return a reduced set of trades or orders (like, last 24 hours, last 100 trades, first 100 orders, etc). If the user wants precise control over the timeframe, the user is responsible for specifying the `since` argument.

**NOTE: not all exchanges provide means for filtering the lists of trades and orders by starting time, so, the support for `since ` and `limit` is exchange-specific. However, most exchanges do provide at least some alternative for "pagination" and "scrolling" which can be overrided with extra `params` argument.**

Some exchanges do not have a method for fetching closed orders or all orders. They will offer just the `fetchOpenOrders()` endpoint, and sometimes also a `fetchOrder` endpoint as well. Those exchanges don't have any methods for fetching the order history. To maintain the order history for those exchanges the user has to store a dictionary or a database of orders in the userland and update the orders in the database after calling methods like `createOrder()`, `fetchOpenOrders()`, `cancelOrder()`, `cancelAllOrders()`.

#### By Order Id

To get the details of a particular order by its id, use the `fetchOrder()` / `fetch_order()` method. Some exchanges also require a symbol even when fetching a particular order by id.

The signature of the fetchOrder/fetch_order method is as follows:


**Some exchanges don't have an endpoint for fetching an order by id, ccxt will emulate it where possible.** For now it may still be missing here and there, as this is a work in progress.

You can pass custom overrided key-values in the additional params argument to supply a specific order type, or some other setting if needed.

Below are examples of using the fetchOrder method to get order info from an authenticated exchange instance:



#### All Orders


**Some exchanges don't have an endpoint for fetching all orders, ccxt will emulate it where possible.** For now it may still be missing here and there, as this is a work in progress.

#### Open Orders


#### Closed Orders

Do not confuse *closed orders* with *trades* aka *fills* ! An order can be closed (filled) with multiple opposing trades! So, a *closed order* is not the same as a *trade*. In general, the order does not have a `fee` at all, but each particular user trade does have `fee`, `cost` and other properties. However, many exchanges propagate those properties to the orders as well.

**Some exchanges don't have an endpoint for fetching closed orders, ccxt will emulate it where possible.** For now it may still be missing here and there, as this is a work in progress.


### Order Structure

Most of methods returning orders within ccxt unified API will yield an order structure as described below:


- The `status` of an order is usually either `'open'` (not filled or partially filled), `'closed'` (fully filled), or `'canceled'` (unfilled and canceled, or partially filled then canceled).
- Some exchanges allow the user to specify an expiration timestamp upon placing a new order. If the order is not filled by that time, its `status` becomes `'expired'`.
- Use the `filled` value to determine if the order is filled, partially filled or fully filled, and by how much.
- The work on `'fee'` info is still in progress, fee info may be missing partially or entirely, depending on the exchange capabilities.
- The `fee` currency may be different from both traded currencies (for example, an ETH/BTC order with fees in USD).
- The `lastTradeTimestamp` timestamp may have no value and may be `undefined/None/null` where not supported by the exchange or in case of an open order (an order that has not been filled nor partially filled yet).
- The `lastTradeTimestamp`, if any, designates the timestamp of the last trade, in case the order is filled fully or partially, otherwise `lastTradeTimestamp` is `undefined/None/null`.
- Order `status` prevails or has precedence over the `lastTradeTimestamp`.
- The `cost` of an order is: `{ filled * price }`
- The `cost` of an order means the total *quote* volume of the order (whereas the `amount` is the *base* volume). The value of `cost` should be as close to the actual most recent known order cost as possible. The `cost` field itself is there mostly for convenience and can be deduced from other fields.
- The `clientOrderId` field can be set upon placing orders by the user with [custom order params](#custom-order-params). Using the `clientOrderId` the user can later distinguish between own orders. This is only available for the exchanges that do support `clientOrderId` at this time.

#### timeInForce

The `timeInForce` field may be `undefined/None/null` if not specified by the exchange. The unification of `timeInForce` is a work in progress.

Possible values for the`timeInForce` field:

- `'GTC'` = _Good Till Cancel(ed)_, the order stays on the orderbook until it is matched or canceled.
- `'IOC'` = _Immediate Or Cancel_, the order has to be matched immediately and filled either partially or completely, the unfilled remainder is canceled (or the entire order is canceled).
- `'FOK'` = _Fill Or Kill_, the order has to get fully filled and closed immediately, otherwise the entire order is canceled.
- `'PO'` = _Post Only_, the order is either placed as a maker order, or it is canceled. This means the order must be placed on orderbook for at at least time in an unfilled state. The unification of `PO` as a `timeInForce` option is a work in progress with unified exchanges having `exchange.has['createPostOnlyOrder'] == True`.
