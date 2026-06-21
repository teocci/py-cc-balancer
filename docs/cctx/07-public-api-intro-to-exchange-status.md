# Public API — intro → Exchange Status

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 413 lines · ~7,004 tokens · 28,018 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [intro](#intro)
- [Order Book](#order-book)
- [Price Tickers](#price-tickers)
- [OHLCV Candlestick Charts](#ohlcv-candlestick-charts)
- [Public Trades](#public-trades)
- [Exchange Time](#exchange-time)
- [Exchange Status](#exchange-status)

---

- [Order Book](#order-book)
- [Price Tickers](#price-tickers)
- [OHLCV Candlestick Charts](#ohlcv-candlestick-charts)
- [Public Trades](#public-trades)
- [Exchange Time](#exchange-time)
- [Exchange Status](#exchange-status)
- [Borrow Rates](#borrow-rates)
- [Borrow Rate History](#borrow-rate-history)
- [Leverage Tiers](#leverage-tiers)
- [Funding Rate](#funding-rate)
- [Funding Rate History](#funding-rate-history)
- [Open Interest History](#open-interest-history)
- [Volatility History](#volatility-history)
- [Underlying Assets](#underlying-assets)
- [Liquidations](#liquidations)
- [Greeks](#greeks)
- [OptionChain](#option-chain)
- [Auto De Leverage](#auto-de-leverage)

## Order Book

Exchanges expose information on open orders with bid (buy) and ask (sell) prices, volumes and other data. Usually there is a separate endpoint for querying current state (stack frame) of the *order book* for a particular market. An order book is also often called *market depth*. The order book information is used in the trading decision making process.

To get data on order books, you can use

- `fetchOrderBook ()` // for a single markets order books
- `fetchOrderBooks ( symbols )` // for multiple markets order books
- `fetchOrderBooks ()` // for the order books of all markets


Parameters

- **symbol** (String) *required* Unified CCXT symbol (e.g. `"BTC/USDT"`)
- **limit** (Integer) The number of orders to return in the order book (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An [order book structure](#order-book-structure)


Parameters

- **symbols** (\[String\]) Unified CCXT symbols (e.g. `["BTC/USDT", "ETH/USDT"]`)
- **limit** (Integer) The number of orders to return in the order book (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A dictionary of [order book structures](#order-book-structure) indexed by market symbols

### fetchOrderBook Examples




```python
import time
delay = 2 # seconds
for symbol in exchange.markets:
    print (exchange.fetch_order_book (symbol))
    time.sleep (delay) # rate limit
```






### Order Book Structure


**The timestamp and datetime may be missing (`undefined/None/null`) if the exchange in question does not provide a corresponding value in the API response.**

Prices and amounts are floats. The bids array is sorted by price in descending order. The best (highest) bid price is the first element and the worst (lowest) bid price is the last element. The asks array is sorted by price in ascending order. The best (lowest) ask price is the first element and the worst (highest) ask price is the last element. Bid/ask arrays can be empty if there are no corresponding orders in the order book of an exchange.

Exchanges may return the stack of orders in various levels of details for analysis. It is either in full detail containing each and every order, or it is aggregated having slightly less detail where orders are grouped and merged by price and volume. Having greater detail requires more traffic and bandwidth and is slower in general but gives a benefit of higher precision. Having less detail is usually faster, but may not be  enough in some very specific cases.

### Notes On Order Book Structure

- The `orderbook['timestamp']` is the time when the exchange generated this orderbook response (before replying it back to you). This may be missing (`undefined/None/null`), as documented in the Manual, not all exchanges provide a timestamp there. If it is defined, then it is the UTC timestamp **in milliseconds** since 1 Jan 1970 00:00:00.
- Some exchanges may index orders in the orderbook by order ids, in that case the order id may be returned as the third element of bids and asks: `[ price, amount, id ]`. This is often the case with L3 orderbooks without aggregation. The order `id`, if shown in the orderbook, refers to the orderbook and does not necessarily correspond to the actual order id from the exchanges' database as seen by the owner or by the others. The order id is an `id` of the row inside the orderbook, but not necessarily the true-`id` of the order (though, they may be equal as well, depending on the exchange in question).
- In some cases the exchanges may supply L2 aggregated orderbooks with order counts for each aggregated level, in that case the order count may be returned as the third element of bids and asks: `[ price, amount, count ]`. The `count` tells how many orders are aggregated on each price level in bids and asks.
- Also, some exchanges may return the order timestamp as the third element of bids and asks: `[ price, amount, timestamp ]`. The `timestamp` tells when the order was placed on the orderbook.

### Market Depth

Some exchanges accept a dictionary of extra parameters to the `fetchOrderBook () / fetch_order_book ()` function. **All extra `params` are exchange-specific (non-unified)**. You will need to consult exchanges docs if you want to override a particular param, like the depth of the order book. You can get a limited count of returned orders or a desired level of aggregation (aka *market depth*) by specifying an limit argument and exchange-specific extra `params` like so:





```python

import ccxt
# return up to ten bidasks on each side of the order book stack
limit = 10
ccxt.cex().fetch_order_book('BTC/USD', limit)
```






The levels of detail or levels of order book aggregation are often number-labelled like L1, L2, L3...

- **L1**: less detail for quickly obtaining very basic info, namely, the market price only. It appears to look like just one order in the order book.
- **L2**: most common level of aggregation where order volumes are grouped by price. If two orders have the same price, they appear as one single order for a volume equal to their total sum. This is most likely the level of aggregation you need for the majority of purposes.
- **L3**: most detailed level with no aggregation where each order is separate from other orders. This LOD naturally contains duplicates in the output. So, if two orders have equal prices they are **not** merged together and it's up to the exchange's matching engine to decide on their priority in the stack. You don't really need L3 detail for successful trading. In fact, you most probably don't need it at all. Therefore some exchanges don't support it and always return aggregated order books.

If you want to get an L2 order book, whatever the exchange returns, use the `fetchL2OrderBook(symbol, limit, params)` or `fetch_l2_order_book(symbol, limit, params)` unified method for that.

The `limit` argument does not guarantee that the number of bids or asks will always be equal to `limit`. It designates the upper boundary or the maximum, so at some moment in time there may be less than `limit` bids or asks. This is the case when the exchange does not have enough orders on the orderbook. However, if the underlying exchange API does not support a `limit` parameter for the orderbook endpoint at all, then the `limit` argument will be ignored. CCXT does not trim `bids` and `asks` if the exchange returns more than you request.

### Market Price

In order to get current best price (query market price) and calculate bidask spread take first elements from bid and ask, like so:






```python
orderbook = exchange.fetch_order_book (exchange.symbols[0])
bid = orderbook['bids'][0][0] if len (orderbook['bids']) > 0 else None
ask = orderbook['asks'][0][0] if len (orderbook['asks']) > 0 else None
spread = (ask - bid) if (bid and ask) else None
print (exchange.id, 'market price', { 'bid': bid, 'ask': ask, 'spread': spread })
```




## Price Tickers

A price ticker contains statistics for a particular market/symbol for some period of time in recent past, usually last 24 hours. The methods for fetching tickers are described below.

### A Single Ticker For One Symbol


### Multiple Tickers For All Or Many Symbols


Check the `exchange.has['fetchTicker']` and `exchange.has['fetchTickers']` properties of the exchange instance to determine if the exchange in question does support these methods.

**Please, note, that calling `fetchTickers ()` without a symbol is usually strictly rate-limited, an exchange may ban you if you poll that endpoint too frequently.**

### Ticker Structure

A ticker is a statistical calculation with the information calculated over the past 24 hours for a specific market.

The structure of a ticker is as follows:


#### Notes On Ticker Structure

- All fields in the ticker represent the past 24 hours prior to `timestamp`.
- The `bidVolume` is the volume (amount) of current best bid in the orderbook.
- The `askVolume` is the volume (amount) of current best ask in the orderbook.
- The `baseVolume` is the amount of base currency traded (bought or sold) in last 24 hours.
- The `quoteVolume` is the amount of quote currency traded (bought or sold) in last 24 hours.

**All prices in ticker structure are in quote currency. Some fields in a returned ticker structure may be undefined/None/null.**


Timestamp and datetime are both Universal Time Coordinated (UTC) in milliseconds.

- `ticker['timestamp']` is the time when the exchange generated this response (before replying it back to you). It may be missing (`undefined/None/null`), as documented in the Manual, not all exchanges provide a timestamp there. If it is defined, then it is a UTC timestamp **in milliseconds** since 1 Jan 1970 00:00:00.
- `exchange.last_response_headers['Date']` is the date-time string of the last HTTP response received (from HTTP headers). The 'Date' parser should respect the timezone designated there. The precision of the date-time is 1 second, 1000 milliseconds. This date should be set by the exchange server when the message originated according to the following standards:
    - https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.18
    - https://tools.ietf.org/html/rfc1123#section-5.2.14
    - https://tools.ietf.org/html/rfc822#section-5

Although some exchanges do mix-in orderbook's top bid/ask prices into their tickers (and some exchanges even serve top bid/ask volumes) you should not treat a ticker as a `fetchOrderBook` replacement. The main purpose of a ticker is to serve statistical data, as such, treat it as "live 24h OHLCV". It is known that exchanges discourage frequent `fetchTicker` requests by imposing stricter rate limits on these queries. If you need a unified way to access bids and asks you should use `fetchL[123]OrderBook` family instead.

To get historical prices and volumes use the unified [`fetchOHLCV`](#ohlcv-candlestick-charts) method where available. To get historical mark, index, and premium index prices, add one of `'price': 'mark'`, `'price': 'index'`, `'price': 'premiumIndex'` respectively to the [params-overrides](#overriding-unified-api-params) of `fetchOHLCV`. There are also convenience methods `fetchMarkPriceOHLCV`, `fetchIndexPriceOHLCV`, and `fetchPremiumIndexOHLCV` that obtain the mark, index and premiumIndex historical prices and volumes.

Methods for fetching tickers:

- `fetchTicker (symbol[, params = {}])`, symbol is required, params are optional
- `fetchTickers ([symbols = undefined[, params = {}]])`, both arguments optional

### Individually By Symbol

To get the individual ticker data from an exchange for a particular trading pair or a specific symbol – call the `fetchTicker (symbol)`:



```python
import random
if (exchange.has['fetchTicker']):
    print(exchange.fetch_ticker('LTC/ZEC')) # ticker for LTC/ZEC
    symbols = list(exchange.markets.keys())
    print(exchange.fetch_ticker(random.choice(symbols))) # ticker for a random symbol
```

### All At Once

Some exchanges (not all of them) also support fetching all tickers at once. See [their docs](#exchanges) for details. You can fetch all tickers with a single call like so:



```python
if (exchange.has['fetchTickers']):
    print(exchange.fetch_tickers()) # all tickers indexed by their symbols
```

Fetching all tickers requires more traffic than fetching a single ticker. Also, note that some exchanges impose higher rate-limits on subsequent fetches of all tickers (see their docs on corresponding endpoints for details). **The cost of the `fetchTickers()` call in terms of rate limit is often higher than average**. If you only need one ticker, fetching by a particular symbol is faster as well. You probably want to fetch all tickers only if you really need all of them and, most likely, you don't want to fetchTickers more frequently than once in a minute or so.

Also, some exchanges may impose additional requirements on the `fetchTickers()` call, sometimes you can't fetch the tickers for all symbols because of the API limitations of the exchange in question. Some exchanges accept a list of symbols in HTTP URL query params, however, because URL length is limited, and in extreme cases exchanges can have thousands of markets – a list of all their symbols simply would not fit in the URL, so it has to be a limited subset of their symbols. Sometimes, there are other reasons for requiring a list of symbols, and there may be a limit on the number of symbols you can fetch at once, but whatever the limitation, please, blame the exchange. To pass the symbols of interest to the exchange, you can supply a list of strings as the first argument to fetchTickers:



```python
if (exchange.has['fetchTickers']):
    print(exchange.fetch_tickers(['ETH/BTC', 'LTC/BTC'])) # listed tickers indexed by their symbols
```

Note that the list of symbols is not required in most cases, but you must add additional logic if you want to handle all possible limitations that might be imposed on the exchanges' side.

Like most methods of the Unified CCXT API, the last argument to fetchTickers is the `params` argument for overriding request parameters that are sent towards the exchange.

The structure of the returned value is as follows:


A general solution for fetching all tickers from all exchanges (even the ones that don't have a corresponding API endpoint) is on the way, this section will be updated soon.


## OHLCV Candlestick Charts

Most exchanges have endpoints for fetching OHLCV data, but some of them don't. The exchange boolean (true/false) property named `has['fetchOHLCV']` indicates whether the exchange supports candlestick data series or not.

To fetch OHLCV candles/bars from an exchange, ccxt has the `fetchOHLCV` method, which is declared in the following way:


You can call the unified `fetchOHLCV` / `fetch_ohlcv` method to get the list of OHLCV candles for a particular symbol like so:



```python
import time
if exchange.has['fetchOHLCV']:
    for symbol in exchange.markets:
        time.sleep (exchange.rateLimit / 1000) # time.sleep wants seconds
        print (symbol, exchange.fetch_ohlcv (symbol, '1d')) # one day
```

To get the list of available timeframes for your exchange see the `timeframes` property. Note that it is only populated when `has['fetchOHLCV']` is true as well.

The returned list of candles may have one or more missing periods, if the exchange did not have any trades for the specified timerange and symbol. To a user that would appear as gaps in a continuous list of candles. That is considered normal. If the exchange did not have any candles at that time, the CCXT library will show the results as returned from the exchange itself.

**There's a limit on how far back in time your requests can go.** Most of exchanges will not allow to query detailed candlestick history (like those for 1-minute and 5-minute timeframes) too far in the past. They usually keep a reasonable amount of most recent candles, like 1000 last candles for any timeframe is more than enough for most of needs. You can work around that limitation by continuously fetching (aka *REST polling*) latest OHLCVs and storing them in a CSV file or in a database.

**Note that the info from the last (current) candle may be incomplete until the candle is closed (until the next candle starts).**

Like with most other unified and implicit methods, the `fetchOHLCV` method accepts as its last argument an associative array (a dictionary) of extra `params`, which is used to [override default values](#overriding-unified-api-params) that are sent in requests to the exchanges. The contents of `params` are exchange-specific, consult the exchanges' API documentation for supported fields and values.

The `since` argument is an integer UTC timestamp **in milliseconds** (everywhere throughout the library with all unified methods).

If `since` is not specified the `fetchOHLCV` method will return the time range as is the default from the exchange itself.  This is not a bug. Some exchanges will return candles from the beginning of time, others will return most recent candles only, the exchanges' default behaviour is expected. Thus, without specifying `since` the range of returned candles will be exchange-specific. One should pass  the `since` argument to ensure getting precisely the history range needed.

### Get raw OHLCV response

Currently, the structure CCXT uses does not include the raw response from the exchange. However, users might be able to override the return value by doing:



```python
# add raw member at last position in list
async def test():
    ex = ccxt.async_support.coinbase()
    prase_ohlcv_original = ex.parse_ohlcv
    def prase_ohlcv_custom(ohlcv, market):
        res = prase_ohlcv_original(ohlcv, market)
        res.append(ohlcv)
        return res
    ex.parse_ohlcv = prase_ohlcv_custom
    result = await ex.fetch_ohlcv('BTC/USDT', '1m')
    print (result[0])

asyncio.run(test())
```


### Notes On Latency

Trading strategies require fresh up-to-date information for technical analysis, indicators and signals. Building a speculative trading strategy based on the OHLCV candles received from the exchange may have critical drawbacks. Developers should account for the details explained in this section to build successful bots.

First and foremost, when using CCXT you're talking to the exchanges directly. CCXT is not a server, nor a service, it's a software library. All data that you are getting with CCXT is received directly from the exchanges first-hand.

The exchanges usually provide two categories of public market data:

1. Fast primary first-order data that includes real time orderbooks and trades or fills
2. Slow second-order data that includes secondary tickers and kline OHLCV candles, that are calculated from the first-order data

The primary first-order data is updated by the exchanges APIs in pseudo real time, or as close to real time as possible, as fast as possible. The second-order data requires time for the exchange to calculate it. For example, a ticker is nothing more than a rolling 24-hour statistical cut of orderbooks and trades. OHLCV candles and volumes are also calculated from first-order trades and represent fixed statistical cuts of specific periods. The volume traded within an hour is just a sum of traded volumes of the corresponding trades that happened within that hour.

Obviously, it takes some time for the exchange to collect the first-order data and calculate the secondary statistical data from it. That literally means that **tickers and OHLCVs are always slower than orderbooks and trades**. In other words, there is always some latency in the exchange API between the moment when a trade happens and the moment when a corresponding OHLCV candle is updated or published by the exchange API.

The latency (or how much time is needed by the exchange API for calculating the secondary data) depends on how fast the exchange engine is, so it is exchange-specific. Top exchange engines will usually return and update fresh last-minute OHLCV candles and tickers at a very fast rate. Some exchanges might do it in regular intervals like once a second or once in a few seconds. Slow exchange engines might take minutes to update the secondary statistical information, their APIs might return the current most recent OHLCV candle a few minutes late.

If your strategy depends on the fresh last-minute most recent data you don't want to build it based on tickers or OHLCVs received from the exchange. Tickers and exchanges' OHLCVs are only suitable for display purposes, or for simple trading strategies for hour-timeframes or day-timeframes that are less susceptible to latency.

Thankfully, the developers of time-critical trading strategies don't have to rely on secondary data from the exchanges and can calculate the OHLCVs and tickers in the userland. That may be faster and more efficient than waiting for the exchanges to update the info on their end. One can aggregate the public trade history by polling it frequently and calculate candles by walking over the list of trades - please take a look into "build-ohlcv-bars" file inside [examples folder](https://github.com/ccxt/ccxt/tree/master/examples)

Due to the differences in their internal implementations the exchanges may be faster to update their primary and secondary market data over WebSockets. The latency remains exchange-specific, cause the exchange engine still needs time to calculate the secondary data, regardless of whether you're polling it over the RESTful API with CCXT or getting updates via WebSockets with CCXT Pro. WebSockets can improve the networking latency, so a fast exchange will work even better, but adding the support for WS subscriptions will not make a slow exchange engine work much faster.

If you want to stay on top of the second-order data latency, then you will have to calculate it on your side and beat the exchange engine in speed of doing so. Depending on the needs of your application, it may be tricky, since you will need to handle redundancy, "data holes" in the history, exchange downtimes, and other aspects of data aggregation which is a whole universe in itself that is impossible to fully cover in this Manual.


### Build OHLCV bars from trades

As noted in above paragraph, users can build candles manually using `buildOHLCV / build_ohlcv` method. You can see an example file named "build-ohlcv-bars" inside [examples folder](https://github.com/ccxt/ccxt/tree/master/examples). 
Notes:
- This method expects the provided trades to be chronologically sorted (newest trade to be the last in array)
- Due to some possible mistakes inside trade entries (coming from `watch_ohlcv` or other sources) inside `build_ohlcv` method we skip trades that have `0` price, to avoid distorted values for a candle. However, if you don't want to skip such trade items, set an option: 

```
exchange.options['buildOHLCV'] = {
    'skipZeroPrices': false
};
```

### OHLCV Structure

The fetchOHLCV method shown above returns a list (a flat array) of OHLCV candles represented by the following structure:


The list of candles is returned sorted in ascending (historical/chronological) order, oldest candle first, most recent candle last.

### Mark, Index and PremiumIndex Candlestick Charts

To obtain historical Mark, Index Price and Premium Index candlesticks pass the `'price'` [params-override](#overriding-unified-api-params) to `fetchOHLCV`. The `'price'` parameter accepts one of the following values:

- `'mark'`
- `'index'`
- `'premiumIndex'`


There are also convenience methods `fetchMarkOHLCV`, `fetchIndexOHLCV` and `fetchPremiumIndexOHLCV`



```python
exchange = ccxt.binance()
response = exchange.fetch_ohlcv('ADA/USDT', '1h', params={'price':'index'})
pprint(response)
# Convenience methods
mark_klines = exchange.fetch_mark_ohlcv('ADA/USDT', '1h')
index_klines = exchange.fetch_index_ohlcv('ADA/USDT', '1h')
pprint(mark_klines)
pprint(index_klines)
```


## Public Trades


You can call the unified `fetchTrades` / `fetch_trades` method to get the list of most recent trades for a particular symbol. The `fetchTrades` method is declared in the following way:


For example, if you want to print recent trades for all symbols one by one sequentially (mind the rateLimit!) you would do it like so:

#### **Typescript**


```python
import time
if exchange.has['fetchTrades']:
    for symbol in exchange.markets:  # ensure you have called loadMarkets() or load_markets() method.
        print (symbol, exchange.fetch_trades (symbol))
```

The fetchTrades method shown above returns an ordered list of trades (a flat array, sorted by timestamp in ascending order, oldest trade first, most recent trade last). A list of trades is represented by the [trade structure](#trade-structure).


Most exchanges return most of the above fields for each trade, though there are exchanges that don't return the type, the side, the trade id or the order id of the trade. Most of the time you are guaranteed to have the timestamp, the datetime, the symbol, the price and the amount of each trade.

The second optional argument `since` reduces the array by timestamp, the third `limit` argument reduces by number (count) of returned items.

If the user does not specify `since`, the `fetchTrades` method will return the default range of public trades from the exchange. The default set is exchange-specific, some exchanges will return trades starting from the date of listing a pair on the exchange, other exchanges will return a reduced set of trades (like, last 24 hours, last 100 trades, etc). If the user wants precise control over the timeframe, the user is responsible for specifying the `since` argument.

Most of unified methods will return either a single object or a plain array (a list) of objects (trades). However, very few exchanges (if any at all) will return all trades at once. Most often their APIs `limit` output to a certain number of most recent objects. **YOU CANNOT GET ALL OBJECTS SINCE THE BEGINNING OF TIME TO THE PRESENT MOMENT IN JUST ONE CALL**. Practically, very few exchanges will tolerate or allow that.

To fetch historical trades, the user will need to traverse the data in portions or "pages" of objects. Pagination often implies *"fetching portions of data one by one"* in a loop.

In most cases users are **required to use at least some type of pagination** in order to get the expected results consistently.

On the other hand, **some exchanges don't support pagination for public trades at all**. In general the exchanges will provide just the most recent trades.

The `fetchTrades ()` / `fetch_trades()` method also accepts an optional `params` (assoc-key array/dict, empty by default) as its fourth argument. You can use it to pass extra params to method calls or to override a particular default value (where supported by the exchange). See the API docs for your exchange for more details.

## Exchange Time

The `fetchTime()` method (if available) returns the current integer timestamp in milliseconds from the exchange server.


## Exchange Status

The exchange status describes the latest known information on the availability of the exchange API. This information is either hardcoded into the exchange class or fetched live directly from the exchange API. The `fetchStatus(params = {})` method can be used to get this information. The status returned by `fetchStatus` is one of:

- Hardcoded into the exchange class, e.g. if the API has been broken or shutdown.
- Updated using the exchange ping or `fetchTime` endpoint to see if its alive
- Updated using the dedicated exchange API status endpoint.


### Exchange Status Structure

The `fetchStatus()` method will return a status structure like shown below:


The possible values in the `status` field are:

- `'ok'` means the exchange API is fully operational
- `'shutdown`' means the exchange was closed, and the `updated` field should contain the datetime of the shutdown
- `'error'` means that either the exchange API is broken, or the implementation of the exchange in CCXT is broken
- `'maintenance'` means regular maintenance, and the `eta` field should contain the datetime when the exchange is expected to be operational again
