# Implicit API

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 177 lines · ~3,179 tokens · 12,717 chars
> **See also**: [Index](./README.md)

---

- [API Methods / Endpoints](#api-methods--endpoints)
- [Implicit API Methods](#implicit-api-methods)
- [Public/Private API](#publicprivate-api)
- [Synchronous vs Asynchronous Calls](#synchronous-vs-asynchronous-calls)
- [Passing Parameters To API Methods](#passing-parameters-to-api-methods)

## API Methods / Endpoints

Each exchange offers a set of API methods. Each method of the API is called an *endpoint*. Endpoints are HTTP URLs for querying various types of information. All endpoints return JSON in response to client requests.

Usually, there is an endpoint for getting a list of markets from an exchange, an endpoint for retrieving an order book for a particular market, an endpoint for retrieving trade history, endpoints for placing and canceling orders, for money deposit and withdrawal, etc... Basically every kind of action you could perform within a particular exchange has a separate endpoint URL offered by the API.

Because the set of methods differs from exchange to exchange, the ccxt library implements the following:
- a public and private API for all possible URLs and methods
- a unified API supporting a subset of common methods

The endpoint URLs are predefined in the `api` property for each exchange. You don't have to override it, unless you are implementing a new exchange API (at least you should know what you're doing).

Most of exchange-specific API methods are implicit, meaning that they aren't defined explicitly anywhere in code. The library implements a declarative approach for defining implicit (non-unified) exchanges' API methods.

## Implicit API Methods

Each method of the API usually has its own endpoint. The library defines all endpoints for each particular exchange in the `.api` property. Upon exchange construction an implicit *magic* method (aka *partial function* or *closure*) will be created inside `defineRestApi()/define_rest_api()` on the exchange instance for each endpoint from the list of `.api` endpoints. This is performed for all exchanges universally. Each generated method will be accessible in both `camelCase` and `under_score` notations.

The endpoints definition is a **full list of ALL API URLs** exposed by an exchange. This list gets converted to callable methods upon exchange instantiation. Each URL in the API endpoint list gets a corresponding callable method. This is done automatically for all exchanges, therefore the ccxt library supports **all possible URLs** offered by crypto exchanges.

Each implicit method gets a unique name which is constructed from the `.api` definition. For example, a private HTTPS PUT `https://api.exchange.com/order/{id}/cancel` endpoint will have a corresponding exchange method named `.privatePutOrderIdCancel()`/`.private_put_order_id_cancel()`. A public HTTPS GET `https://api.exchange.com/market/ticker/{pair}` endpoint would result in the corresponding method named `.publicGetTickerPair()`/`.public_get_ticker_pair()`, and so on.

An implicit method takes a dictionary of parameters, sends the request to the exchange and returns an exchange-specific JSON result from the API **as is, unparsed**. To pass a parameter, add it to the dictionary explicitly under a key equal to the parameter's name. For the examples above, this would look like `.privatePutOrderIdCancel ({ id: '41987a2b-...' })` and `.publicGetTickerPair ({ pair: 'BTC/USD' })`.

The recommended way of working with exchanges is not using exchange-specific implicit methods but using the unified ccxt methods instead. The exchange-specific methods should be used as a fallback in cases when a corresponding unified method isn't available (yet).

To get a list of all available methods with an exchange instance, including implicit methods and unified methods you can simply do the following:


## Public/Private API

API URLs are often grouped into two sets of methods called a *public API* for market data and a *private API* for trading and account access. These groups of API methods are usually prefixed with a word 'public' or 'private'.

A public API is used to access market data and does not require any authentication whatsoever. Most exchanges provide market data openly to all (under their rate limit). With the ccxt library anyone can access market data out of the box without having to register with the exchanges and without setting up account keys and passwords.

Public APIs include the following:

- instruments/trading pairs
- price feeds (exchange rates)
- order books (L1, L2, L3...)
- trade history (closed orders, transactions, executions)
- tickers (spot / 24h price)
- OHLCV series for charting
- other public endpoints

The private API is mostly used for trading and for accessing account-specific private data, therefore it requires authentication. You have to get the private API keys from the exchanges. It often means registering with an exchange website and creating the API keys for your account. Most exchanges require personal information or identification. Some exchanges will only allow trading after completing the KYC verification.
Private APIs allow the following:

- manage personal account info
- query account balances
- trade by making market and limit orders
- create deposit addresses and fund accounts
- request withdrawal of fiat and crypto funds
- query personal open / closed orders
- query positions in margin/leverage trading
- get ledger history
- transfer funds between accounts
- use merchant services

Some exchanges offer the same logic under different names. For example, a public API is also often called *market data*, *basic*, *market*, *mapi*, *api*, *price*, etc... All of them mean a set of methods for accessing data available to public. A private API is also often called *trading*, *trade*, *tapi*, *exchange*, *account*, etc...

A few exchanges also expose a merchant API which allows you to create invoices and accept crypto and fiat payments from your clients. This kind of API is often called *merchant*, *wallet*, *payment*, *ecapi* (for e-commerce).

To get a list of all available methods with an exchange instance, you can simply do the following:


**contract only and margin only**

- methods in this documentation that are documented as **contract only** or **margin only** are only intended to be used for contract trading and margin trading respectively. They may work when trading in other types of markets but will most likely return irrelevant information.

## Synchronous vs Asynchronous Calls



In the JavaScript version of CCXT all methods are asynchronous and return [Promises](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) that resolve with a decoded JSON object. In CCXT we use the modern *async/await* syntax to work with Promises. If you're not familiar with that syntax, you can read more about it [here](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function).






The ccxt library supports asynchronous concurrency mode in Python 3.5+ with async/await syntax. The asynchronous Python version uses pure [asyncio](https://docs.python.org/3/library/asyncio.html) with [aiohttp](http://aiohttp.readthedocs.io). In async mode you have all the same properties and methods, but most methods are decorated with an async keyword. If you want to use async mode, you should link against the `ccxt.async_support` subpackage, like in the following example:

```python
# Python

import asyncio
import ccxt.async_support as ccxt

async def print_poloniex_ethbtc_ticker():
    poloniex = ccxt.poloniex()
    print(await poloniex.fetch_ticker('ETH/BTC'))
    await polonix.close()  # close the exchange instance when you don't need it anymore

asyncio.run(print_poloniex_ethbtc_ticker())
```


CCXT support PHP 8+ versions. The library has both synchronous and asynchronous versions. To use synchronous version, use `\ccxt` namespace (i.e. `new ccxt\binance()`) and to use asynchronous version, use `\ccxt\async` namespace (i.e. `new ccxt\async\binance()`). Asynchronous version uses [ReactPHP](https://reactphp.org/) library in the background. In async mode you have all the same properties and methods, but any networking API method should be decorated with the `\React\Async\await` keyword and your script should be in a ReactPHP wrapper:

See further examples in the `examples/php` directory; look for filenames that include the `async` word. Also, make sure you have installed the required dependencies using `composer require recoil/recoil clue/buzz-react react/event-loop recoil/react react/http`. Lastly, [this article](https://sergeyzhuk.me/2018/10/26/from-promise-to-coroutines/) provides a good introduction to the methods used here. While syntactically the change is simple (i.e., just using a `yield` keyword before relevant methods), concurrency has significant implications for the overall design of your code.


In Go every networking method is synchronous and returns a `(value, error)` pair — there is no async variant. Always check the returned `error` before using the value:



In C# every networking method is asynchronous and returns a `Task<T>` that you `await`. The unified methods use native `async`/`await`:



In Java, each exchange has its own typed subclass. Every typed method ships
**both** a blocking sync overload and a non-blocking `CompletableFuture`-returning
async overload — symmetric for REST `fetch*` / `fetch*Async` and WS `watch*` /
`watch*Async`:


The same sync/async pair applies to the pro (WebSocket) classes — `watchTicker`
blocks for one update; `watchTickerAsync` returns a `CompletableFuture<Ticker>`
that completes on the next update:



### Returned JSON Objects

All public and private API methods return raw decoded JSON objects in response from the exchanges, as is, untouched. The unified API returns JSON-decoded objects in a common format and structured uniformly across all exchanges.

## Passing Parameters To API Methods

The set of all possible API endpoints differs from exchange to exchange. Most of methods accept a single associative array (or a Python dict) of key-value parameters. The params are passed as follows:


The unified methods of exchanges might expect and will accept various `params` which affect their functionality, like:

```python
params = {'type':'margin', 'isIsolated': 'TRUE'}  # --------------┑
# params will go as the last argument to the unified method       |
#                                                                 v
binance.create_order('BTC/USDT', 'limit', 'buy', amount, price, params)
```

An exchange will not accept the params from a different exchange, they're not interchangeable. The list of accepted parameters is defined by each specific exchange.

To find which parameters can be passed to a unified method:

- either open the [exchange-specific implementation](https://github.com/ccxt/ccxt/tree/master/js) file and search for the desired function (i.e. `createOrder`) to inspect and find out the details of `params` usage
- or go to the exchange's API docs and read the list of parameters for your specific function or endpoint (i.e. `order`)

For a full list of accepted method parameters for each exchange, please consult [API docs](#exchanges).

### API Method Naming Conventions

An exchange method name is a concatenated string consisting of type (public or private), HTTP method (GET, POST, PUT, DELETE) and endpoint URL path like in the following examples:

| Method Name                  | Base API URL                   | Endpoint URL                   |
|------------------------------|--------------------------------|--------------------------------|
| publicGetIdOrderbook         | https://bitbay.net/API/Public  | {id}/orderbook                 |
| publicGetPairs               | https://bitlish.com/api        | pairs                          |
| publicGetJsonMarketTicker    | https://www.bitmarket.net      | json/{market}/ticker           |
| privateGetUserMargin         | https://bitmex.com             | user/margin                    |
| privatePostTrade             | https://btc-x.is/api           | trade                          |
| tapiCancelOrder              | https://yobit.net              | tapi/CancelOrder               |
| ...                          | ...                            | ...                            |

The ccxt library supports both camelcase notation (preferred in JavaScript) and underscore notation (preferred in Python and PHP), therefore all methods can be called in either notation or coding style in any language. Both of these notations work in JavaScript, Python and PHP:


To get a list of all available methods with an exchange instance, you can simply do the following:

