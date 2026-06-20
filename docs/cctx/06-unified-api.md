# Unified API

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 252 lines · ~3,339 tokens · 13,356 chars
> **See also**: [Index](./README.md)

---

- [Overriding Unified API Params](#overriding-unified-api-params)
- [Pagination](#pagination)
- [Automatic Pagination](#automatic-pagination)

The unified ccxt API is a subset of methods common among the exchanges. It currently contains the following methods:

- `fetchMarkets ()`: Fetches a list of all available markets from an exchange and returns an array of Market objects as defined by the [Market structure](#market-structure) (with properties such as `symbol`, `base`, `quote` etc.). Some exchanges do not have means for obtaining a list of markets via their online API. For those, the list of markets is hardcoded.
- `fetchCurrencies ()`: Fetches all available currencies from an exchange and returns an associative dictionary of currencies (objects with properties such as `code`, `name`, etc.). Some exchanges do not have means for obtaining currencies via their online API. For those, the currencies will be extracted from market pairs or hardcoded.
- `loadMarkets ([reload])`: Returns the list of markets as an object indexed by symbol and caches it with the exchange instance. Returns cached markets if loaded already, unless the `reload = true` flag is forced.
- `fetchOrderBook (symbol, limit = undefined, params = {})`: Fetch L2/L3 order book for a particular market trading symbol.
- `fetchStatus (params = {})`: Returns information regarding the exchange status from either the info hardcoded in the exchange instance or the API, if available.
- `fetchL2OrderBook (symbol, limit = undefined, params)`: Level 2 (price-aggregated) order book for a particular symbol.
- `fetchTrades (symbol, since, limit, params)`: Fetch recent trades for a particular trading symbol.
- `fetchTicker (symbol)`: Fetch latest ticker data by trading symbol.
- `fetchBalance ()`: Fetch Balance.
- `createOrder (symbol, type, side, amount, price, params)`
- `createOrders(orders, params)`
- `createLimitBuyOrder (symbol, amount, price, param)`
- `createLimitSellOrder (symbol, amount, price, param)`
- `createMarketBuyOrder (symbol, amount, param)`
- `createMarketSellOrder (symbol, amount, param)`
- `cancelOrder (id, symbol, params)`
- `fetchOrder (id, symbol, params)`
- `fetchOrders (symbol, since, limit, params)`
- `fetchOpenOrders (symbol, since, limit, params)`
- `fetchCanceledOrders (symbol, since, limit, params)`
- `fetchClosedOrders (symbol, since, limit, params)`
- `fetchMyTrades (symbol, since, limit, params)`
- `fetchOpenInterest (symbol, params)`
- `fetchVolatilityHistory (code, params)`
- `fetchUnderlyingAssets ()`
- `fetchSettlementHistory (symbol, since, limit, params)`
- `fetchLiquidations (symbol, since, limit, params)`
- `fetchMyLiquidations (symbol, since, limit, params)`
- `fetchGreeks (symbol, params)`
- `fetchAllGreeks (symbols, params)`
- `fetchCrossBorrowRate (code, params)`
- `fetchCrossBorrowRates (params)`
- `fetchIsolatedBorrowRate (symbol, params)`
- `fetchIsolatedBorrowRates (params)`
- `fetchOption (symbol, params)`
- `fetchOptionChain (code, params)`
- `fetchConvertQuote (fromCode, toCode, amount, params)`
- `createConvertTrade (id, fromCode, toCode, amount, params)`
- `fetchFundingRate (symbol, params)`
- `fetchFundingRates (symbols, params)`
- `fetchFundingRateHistory (symbol, since, limit, params)`
- `fetchFundingRateInterval (symbol, params)`
- `fetchFundingRateIntervals (symbols, params)`
- `fetchLongShortRatio (symbol, params)`
- `fetchAutoDeLeverageRank (symbol, params)`
- `fetchPositionAutoDeLeverageRank (symbol, params)`
- `fetchPositionsAutoDeLeverageRank (symbols, params)`
- ...


## Overriding Unified API Params

Note, that most of methods of the unified API accept an optional `params` argument. It is an associative array (a dictionary, empty by default) containing the params you want to override. The contents of `params` are exchange-specific, consult the exchanges' API documentation for supported fields and values. Use the `params` dictionary if you need to pass a custom setting or an optional parameter to your unified query.





```python
params = {
    'foo': 'bar',       # exchange-specific overrides in unified queries
    'Hello': 'World!',  # see their docs for more details on parameter names
}

# overrides go in the last argument to the unified call ↓ HERE
result = exchange.fetch_order_book(symbol, length, params)
```






## Pagination

Most of unified methods will return either a single object or a plain array (a list) of objects (trades, orders, transactions and so on). However, very few exchanges (if any at all) will return all orders, all trades, all ohlcv candles or all transactions at once. Most often their APIs `limit` output to a certain number of most recent objects. **YOU CANNOT GET ALL OBJECTS SINCE THE BEGINNING OF TIME TO THE PRESENT MOMENT IN JUST ONE CALL**. Practically, very few exchanges will tolerate or allow that.

To fetch historical orders or trades, the user will need to traverse the data in portions or "pages" of objects. Pagination often implies *"fetching portions of data one by one"* in a loop.

In most cases users are **required to use at least some type of pagination** in order to get the expected results consistently. If the user does not apply any pagination, most methods will return the exchanges' default, which may start from the beginning of history or may be a subset of most recent objects. The default behaviour (without pagination) is exchange-specific! The means of pagination are often used with the following methods in particular:

- `fetchTrades()`
- `fetchOHLCV()`
- `fetchOrders()`
- `fetchCanceledOrders()`
- `fetchClosedOrder()`
- `fetchClosedOrders()`
- `fetchOpenOrder()`
- `fetchOpenOrders()`
- `fetchMyTrades()`
- `fetchTransactions()`
- `fetchDeposit()`
- `fetchDeposits()`
- `fetchWithdrawals()`

With methods returning lists of objects, exchanges may offer one or more types of pagination. CCXT unifies **date-based pagination** by default, with timestamps **in milliseconds** throughout the entire library.


### Automatic Pagination

*Warning: this is an experimental feature and might produce unexpected/incorrect results in some instances.*

Recently, CCXT introduced a way to paginate through several results automatically by just providing the `paginate` flag inside `params,` lifting this work from the userland. Most leading exchanges support it, and more will be added in the future, but the easiest way to check it is to look in the method's documentation and search for the *pagination* parameter. As always there are exceptions, and some endpoints might not provide a way to paginate either through a timestamp or a cursor, and in those cases, there's nothing CCXT can do about it.


Right now, we have three different ways of paginating:
- **dynamic/time-based**: uses the `until` and `since` parameters to paginate through dynamic results like (trades, orders, transactions, etc). Since we don't know a priori how many entries are available to be fetched, it will perform one request at a time until we reach the end of the data or the maximum amount of pagination calls (configurable through an option)
- **deterministic**: when we can pre-compute the boundaries of each page, it will perform the requests concurrently for maximum performance. This applies to OHLCV, Funding Rates, and Open Interest and also respects the `paginationCalls` option.
- **cursor-based**: when the exchange provides a cursor inside the response, we extract the cursor and perform the subsequent request until the end of the data or reach the maximum number of pagination calls.

The user cannot select the pagination method used, it will depend from implementation to implementation, considering the exchange API's features.

#### Pagination params

We can't perform an infinite amount of requests, and some of them might throw an error for different reasons, thus, we have some options that allow the user to control these variables and other pagination specificities.

*All the options below, should be provided inside `params`, you can check the examples below*

- **paginate**: (**boolean**) indicates that the user wants to paginate through different pages to get more data. Default is *false*.
- **paginationCalls**: (**integer**) allows the user to control the maximum amount of requests to paginate the data. Due to the rate limits, this value should not be too high. Default is 10.
- **maxRetries**: (**integer**) how many times should the pagination mechanism retry upon getting an error. Default is 3
- **paginationDirection**: (**string**) Only applies to the dynamic pagination and it can be either *forward* (start the pagination from some time in the past and paginate forward) or *backward* (start from the most recent time and paginate backward). If *forward* is selected then a *since* parameter must also be provided. Default is *backward*.
- **maxEntriesPerRequest**: (**integer**): The max amount of entries per request so that we can maximize the data retrieved per call. It varies from endpoint to endpoint and CCXT will populate this value for you, but you can override it if needed.

#### Examples

```Python

trades = await binance.fetch_trades("BTC/USDT", params = {"paginate": True}) # dynamic/time-based

ohlcv = await binance.fetch_ohlcv("BTC/USDT", params = {"paginate": True, "paginationCalls": 5}) # deterministic-pagination will perform 5 requests

trades = await binance.fetch_trades("BTC/USDT", since = 1664812416000, params = {"paginate": True, "paginationDirection": "forward"}) # dynamic/time-based pagination starting from 1664812416000

ledger = await bybit.fetch_ledger(params = {"paginate": True}) # bybit returns a cursor so the pagination will be cursor-based

funding_rates = await binance.fetch_funding_rate_history("BTC/USDT:USDT", params = {"paginate": True, "maxEntriesPerRequest": 50}) # customizes the number of entries per request

```


### Working With Datetimes And Timestamps

All unified timestamps throughout the CCXT library are integers **in milliseconds** unless explicitly stated otherwise.

Below is the set of methods for working with UTC dates and timestamps and for converting between them:


### Date-based Pagination

This is the type of pagination currently used throughout the CCXT Unified API. The user supplies a `since` timestamp **in milliseconds** (!) and a number to `limit` results. To traverse the objects of interest page by page, the user runs the following (below is pseudocode, it may require overriding some exchange-specific params, depending on the exchange in question):




```python
if exchange.has['fetchOrders']:
    since = exchange.milliseconds () - 86400000  # -1 day from now
    # alternatively, fetch from a certain starting datetime
    # since = exchange.parse8601('2018-01-01T00:00:00Z')
    all_orders = []
    while since < exchange.milliseconds ():
        symbol = None  # change for your symbol
        limit = 20  # change for your limit
        orders = await exchange.fetch_orders(symbol, since, limit)
        if len(orders):
            since = orders[len(orders) - 1]['timestamp'] + 1
            all_orders += orders
        else:
            break
```






### id-based Pagination

The user supplies a `from_id` of the object, from where the query should continue returning results, and a number to `limit` results. This is the default with some exchanges, however, this type is not unified (yet). To paginate objects based on their ids, the user would run the following:





```python
if exchange.has['fetchOrders']:
    from_id = 'abc123'  # all ids are strings
    all_orders = []
    while True:
        symbol = None  # change for your symbol
        since = None
        limit = 20  # change for your limit
        params = {
            'from_id': from_id,  # exchange-specific non-unified parameter name
        }
        orders = await exchange.fetch_orders(symbol, since, limit, params)
        if len(orders):
            from_id = orders[len(orders) - 1]['id']
            all_orders += orders
        else:
            break
```









### Pagenumber-based (Cursor) Pagination

The user supplies a page number or an *initial "cursor"* value. The exchange returns a page of results and the *next "cursor"* value, to proceed from. Most of exchanges that implement this type of pagination will either return the next cursor within the response itself or will return the next cursor values within HTTP response headers.

See an example implementation here: https://github.com/ccxt/ccxt/blob/master/examples/py/coinbaseexchange-fetch-my-trades-pagination.py

Upon each iteration of the loop the user has to take the next cursor and put it into the overrided params for the next query (on the following iteration):




```python
if exchange.has['fetchOrders']:
    cursor = 0  # exchange-specific type and value
    all_orders = []
    while True:
        symbol = None  # change for your symbol
        since = None
        limit = 20  # change for your limit
        params = {
            'cursor': cursor,  # exchange-specific non-unified parameter name
        }
        orders = await exchange.fetch_orders(symbol, since, limit, params)
        if len(orders):
            # not thread-safe and exchange-specific!
            cursor = exchange.last_response_headers['CB-AFTER']
            all_orders += orders
        else:
            break
```





