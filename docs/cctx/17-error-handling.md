# Error Handling

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 187 lines · ~2,963 tokens · 11,852 chars
> **See also**: [Index](./README.md)

---

- [Retry Mechanism](#retry-mechanism)
- [Exception Hierarchy](#exception-hierarchy)
- [ExchangeError](#exchangeerror)
- [OperationFailed](#operationfailed)
- [DDoSProtection](#ddosprotection)
- [RateLimitExceeded](#ratelimitexceeded)
- [RequestTimeout](#requesttimeout)
- [RequestTimeout](#requesttimeout)
- [ExchangeNotAvailable](#exchangenotavailable)
- [InvalidNonce](#invalidnonce)

The error handling with CCXT is done with the exception mechanism that is natively available with all languages.

To handle the errors you should add a `try` block around the call to a unified method and catch the exceptions like you would normally do with your language:


```python
# try to call a unified method
try:
    response = await exchange.fetch_order_book('ETH/BTC')
    print(response)
except ccxt.NetworkError as e:
    print(exchange.id, 'fetch_order_book failed due to a network error:', str(e))
    # retry or whatever
except ccxt.ExchangeError as e:
    print(exchange.id, 'fetch_order_book failed due to exchange error:', str(e))
    # retry or whatever
except Exception as e:
    print(exchange.id, 'fetch_order_book failed with:', str(e))
    # retry or whatever
```

For async pipelines (`fetchTickerAsync`, etc.), `CompletableFuture` wraps
thrown errors in `CompletionException`. Use `Helpers.unwrap()` inside
`.exceptionally(...)` to peel the wrapper and pattern-match the underlying
ccxt error:


## Retry Mechanism
When dealing with HTTP requests, it's important to understand that requests might fail for various reasons. Common causes of these failures include the server being unavailable, network instability, or temporary server issues. To handle such scenarios gracefully, CCXT provide an option to automatically retry failed requests. You can set the value of `maxRetriesOnFailure` and `maxRetriesOnFailureDelay` to configure the number of retries and the delay between retries, example:

```Python
exchange.options['maxRetriesOnFailure'] = 3 # if we get an error like the ones mentioned above we will retry up to three times per request
exchange.options['maxRetriesOnFailureDelay'] = 1000 # we will wait 1000ms (1s) between retries
```

It's important to highlight that only server/network-related issues will be part of the retry mechanism; if the user gets an error due to `InsufficientFunds` or `InvalidOrder,`  the request will not be repeated.

## Exception Hierarchy

All exceptions are derived from the base BaseError exception, which, in its turn, is defined in the ccxt library like so:



```python
class BaseError (Exception):
    pass
```

The exception inheritance hierarchy lives in this file: https://github.com/ccxt/ccxt/blob/master/ts/src/base/errorHierarchy.ts , and visually can be outlined like shown below:


The `BaseError` class is a generic root error class for all sorts of errors, including accessibility and request/response mismatch. If you don't need to catch any specific subclass of exceptions, you can just use `BaseError`, where all exception types are being caught.

From `BaseError` derives two different families of errors: `OperationFailed` and `ExchangeError` (they also have their specific sub-types, as explained below).

### OperationFailed
<a name="NetworkError" id="NetworkError"></a>

An `OperationFailed` might happen when user sends **correctly constructed & valid request** to exchange, but a non-deterministic problem occurred:
- maintenance ongoing
- internet/network connectivitiy issues
- DDoS protections
- "Server busy, try again"...

Such exceptions are temporary and re-trying the request again might be enough. However, if the error still happens, then it may indicate some persistent problem with the exchange or with your connection.

`OperationFailed` has the following sub-types: `RequestTimeout`,`DDoSProtection` (includes sub-type `RateLimitExceeded`),  `ExchangeNotAvailable`, `InvalidNonce`.


#### DDoSProtection

This exception is thrown in cases when cloud/hosting services (Cloudflare, Incapsula or etc..) limits requests from user/region/location or when the exchange API restricts user because of making abnormal requests. This exception also contains specific sub-type exception `RateLimitExceeded`, which directly means that user makes much frequent requests than tolerated by exchange API engine.

#### RequestTimeout

This exception is raised when the connection with the exchange fails or data is not fully received in a specified amount of time. This is controlled by the exchange's `.timeout` property. When a `RequestTimeout` is raised, the user doesn't know the outcome of a request (whether it was accepted by the exchange server or not).

Thus it's advised to handle this type of exception in the following manner:

- for fetching requests it is safe to retry the call
- for a request to `cancelOrder()` a user is required to retry the same call the second time. A subsequent retry to `cancelOrder()` will return one of the following possible results:
  - a request is completed successfully, meaning the order has been properly canceled now
  - an `OrderNotFound` exception is raised, which means the order was either already canceled on the first attempt or has been executed (filled and closed) in the meantime between the two attempts.
- if a request to `createOrder()` fails with a `RequestTimeout` the user should:
  - call `fetchOrders()`, `fetchOpenOrders()`, `fetchClosedOrders()` to check if the request to place the order has succeeded and the order is now open
  - if the order is not `'open'` the user should `fetchBalance()` to check if the balance has changed since the order was created on the first run and then was filled and closed by the time of the second check.

#### ExchangeNotAvailable

This type of exception is thrown when the underlying exchange is unreachable. The ccxt library also throws this error if it detects any of the following keywords in response:

  - `offline`
  - `unavailable`
  - `busy`
  - `retry`
  - `wait`
  - `maintain`
  - `maintenance`
  - `maintenancing`

#### InvalidNonce

Raised when your nonce is less than the previous nonce used with your keypair, as described in the [Authentication](#authentication) section. This type of exception is thrown in these cases (in order of precedence for checking):

  - You are not rate-limiting your requests or sending too many of them too often.
  - Your API keys are not fresh and new (have been used with some different software or script already, just always create a new keypair when you add this or that exchange).
  - The same keypair is shared across multiple instances of the exchange class (for example, in a multithreaded environment or in separate processes).
  - Your system clock is out of synch. System time should be synched with UTC in a non-DST timezone at a rate of once every ten minutes or even more frequently because of the clock drifting. **Enabling time synch in Windows is usually not enough!** You have to set it up with the OS Registry (Google *"time synch frequency"* for your OS).


### ExchangeError

In contrast to `OperationFailed`, the `ExchangeError` is mostly happening when the request is impossible to succeed (because of factors listed below), so even if you retry the same request hundreds of times, they will still fail, because the request is being made incorrectly.

Possible reasons for this exception:

  - endpoint is switched off by the exchange
  - symbol not found on the exchange
  - required parameter is missing
  - the format of parameters is incorrect
  - some problem happening on user-side that needs to be fixed

`ExchangeError` has the following sub-type exceptions:

  - `NotSupported`: when the endpoint/operation is not offered or supported by the exchange API.
  - `BadRequest`: user sends an **incorrectly** constructed request/parameter/action that is invalid/unallowed (i.e.: "invalid number", "forbidden symbol", "size beyond min/max limits", "incorrect precision", etc). Retrying would not help in this case, the request needs to be fixed/adjusted first.
  - `OperationRejected` - user sends a **correctly** constructed request (that should be accepted by the exchange in a typical case), but some deterministic factor prevents your request to succeed. For example, your current account status might not allow it (i.e. "please close existing positions before changing the leverage", "too many pending orders", "your account in wrong position/margin mode") or at the give moment symbol is not tradable (i.e. "MarketClosed") or some explained factors, where you need to take a specific action (i.e. change some setting at first, or wait till specific moment). So, once again: [**OperationFailed**](#operationfailed) can be blindly re-tried and should success, while `OperationRejected` is a failure that depends on specific exact factors that need to be considered, before request can be retried.
  - `AuthenticationError`: when an exchange requires one of the API credentials that you've missed to specify, or when there's a mistake in the keypair or an outdated nonce. Most of the time you need `apiKey` and `secret`, sometimes you also need `uid` and/or `password` if exchange API requires it.
  - `PermissionDenied`: when there's no access for specified action or insufficient permissions on the specified `apiKey`.
  - `InsufficientFunds`: when you don't have enough currency on your account balance to place an order.
  - `InvalidAddress`: when encountering a bad funding address or a funding address shorter than `.minFundingAddressLength` (10 characters by default) in a call to `fetchDepositAddress`, `createDepositAddress` or `withdraw`.
  - `InvalidOrder`: the base class for all exceptions related to the unified order API.
  - `OrderNotFound`: when you are trying to fetch or cancel a non-existent order.

### Handling timestamp errors

Users may occasionally encounter errors such as:

> "Timestamp for this request is outside of the recvWindow."
> "Invalid request, please check your server timestamp or recv_window param."
> "Timestamp for this request was 1000ms ahead of the server's time."

These issues can arise for several reasons:

#### 1. System Clock Desynchronization
Your device’s system clock may not be properly synchronized with global time standards, leading to timestamp discrepancies.
To resolve this, ensure your system clock is accurate to the millisecond. This should not be a one-time adjustment — configure your operating system to synchronize time periodically (e.g., every hour) to maintain accuracy.

#### 2. Network Latency or Delayed Requests
If your device’s clock is correctly synchronized but network delays cause requests to take longer than the exchange’s accepted window (commonly around `5` seconds, though this varies by exchange), your request may be rejected.


If the issue persists, you can compare your local timestamp with the exchange’s server time to diagnose discrepancies:

```
for i in range(0, 20):
    local_time = exchange.milliseconds()
    exchange_time = await exchange.fetch_time()
    print(exchange_time - local_time)
```

####  Adjusting Exchange Options

If you continue to experience timestamp errors after verifying synchronization, you can modify certain exchange options to help mitigate the issue.

A) `exchange.options['adjustForTimeDifference'] = True`
or increase window to eg. 10 seconds (only if an exchange supports it, search this keyword in target [exchange file](https://github.com/ccxt/ccxt/tree/master/ts/src)):
B) `exchange.options['recvWindow'] = 10000`


For additional troubleshooting steps, community discussions, and related timestamp/`recvWindow` issues, refer to the following GitHub threads:

- [CCXT Issue #773](https://github.com/ccxt/ccxt/issues/773)
- [CCXT Issue #850](https://github.com/ccxt/ccxt/issues/850)
- [CCXT Issue #936](https://github.com/ccxt/ccxt/issues/936)
