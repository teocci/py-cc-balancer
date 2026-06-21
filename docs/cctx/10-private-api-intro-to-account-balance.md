# Private API — intro → Account Balance

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 211 lines · ~3,043 tokens · 12,174 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [intro](#intro)
- [Authentication](#authentication)
- [Overriding The Nonce](#overriding-the-nonce)
- [Accounts](#accounts)
- [Account Balance](#account-balance)

---

- [Authentication](#authentication)
- [Sign In](#sign-in)
- [API Keys Setup](#api-keys-setup)
- [Accounts](#accounts)
- [Account Balance](#account-balance)
- [Orders](#orders)
- [My Trades](#my-trades)
- [Ledger](#ledger)
- [Deposit](#deposit)
- [Withdrawal](#withdrawal)
- [Deposit Addresses](#deposit-addresses)
- [Transfers](#transfers)
- [Fees](#fees)
- [Borrow Interest](#borrow-interest)
- [Borrow And Repay Margin](#borrow-and-repay-margin)
- [Margin](#margin)
- [Margin Mode](#margin-mode)
- [Leverage](#leverage)
- [Positions](#positions)
- [Funding History](#funding-history)
- [Conversion](#conversion)
- [Auto De Leverage](#auto-de-leverage)

In order to be able to access your user account, perform algorithmic trading by placing market and limit orders, query balances, deposit and withdraw funds and so on, you need to obtain your API keys for authentication from each exchange you want to trade with. They usually have it available on a separate tab or page within your user account settings. API keys are exchange-specific and cannnot be interchanged under any circumstances.

The exchanges' private APIs will usually allow the following types of interaction:

- the current state of the user's account balance can be obtained with the `fetchBalance()` method as described in the [Account Balance](#account-balance) section
- the user can place and cancel orders with `createOrder()`, `cancelOrder()`, as well as fetch current open orders and the past order history with methods like `fetchOrder`, `fetchOrders()`, `fetchOpenOrder()`, `fetchOpenOrders()`, `fetchCanceledOrders`, `fetchClosedOrder`, `fetchClosedOrders`, as described in the section on [Orders](#orders)
- the user can query the history of past trades executed with their account using `fetchMyTrades`, as described in the [My Trades](#my-trades) section, also see [How Orders Are Related To Trades](#how-orders-are-related-to-trades)
- the user can query their positions with `fetchPositions()` and `fetchPosition()` as described in the [Positions](#positions) section
- the user can fetch the history of their transactions (on-chain _transactions_ which are either _deposits_ to the exchange account or _withdrawals_ from the exchange account) with `fetchTransactions()`, or with `fetchDeposit()`, `fetchDeposits()` `fetchWithdrawal()`, and `fetchWithdrawals()` separately, depending on what is available from the exchange API
- if the exchange API provides a ledger endpoint, the user can fetch a history of all money movements that somehow affected the balance, with `fetchLedger` that will return all accounting ledger entries such as trades, deposits, withdrawals, internal transfers between accounts, rebates, bonuses, fees, staking profits and so on, as described in the [Ledger](#ledger) section.

## Authentication

Authentication with all exchanges is handled automatically if provided with proper API keys. The process of authentication usually goes through the following pattern:

1. Generate new nonce. A nonce is an integer, often a Unix Timestamp in seconds or milliseconds (since epoch January 1, 1970). The nonce should be unique to a particular request and constantly increasing, so that no two requests share the same nonce. Each next request should have greater nonce than the previous request. **The default nonce is a 32-bit Unix Timestamp in seconds.**
2. Append public apiKey and nonce to other endpoint params, if any, then serialize the whole thing for signing.
3. Sign the serialized params using HMAC-SHA256/384/512 or MD5 with your secret key.
4. Append the signature in Hex or Base64 and nonce to HTTP headers or body.

This process may differ from exchange to exchange. Some exchanges may want the signature in a different encoding, some of them vary in header and body param names and formats, but the general pattern is the same for all of them.

**You should not share the same API keypair across multiple instances of an exchange running simultaneously, in separate scripts or in multiple threads. Using the same keypair from different instances simultaneously may cause all sorts of unexpected behaviour.**

**DO NOT REUSE API KEYS WITH DIFFERENT SOFTWARE! The other software will screw your nonce too high. If you get [InvalidNonce](#invalid-nonce) errors – make sure to generate a fresh new keypair first and foremost.**

The authentication is already handled for you, so you don't need to perform any of those steps manually unless you are implementing a new exchange class. The only thing you need for trading is the actual API key pair.

### API Keys Setup

#### Required Credentials

The API credentials usually include the following:

- `apiKey`. This is your public API Key and/or Token. This part is *non-secret*, it is included in your request header or body and sent over HTTPS in open text to identify your request. It is often a string in Hex or Base64 encoding or an UUID identifier.
- `secret`. This is your private key. Keep it secret, don't tell it to anybody. It is used to sign your requests locally before sending them to exchanges. The secret key does not get sent over the internet in the request-response process and should not be published or emailed. It is used together with the nonce to generate a cryptographically strong signature. That signature is sent with your public key to authenticate your identity. Each request has a unique nonce and therefore a unique cryptographic signature.
- `uid`. Some exchanges (not all of them) also generate a user id or *uid* for short. It can be a string or numeric literal. You should set it, if that is explicitly required by your exchange. See [their docs](#exchanges) for details.
- `password`. Some exchanges (not all of them) also require your password/phrase for trading. You should set this string, if that is explicitly required by your exchange. See [their docs](#exchanges) for details.

In order to create API keys find the API tab or button in your user settings on the exchange website. Then create your keys and copy-paste them to your config file. Your config file permissions should be set appropriately, unreadable to anyone except the owner.

**Remember to keep your apiKey and secret key safe from unauthorized use, do not send or tell it to anybody. A leak of the secret key or a breach in security can cost you a fund loss.**

#### Credential Validation

For checking if the user has supplied all the required credentials the `Exchange` base class has a method called `exchange.checkRequiredCredentials()` or `exchange.check_required_credentials()`. Calling that method will throw an `AuthenticationError`, if some of the credentials are missing or empty. The `Exchange` base class also has  property `exchange.requiredCredentials` that allows a user to see which credentials are required for this or that exchange, as shown below:


```python
import ccxt
exchange = ccxt.coinbaseexchange()
print(exchange.requiredCredentials)  # prints required credentials
exchange.check_required_credentials()  # raises AuthenticationError
```

#### Configuring API Keys

To set up an exchange for trading just assign the API credentials to an existing exchange instance or pass them to exchange constructor upon instantiation, like so:



```python
import ccxt

# any time
bitfinex = ccxt.bitfinex ()
bitfinex.apiKey = 'YOUR_BFX_API_KEY'
bitfinex.secret = 'YOUR_BFX_SECRET'

# upon instantiation
hitbtc = ccxt.hitbtc ({
    'apiKey': 'YOUR_HITBTC_API_KEY',
    'secret': 'YOUR_HITBTC_SECRET_KEY',
})

# from variable id
exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
})
```

Note that your private requests will fail with an exception or error if you don't set up your API credentials before you start trading. To avoid character escaping **always write your credentials in single quotes**, not double quotes (`'VERY_GOOD'`, `"VERY_BAD"`).

#### API Key Permissions
When you get errors like `"Invalid API-key, IP, or permissions for action."` or `"API-key format invalid"`, then, most likely, the problem is not within ccxt, please avoid opening a new issue unless you ensure that:
1) You don't have typos, empty spaces, or quotes in your keys
2) Your current IP address (check [IPv4](https://api.ipify.org/) or [IPv6](https://api64.ipify.org/)) is added into API-KEY's whitelist (if you use proxy, consider that too)
3) You have selected the correct options in permissions list for that api-key
4) You are not accidentally mixing "testnet" api-keys or "testnet" mode in your script
5) You have checked already [reported issues](https://github.com/ccxt/ccxt/issues?q=is%3Aissue+%22Invalid+Api-Key+ID%22) about this error


#### Sign In

Some exchanges required you to sign in prior to calling private methods, which can be done using the `signIn` method


Parameters

- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"2fa": "329293"}`)

Returns

- response from the exchange

## Overriding The Nonce

**The default nonce is defined by the underlying exchange. You can override it with a milliseconds-nonce if you want to make private requests more frequently than once per second! Most exchanges will throttle your requests if you hit their rate limits, read [API docs for your exchange](https://github.com/ccxt/ccxt/wiki/Exchanges) carefully!**

In case you need to reset the nonce it is much easier to create another pair of keys for using with private APIs. Creating new keys and setting up a fresh unused keypair in your config is usually enough for that.

In some cases you are unable to create new keys due to lack of permissions or whatever. If that happens you can still override the nonce. Base market class has the following methods for convenience:

- `seconds ()`: returns a Unix Timestamp in seconds.
- `milliseconds ()`: same in milliseconds (ms = 1000 * s, thousandths of a second).
- `microseconds ()`: same in microseconds (μs = 1000 * ms, millionths of a second).

There are exchanges that confuse milliseconds with microseconds in their API docs, let's all forgive them for that, folks. You can use methods listed above to override the nonce value. If you need to use the same keypair from multiple instances simultaneously use closures or a common function to avoid nonce conflicts. In Javascript you can override the nonce by providing a `nonce` parameter to the exchange constructor or by setting it explicitly on exchange object:


In Python and PHP you can do the same by subclassing and overriding nonce function of a particular exchange class:

```python
# Python

# 1: the shortest
coinbaseexchange = ccxt.coinbaseexchange({'nonce': ccxt.Exchange.milliseconds})

# 2: custom nonce
class MyKraken(ccxt.kraken):
    n = 1
    def nonce(self):
        return self.n += 1

# 3: milliseconds nonce
class MyBitfinex(ccxt.bitfinex):
    def nonce(self):
        return self.milliseconds()

# 4: milliseconds nonce inline
hitbtc = ccxt.hitbtc({
    'nonce': lambda: int(time.time() * 1000)
})

# 5: milliseconds nonce
acx = ccxt.acx({'nonce': lambda: ccxt.Exchange.milliseconds()})
```


## Accounts

You can get all the accounts associated with a profile by using the `fetchAccounts()` method


### Accounts Structure

The `fetchAccounts()` method will return a structure like shown below:


Types of account is one of the [unified account types](####Account-Balance) or `subaccount`

## Account Balance

To query for balance and get the amount of funds available for trading or funds locked in orders, use the `fetchBalance` method:


Parameters

- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"currency": "usdt"}`)

Returns

- A [balance structure](#balance-structure)

### Balance Structure


The `timestamp` and `datetime` values may be undefined or missing if the underlying exchange does not provide them.

Some exchanges may not return full balance info. Many exchanges do not return balances for your empty or unused accounts. In that case some currencies may be missing in returned balance structure.


```python
print (exchange.fetch_balance ())
```
