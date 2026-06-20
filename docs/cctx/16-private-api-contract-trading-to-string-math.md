# Private API — Contract Trading → String Math

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 352 lines · ~4,134 tokens · 16,536 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [Contract Trading](#contract-trading)
- [Auto De Leverage](#auto-de-leverage)
- [Proxy](#proxy)
- [String Math](#string-math)

---

## Contract Trading

This can include futures with a set expiry date, perpetual swaps with funding payments, and inverse futures or swaps.
Information about the positions can be served from different endpoints depending on the exchange.
In the case that there are multiple endpoints serving different types of derivatives CCXT will default to just loading the "linear" (as oppose to the "inverse") contracts or the "swap" (as opposed to the "future") contracts.

### Positions

*contract only*

To get information about positions currently held in contract markets, use

- fetchPosition ()            // for a single market
- fetchPositions ()           // for all positions
- fetchAccountPositions ()    // TODO
- fetchPositionHistory ()     // for single historical position
- fetchPositionsHistory ()     // for historical positions


Parameters

- **symbol** (String) *required* Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A [position structure](#position-structure)


Parameters

- **symbols** (\[String\]) Unified CCXT market symbols, do not set to retrieve all positions (e.g. `["BTC/USDT:USDT"]`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [position structures](#position-structure)


Parameters

- **symbol** (\[String\]) Unified CCXT market symbols, do not set to retrieve all positions (e.g. `["BTC/USDT:USDT"]`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve positions for (e.g. `1646940314000`)
- **limit** (Integer) The number of [position structures](#position-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [position structures](#position-structure)

#### Position Structure

Positions allow you to borrow money from an exchange to go long or short on an market. Some exchanges require you to pay a funding fee to keep the position open.

When you go long on a position you are betting that the price will be higher in the future and that the price will never be less than the `liquidationPrice`.

As the price of the underlying index changes so does the unrealisedPnl and as a consequence the amount of collateral you have left in the position (since you can only close it at market price or worse). At some price you will have zero collateral left, this is called the "bust" or "zero" price. Beyond this point, if the price goes in the opposite direction far enough, the collateral of the position will drop below the `maintenanceMargin`. The maintenanceMargin acts as a safety buffer between your position and negative collateral, a scenario where the exchange incurs losses on your behalf. To protect itself the exchange will swiftly liquidate your position if and when this happens. Even if the price returns back above the liquidationPrice you will not get your money back since the exchange sold all the `contracts` you bought at market. In other words the maintenanceMargin is a hidden fee to borrow money.

It is recommended to use the `maintenanceMargin` and `initialMargin` instead of the `maintenanceMarginPercentage` and `initialMarginPercentage` since these tend to be more accurate. The maintenanceMargin might be calculated from other factors outside of the maintenanceMarginPercentage including the funding rate and taker fees, for example on [kucoin](https://futures.kucoin.com/contract/detail).

An inverse contract will allow you to go long or short on BTC/USD by putting up BTC as collateral. Our API for inverse contracts is the same as for linear contracts. The amounts in an inverse contracts are quoted as if they were traded USD/BTC, however the price is still quoted terms of BTC/USD.  The formula for the profit and loss of a inverse contract is `(1/markPrice - 1/price) * contracts`. The profit and loss and collateral will now be quoted in BTC, and the number of contracts are quoted in USD.

#### Closing Positions

*contract only*

To quickly close open positions with a market order, use

- closePosition (symbol)               // for a single market
- closeAllPositions (symbol)           // for all positions


Parameters

- **symbol** (String) *required* Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **side** *optional* a string literal for the direction of your order. Some exchanges require it.
  **Unified sides:**
  - `buy` give quote currency and receive base currency; for example, buying `BTC/USD` means that you will receive bitcoins for your dollars.
  - `sell` give base currency and receive quote currency; for example, buying `BTC/USD` means that you will receive dollars for your bitcoins.
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An [order structure](#order-structure)


Parameters
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A list of [order structures](#order-structure)


### Position Mode

*margin and contract only*

Method used for setting position mode:


Parameters

- **hedged** (String) *required* hedged-mode value:
    - `true` - sets to **hedged** mode
    - `false` - sets to **one-way** mode
- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint

Method used for fetching position mode:


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint

Returns



#### Liquidation Price

It is the price at which the `initialMargin + unrealized = collateral = maintenanceMargin`. The price has gone in the opposite direction of your position to the point where the is only maintenanceMargin collateral left and if it goes any further the position will have negative collateral.


### Funding History

*contract only*

Perpetual swap (also known as perpetual future) contracts maintain a market price that mirrors the price of the asset they are based on because funding fees are exchanged between traders who hold positions in perpetual swap markets.

If the contract is being traded at a price that is higher than the price of the asset they represent, then traders in long positions pay a funding fee to traders in short positions at specific times of day, which encourages more traders to enter short positions prior to these times.

If the contract is being traded at a price that is lower than the price of the asset they represent, then traders in short positions pay a funding fee to traders in long positions at specific times of day, which encourages more traders to enter long positions prior to these times.

These fees are usually exchanged between traders with no commission going to the exchange

The `fetchFundingHistory` method can be used to retrieve an accounts history of funding fees paid or received


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve funding history for (e.g. `1646940314000`)
- **limit** (Integer) The number of [funding history structures](#funding-history-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [funding history structures](#funding-history-structure)

#### Funding History Structure



### Conversion

The `fetchConvertQuote` method can be used to retrieve a quote that can be used for a conversion trade.
The quote usually needs to be used within a certain timeframe specified by the exchange for the convert trade to execute successfully.


Parameters

- **fromCode** (String) *required* The unified currency code for the currency to convert from (e.g. `"USDT"`)
- **toCode** (String) *required* The unified currency code for the currency to be converted into (e.g. `"USDC"`)
- **amount** (Float) Amount to convert in units of the from currency (e.g. `20.0`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"toAmount": 2.9722}`)

Returns

- A [conversion structure](#conversion-structure)

The `createConvertTrade` method can be used to create a conversion trade order using the id retrieved from fetchConvertQuote.
The quote usually needs to be used within a certain timeframe specified by the exchange for the convert trade to execute successfully.


Parameters

- **id** (String) *required* Conversion quote id (e.g. `1645807945000`)
- **fromCode** (String) *required* The unified currency code for the currency to convert from (e.g. `"USDT"`)
- **toCode** (String) *required* The unified currency code for the currency to be converted into (e.g. `"USDC"`)
- **amount** (Float) Amount to convert in units of the from currency (e.g. `20.0`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"toAmount": 2.9722}`)

Returns

- A [conversion structure](#conversion-structure)

The `fetchConvertTrade` method can be used to fetch a specific conversion trade using the trades id.


Parameters

- **id** (String) *required* Conversion trade id (e.g. `"80794187SDHJ25"`)
- **code** (String) The unified currency code of the conversion trade (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"toAmount": 2.9722}`)

Returns

- A [conversion structure](#conversion-structure)

The `fetchConvertTradeHistory` method can be used to fetch the conversion history for a specified currency code.


Parameters

- **code** (String) The unified currency code to fetch conversion trade history for (e.g. `"USDT"`)
- **since** (Integer) Timestamp of the earliest conversion (e.g. `1645807945000`)
- **limit** (Integer) The maximum number of conversion structures to retrieve (e.g. `10`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"toAmount": 2.9722}`)

Returns

- An array of [conversion structures](#conversion-structure)

#### Conversion Structure


## Auto De Leverage

*contract only*

Use the `fetchPositionADLRank` or `fetchPositionsADLRank` methods to get the private details of a positions auto de leverage rank from the exchange.


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "futures"}`)

Returns

- An [auto de leverage structure](#auto-de-leverage)


Parameters

- **symbols** (\[String\]) A list of unified CCXT symbols (e.g. `[ "BTC/USDT:USDT" ]`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "futures"}`)

Returns

- A list of [auto de leverage structures](#auto-de-leverage)

### Auto De Leverage Stucture



## Proxy

In some specific cases you may want a proxy, when:
- Exchange is not available in your location
- Your IP is forbidden by exchange
- You experience random restriction by exchange, like [DDoS protection by Cloudflare](#ddos-protection-by-cloudflare-incapsula)

However, beware that each added intermediary might add some latency to requests.

**Note for Go users:** After setting any proxy property, you must call `UpdateProxySettings()` to apply the changes:
However be aware that each added intermediary might add some latency to requests.

### Supported proxy types
CCXT supports the following proxy types (note, each of them also have [callback support](#using-proxy-callbacks)):

#### proxyUrl

This property prepends an url to API requests. It might be useful for simple redirection or [bypassing CORS browser restriction](#cors-access-control-allow-origin).
```
ex = ccxt.binance();
ex.proxyUrl = 'YOUR_PROXY_URL';
```
while 'YOUR_PROXY_URL' could be like (use the slash accordingly):
- `https://cors-anywhere.herokuapp.com/`
- `http://127.0.0.1:8080/`
- `http://your-website.com/sample-script.php?url=`
- etc

So requests will be made to i.e. `https://cors-anywhere.herokuapp.com/https://exchange.xyz/api/endpoint`. ( You can also have a small proxy script running on your device/webserver to use it in `.proxyUrl` -  "sample-local-proxy-server" in [examples folder](https://github.com/ccxt/ccxt/tree/master/examples)). To customize the target url, you can also override `urlEncoderForProxyUrl` method of instance.

This approach works **only for REST** requests, but not for websocket connections. ((_How to test if your proxy works_))[#test-if-your-proxy-works]

#### httpProxy and httpsProxy
To set a real http(s) proxy for your scripts, you need to have an access to a remote [http or https proxy](https://stackoverflow.com/q/10440690/2377343), so calls will be made directly to the target exchange, tunneled through your proxy server:
```
ex.httpProxy = 'http://1.2.3.4:8080/';
// or
ex.httpsProxy = 'http://1.2.3.4:8080/';
```
This approach only affects **non-websocket** requests of ccxt. To route CCXT's WebSockets connections through proxy, you need to specifically set `wsProxy` (or `wssProxy`) property, in addition to the `httpProxy` (or `httpsProxy`), so your script should be like:
```
ex.httpProxy = 'http://1.2.3.4:8080/';
ex.wsProxy   = 'http://1.2.3.4:8080/';
```
So, both connections (HTTP & WS) would go through proxies.
((_How to test if your proxy works_))[#test-if-your-proxy-works]


#### socksProxy
You can also use [socks proxy](https://www.google.com/search?q=what+is+socks+proxy) with the following format:
```
// from protocols: socks, socks5, socks5h
ex.socksProxy = 'socks5://1.2.3.4:8080/';
ex.wsSocksProxy = 'socks://1.2.3.4:8080/';
```
((_How to test if your proxy works_))[#test-if-your-proxy-works]

#### Test if your proxy works
After setting any of the above listed proxy properties in your ccxt snippet, you can test whether it works by pinging some IP echoing websites - check a "proxy-usage" file in [examples](https://github.com/ccxt/ccxt/blob/master/examples/).

#### using proxy callbacks
**Instead of setting a property, you can also use callbacks `proxyUrlCallback, http(s)ProxyCallback, socksProxyCallback`:
```
myEx.proxyUrlCallback = function (url, method, headers, body) { ... return 'http://1.2.3.4/'; }
```

### extra proxy related details

#### userAgent

If you need for special cases, you can override `userAgent` property like:
```
exchange.userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'
```

#### custom proxy agents

Depending your programming language, you can set custom proxy agents.
 - For JS, see [this example](
https://github.com/ccxt/ccxt/blob/master/examples/js/custom-proxy-agent-for-js.js)
 - For Python, see the following examples: [proxies-for-synchronous-python](
https://github.com/ccxt/ccxt/blob/master/examples/py/proxies-for-synchronous-python.py), [proxy-asyncio-aiohttp-python-3](
https://github.com/ccxt/ccxt/blob/master/examples/py/proxy-asyncio-aiohttp-python-3.py), [proxy-asyncio-aiohttp-socks](
https://github.com/ccxt/ccxt/blob/master/examples/py/proxy-asyncio-aiohttp-socks.py), [proxy-sync-python-requests-2-and-3](
https://github.com/ccxt/ccxt/blob/master/examples/py/proxy-sync-python-requests-2-and-3.py)

#### CORS (Access-Control-Allow-Origin)

CORS (known as [Cross-Origin Resource Sharing](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing)) affects mostly browsers and is the cause of the well-know warning `No 'Access-Control-Allow-Origin' header is present on the requested resource`. It happens when a script (running in a browser) makes a request to a 3rd party domain (by default such requests are blocked, unless the target domain explicitly allows it).
So, in such cases you will need to communicate with a "CORS" proxy, which would redirect requests (as opposed to direct browser-side request) to the target exchange. To set a CORS proxy, you can run [sample-local-proxy-server-with-cors](https://github.com/ccxt/ccxt/blob/master/examples/) example file and in ccxt set the [`.proxyUrl`](#proxyUrl) property to route requests through cors/proxy server.

## String Math

Some users might want to control how CCXT handles arithmetic operations. Even though it uses numeric types by default, users can switch to fixed-point math using string types. This can be done by:



```python
ex = ccxt.coinbase()
ex.number = str  # str | float
```


