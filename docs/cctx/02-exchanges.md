# Exchanges

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 317 lines · ~5,031 tokens · 20,124 chars
> **See also**: [Index](./README.md)

---

- [Instantiation](#instantiation)
- [Exchange Structure](#exchange-structure)
- [Rate Limit](#rate-limit)
The CCXT library currently supports the following 105 cryptocurrency exchange markets and trading APIs:


_The CCXT library supports **105** cryptocurrency exchanges. Below is the compact list of exchange IDs — instantiate with `ccxt.<id>()`, e.g. `ccxt.binance()`._

`aftermath` · `alpaca` · `apex` · `ascendex` · `aster` · `backpack`
`bequant` · `bigone` · `binance` · `binancecoinm` · `binanceus` · `binanceusdm`
`bingx` · `bit2c` · `bitbank` · `bitbns` · `bitfinex` · `bitflyer`
`bitget` · `bithumb` · `bitmart` · `bitmex` · `bitopro` · `bitrue`
`bitso` · `bitstamp` · `bitteam` · `bittrade` · `bitvavo` · `blockchaincom`
`blofin` · `btcbox` · `btcmarkets` · `btcturk` · `bullish` · `bybit`
`bybiteu` · `bydfi` · `cex` · `coinbase` · `coinbaseexchange` · `coinbaseinternational`
`coincheck` · `coinex` · `coinmate` · `coinmetro` · `coinone` · `coinsph`
`coinspot` · `cryptocom` · `cryptomus` · `deepcoin` · `delta` · `deribit`
`derive` · `digifinex` · `dydx` · `exmo` · `extended` · `fmfwio`
`foxbit` · `gate` · `gemini` · `grvt` · `hashkey` · `hibachi`
`hitbtc` · `hollaex` · `htx` · `hyperliquid` · `independentreserve` · `indodax`
`kraken` · `krakenfutures` · `kucoin` · `kucoinfutures` · `latoken` · `lbank`
`lighter` · `luno` · `mercado` · `mexc` · `modetrade` · `myokx`
`ndax` · `novadax` · `okx` · `okxus` · `onetrading` · `p2b`
`pacifica` · `paradex` · `paymium` · `phemex` · `poloniex` · `tokocrypto`
`toobit` · `upbit` · `weex` · `whitebit` · `woo` · `woofipro`
`xt` · `zaif` · `zebpay`

<!--- end list -->


Besides making basic market and limit orders, some exchanges offer margin trading (leverage), various derivatives (like futures contracts and options) and also have [dark pools](https://en.wikipedia.org/wiki/Dark_pool), [OTC](https://en.wikipedia.org/wiki/Over-the-counter_(finance)) (over-the-counter trading), merchant APIs and much more.

## Instantiation

To connect to an exchange and start trading you need to instantiate an exchange class from ccxt library.

To get the full list of ids of supported exchanges programmatically:



```python
import ccxt
print (ccxt.exchanges)
```

An exchange can be instantiated like shown in the examples below:



```python
import ccxt
exchange = ccxt.okcoin () # default id
okcoin1 = ccxt.okcoin ({ 'id': 'okcoin1' })
okcoin2 = ccxt.okcoin ({ 'id': 'okcoin2' })
id = 'btcchina'
btcchina = eval ('ccxt.%s ()' % id)
coinbaseexchange = getattr (ccxt, 'coinbaseexchange') ()

# from variable id
exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
})
```

The ccxt library in PHP uses builtin UTC/GMT time functions, therefore you are required to set date.timezone in your php.ini or call [date_default_timezone_set()](http://php.net/manual/en/function.date-default-timezone-set.php) function before using the PHP version of the library. The recommended timezone setting is `"UTC"`.


### Features

Major exchanges have the `.features` property available, where you can see what methods and functionalities are supported for each market-type (if any method is set to `null/undefined` it means method is "not supported" by the exchange)

*this feature is currently a work in progress and might be incomplete, feel free to report any issues you find in it*



### Overriding Exchange Properties Upon Instantiation

Most of exchange properties as well as specific options can be overrided upon exchange class instantiation or afterwards, like shown below:






```python
exchange = ccxt.binance ({
    'rateLimit': 10000,  # unified exchange property
    'headers': {
        'YOUR_CUSTOM_HTTP_HEADER': 'YOUR_CUSTOM_VALUE',
    },
    'options': {
        'adjustForTimeDifference': True,  # exchange-specific option
    }
})
exchange.options['adjustForTimeDifference'] = False
```


### Overriding Exchange Methods

In all CCXT-supported languages, you can override instance methods during runtime:




```python
ex = ccxt.binance()
def my_overload(symbol, params = {}):
    # your codes go here

ex.fetch_ticker = my_overload
print(ex.fetch_ticker('BTC/USDT'))
```




### Testnets And Sandbox Environments

Some exchanges also offer separate APIs for testing purposes that allows developers to trade virtual money for free and test out their ideas. Those APIs are called _"testnets", "sandboxes" or "staging environments"_ (with virtual testing assets) as opposed to _"mainnets" and "production environments"_ (with real assets). Most often a sandboxed API is a clone of a production API, so, it's literally the same API, except for the URL to the exchange server.

CCXT unifies that aspect and allows the user to switch to the exchange's sandbox (if supported by the underlying exchange).
To switch to the sandbox one has to call the `exchange.setSandboxMode (true)` or `exchange.set_sandbox_mode(true)` **immediately after creating the exchange before any other call**!





```python
exchange = ccxt.binance(config)
exchange.set_sandbox_mode(True)  # enable sandbox mode
```



- The `exchange.setSandboxMode (true) / exchange.set_sandbox_mode (True)` has to be your first call immediately after creating the exchange (before any other calls)
- To obtain the [API keys](#authentication) to the sandbox the user has to register with the sandbox website of the exchange in question and create a sandbox keypair
- **Sandbox keys are not interchangeable with production keys!**

## Exchange Structure

Every exchange has a set of properties and methods, most of which you can override by passing an associative array of params to an exchange constructor. You can also make a subclass and override everything.

Here's an overview of generic exchange properties with values added for example:


### Exchange Properties

Below is a detailed description of each of the base exchange properties:

- `id`: Each exchange has a default id. The id is not used for anything, it's a string literal for user-land exchange instance identification purposes. You can have multiple links to the same exchange and differentiate them by ids. Default ids are all lowercase and correspond to exchange names.

- `name`: This is a string literal containing the human-readable exchange name.

- `countries`: An array of string literals of 2-symbol ISO country codes, where the exchange is operating from.

- `urls['api']`: The single string literal base URL for API calls or an associative array of separate URLs for private and public APIs.

- `urls['www']`: The main HTTP website URL.

- `urls['doc']`: A single string URL link to original documentation for exchange API on their website or an array of links to docs.

- `version`: A string literal containing version identifier for current exchange API. The ccxt library will append this version string to the API Base URL upon each request. You don't have to modify it, unless you are implementing a new exchange API. The version identifier is a usually a numeric string starting with a letter 'v' in some cases, like v1.1. Do not override it unless you are implementing your own new crypto exchange class.

- `api`: An associative array containing a definition of all API endpoints exposed by a crypto exchange. The API definition is used by ccxt to automatically construct callable instance methods for each available endpoint.

- `has`: This is an associative array of exchange capabilities (e.g `fetchTickers`, `fetchOHLCV` or `CORS`).

- `timeframes`: An associative array of timeframes, supported by the fetchOHLCV method of the exchange. This is only populated when `has['fetchOHLCV']` property is true.

- `timeout`: A timeout in milliseconds for a request-response roundtrip (default timeout is 10000 ms = 10 seconds). If the response is not received in that time, the library will throw an `RequestTimeout` exception. You can leave the default timeout value or set it to a reasonable value. Hanging forever with no timeout is not your option, for sure. You don't have to override this option in general case.

- `rateLimit`: The rate limit in milliseconds. This value represents the number of milliseconds to wait between consecutive requests to stay within the exchange's rate limits. For example, if `rateLimit` is 1000, it means 1 request per second is allowed. The built-in rate-limiter is enabled by default and can be turned off by setting the `enableRateLimit` property to false.

- `enableRateLimit`: A boolean (true/false) value that enables the built-in rate limiter and throttles consecutive requests. This setting is `true` (enabled) by default. **The user is required to implement own [rate limiting](#rate-limit) or leave the built-in rate limiter enabled to avoid being banned from the exchange**.

- `userAgent`: An object to set HTTP User-Agent header to. The ccxt library will set its User-Agent by default. Some exchanges may not like it. If you are having difficulties getting a reply from an exchange and want to turn User-Agent off or use the default one, set this value to false, undefined, or an empty string. The value of `userAgent` may be overrided by HTTP `headers` property below.

- `headers`: An associative array of HTTP headers and their values. Default value is empty `{}`. All headers will be prepended to all requests. If the `User-Agent` header is set within `headers`, it will override whatever value is set in the `userAgent` property above.

- `verbose`: A boolean flag indicating whether to log HTTP requests to stdout (verbose flag is false by default). Python people have an alternative way of DEBUG logging with a standard pythonic logger, which is enabled by adding these two lines to the beginning of their code:
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```
- `returnResponseHeaders`: If set to `true`, the HTTP response headers from the exchange will be included in the `responseHeaders` property inside the `info` field of the returned result for REST API calls. This can be useful for accessing metadata such as rate limit information or exchange-specific headers. By default, this is `false` and headers are not included in the response. Note: it's only supported when response is an object and not a list or string

- `markets`: An associative array of markets indexed by common trading pairs or symbols. Markets should be loaded prior to accessing this property. Markets are unavailable until you call the `loadMarkets() / load_markets()` method on exchange instance.

- `symbols`: A non-associative array (a list) of symbols available with an exchange, sorted in alphabetical order. These are the keys of the `markets` property. Symbols are loaded and reloaded from markets. This property is a convenient shorthand for all market keys.

- `currencies`: An associative array (a dict) of currencies by codes (usually 3 or 4 letters) available with an exchange. Currencies are loaded and reloaded from markets.

- `markets_by_id`: An associative array of arrays of markets indexed by exchange-specific ids. Typically a length one array unless there are multiple markets with the same marketId. Markets should be loaded prior to accessing this property.

- `apiKey`: This is your public API key string literal. Most exchanges require [API keys setup](#api-keys-setup).

- `secret`: Your private secret API key string literal. Most exchanges require this as well together with the apiKey.

- `password`: A string literal with your password/phrase. Some exchanges require this parameter for trading, but most of them don't.

- `uid`: A unique id of your account. This can be a string literal or a number. Some exchanges also require this for trading, but most of them don't.

- `requiredCredentials`: A unified associative dictionary that shows which of the above API credentials are required for sending private API calls to the underlying exchange (an exchange may require a specific set of keys).

- `options`: An exchange-specific associative dictionary containing special keys and options that are accepted by the underlying exchange and supported in CCXT.

- `precisionMode`: The exchange decimal precision counting mode, read more about [Precision And Limits](#precision-and-limits)

- For proxies - `proxyUrl`, `httpUrl`, `httpsUrl`, `socksProxy`, `wsProxy`, `wssProxy`, `wsSocksProxy` : An url of specific proxy. See the [Proxy](#proxy) section for more details.

See this section on [Overriding exchange properties](#overriding-exchange-properties-upon-instantiation).

#### Exchange Metadata

- `has`: An assoc-array containing flags for exchange capabilities, including the following:


    The meaning of each flag showing availability of this or that method is:

    - a value of `undefined` / `None` / `null` means the method is not currently implemented in ccxt (either ccxt has not unified it yet or the method isn't natively available from the exchange API)
    - boolean `false` specifically means that the endpoint isn't natively available from the exchange API
    - boolean `true` means the endpoint is natively available from the exchange API and unified in the ccxt library
    - `'emulated'` string means the endpoint isn't natively available from the exchange API but reconstructed (as much as possible) by the ccxt library from other available true-methods

    For a complete list of all exchanges and their supported methods, please, refer to this example: https://github.com/ccxt/ccxt/blob/master/examples/js/exchange-capabilities.js

## Rate Limit

Exchanges usually impose what is called a *rate limit*. Exchanges will remember and track your user credentials and your IP address and will not allow you to query the API too frequently. They balance their load and control traffic congestion to protect API servers from (D)DoS and misuse.

**WARNING: Stay under the rate limit to avoid ban!**

Most exchanges allow **up to 1 or 2 requests per second**. Exchanges may temporarily restrict your access to their API or ban you for some period of time if you are too aggressive with your requests.

**The `exchange.rateLimit` property is set to a safe default which is sub-optimal. Some exchanges may have varying rate limits for different endpoints. It is up to the user to tweak `rateLimit` according to application-specific purposes.**

The CCXT library has built-in experimental rate-limiter algorithms that will do the necessary throttling in background transparently to the user. **WARNING: users are responsible for at least some type of rate-limiting: either by implementing a custom algorithm or by doing it with the built-in rate-limiter.**

CCXT has the following built-in rate-limiting algorithms:

- **Leaky Bucket (default)**: Works by queueing requests and releasing them at a steady, fixed rate. Bursts of requests are smoothed out over time rather than executed immediately, which helps prevent hitting exchange rate limits while still allowing short spikes in activity to be handled gracefully.
- **Window-Based (optional)**:  If the user provides the `{ 'rateLimiterAlgorithm': 'rollingWindow' }` option, ccxt switches from the leaky bucket model to a window-based rate limiter (the size of the window can be customized by providing `rollingWindowSize: X0000`, CCXT uses 60s as the default windowSize). A window-based limiter enforces a maximum number of requests within a fixed time window (for example, N requests per X milliseconds). Once the limit is reached, further requests are delayed until the current window expires.

You can turn on/off the built-in rate-limiter with `.enableRateLimit` property, like so:




```python

# enable built-in rate limiting upon instantiation of the exchange
exchange = ccxt.bitfinex({
    # 'enableRateLimit': True,  # enabled by default
})

# or switch the built-in rate-limiter on or off later after instantiation
exchange.enableRateLimit = True  # enable
exchange.enableRateLimit = False  # disable
```



In case your calls hit a rate limit or get nonce errors, the ccxt library will throw an `InvalidNonce` exception, or, in some cases, one of the following types:

- `DDoSProtection`
- `ExchangeNotAvailable`
- `ExchangeError`
- `InvalidNonce`

A later retry is usually enough to handle that.

### Notes On Rate Limiter
#### One Rate Limiter Per Each Exchange Instance

The rate limiter is a property of the exchange instance, in other words, each exchange instance has its own rate limiter that is not aware of the other instances. In many cases the user should reuse the same exchange instance throughout the program. Do not use multiple instances of the same exchange with the same API keypair from the same IP address.


Reuse the exchange instance as much as possible as shown below:


Since the rate limiter belongs to the exchange instance, destroying the exchange instance will destroy the rate limiter as well. Among the most common pitfalls with the rate limiting is creating and dropping the exchange instance over and over again. If in your program you are creating and destroying the exchange instance (say, inside a function that is called multiple times), then you are effectively resetting the rate limiter over and over and that will eventually break the rate limits. If you are recreating the exchange instance every time instead of reusing it, CCXT will try to load the markets every time. Therefore, you will force-load the markets over and over as explained in the [Loading Markets](#loading-markets) section. Abusing the markets endpoint will eventually break the rate limiter as well.


Do not break this rule unless you really understand the inner workings of the rate-limiter and you are 100% sure you know what you're doing. In order to stay safe always reuse the exchange instance throughout your functions and methods callchain like shown below:


### DDoS Protection By Cloudflare / Incapsula

Some exchanges are [DDoS](https://en.wikipedia.org/wiki/Denial-of-service_attack)-protected by [Cloudflare](https://www.cloudflare.com) or [Incapsula](https://www.incapsula.com). Your IP can get temporarily blocked during periods of high load. Sometimes they even restrict whole countries and regions. In that case their servers usually return a page that states a HTTP 40x error or runs an AJAX test of your browser / captcha test and delays the reload of the page for several seconds. Then your browser/fingerprint is granted access temporarily and gets added to a whitelist or receives a HTTP cookie for further use.

The most common symptoms for a DDoS protection problem, rate-limiting problem or for a location-based filtering issue:
- Getting `RequestTimeout` exceptions with all types of exchange methods
- Catching `ExchangeError` or `ExchangeNotAvailable` with HTTP error codes 400, 403, 404, 429, 500, 501, 503, etc..
- Having DNS resolving issues, SSL certificate issues and low-level connectivity issues
- Getting a template HTML page instead of JSON from the exchange

If you encounter DDoS protection errors and cannot reach a particular exchange then:

- use a [proxy](#proxy) (this is less responsive, though)
- ask the exchange support to add you to a whitelist
- try an alternative IP within a different geographic region
- run your software in a distributed network of servers
- run your software in close proximity to the exchange (same country, same city, same datacenter, same server rack, same server)
- ...

## Maximum Requests capacity

In asynchronous programming, CCXT allows you to schedule an unlimited number of requests. However, there's a limit on the queue length which is by default set to 1000 concurrent requests max. If you attempt to enqueue more than that, you will encounter the error: "throttle queue is over maxCapacity".

In most cases, having so many pending tasks indicates suboptimal design, as new requests will be delayed until the existing tasks complete.

That said, users who wish to bypass this restriction can increase the default maxCapacity during instantiation as shown below:

```
ex = ccxt.binance({'options': {'maxRequestsQueue': 9999}})
```
