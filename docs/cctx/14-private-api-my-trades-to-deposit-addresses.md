# Private API — My Trades → Deposit Addresses

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 397 lines · ~5,229 tokens · 20,918 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [My Trades](#my-trades)
- [Ledger](#ledger)
- [Deposit](#deposit)
- [Withdrawal](#withdrawal)
- [Deposit Addresses](#deposit-addresses)

---

## My Trades


### How Orders Are Related To Trades

A trade is also often called `a fill`. Each trade is a result of order execution. Note, that orders and trades have a one-to-many relationship: an execution of one order may result in several trades. However, when one order matches another opposing order, the pair of two matching orders yields one trade. Thus, when an order matches multiple opposing orders, this yields multiple trades, one trade per each pair of matched orders.

To put it shortly, an order can contain *one or more* trades. Or, in other words, an order can be *filled* with one or more trades.

For example, an orderbook can have the following orders (whatever trading symbol or pair it is):


All specific numbers above aren't real, this is just to illustrate the way orders and trades are related in general.

A seller decides to place a sell limit order on the ask side for a price of 0.700 and an amount of 150.


As the price and amount of the incoming sell (ask) order cover more than one bid order (orders `b` and `i`), the following sequence of events usually happens within an exchange engine very quickly, but not immediately:

1. Order `b` is matched against the incoming sell because their prices intersect. Their volumes *"mutually annihilate"* each other, so, the bidder gets 100 for a price of 0.800. The seller (asker) will have their sell order partially filled by bid volume 100 for a price of 0.800. Note that for the filled part of the order the seller gets a better price than he asked for initially. He asked for 0.7 at least but got 0.8 instead which is even better for the seller. Most conventional exchanges fill orders for the best price available.

2. A trade is generated for the order `b` against the incoming sell order. That trade *"fills"* the entire order `b` and most of the sell order. One trade is generated per each pair of matched orders, whether the amount was filled completely or partially. In this example the seller amount (100) fills order `b` completely (closes the order `b`) and also fills the selling order partially (leaves it open in the orderbook).

3. Order `b` now has a status of `closed` and a filled volume of 100. It contains one trade against the selling order. The selling order has an `open` status and a filled volume of 100. It contains one trade against order `b`. Thus each order has just one fill-trade so far.

4. The incoming sell order has a filled amount of 100 and has yet to fill the remaining amount of 50 from its initial amount of 150 in total.

The intermediate state of the orderbook is now (order `b` is `closed` and is not in the orderbook anymore):


5. Order `i` is matched against the remaining part of incoming sell, because their prices intersect. The amount of buying order `i` which is 200 completely annihilates the remaining sell amount of 50. The order `i` is filled partially by 50, but the rest of its volume, namely the remaining amount of 150 will stay in the orderbook. The selling order, however, is fulfilled completely by this second match.

6. A trade is generated for the order `i` against the incoming sell order. That trade partially fills order `i`. And completes the filling of the sell order. Again, this is just one trade for a pair of matched orders.

7. Order `i` now has a status of `open`, a filled amount of 50, and a remaining amount of 150. It contains one filling trade against the selling order. The selling order has a `closed` status now and it has completely filled its total initial amount of 150. However, it contains two trades, the first against order `b` and the second against order `i`. Thus each order can have one or more filling trades, depending on how their volumes were matched by the exchange engine.

After the above sequence takes place, the updated orderbook will look like this.


Notice that the order `b` has disappeared, the selling order also isn't there. All closed and fully-filled orders disappear from the orderbook. The order `i` which was filled partially and still has a remaining volume and an `open` status, is still there.

### Personal Trades

Most of unified methods will return either a single object or a plain array (a list) of objects (trades). However, very few exchanges (if any at all) will return all trades at once. Most often their APIs `limit` output to a certain number of most recent objects. **YOU CANNOT GET ALL OBJECTS SINCE THE BEGINNING OF TIME TO THE PRESENT MOMENT IN JUST ONE CALL**. Practically, very few exchanges will tolerate or allow that.

As with all other unified methods for fetching historical data, the `fetchMyTrades` method accepts a `since` argument for [date-based pagination](#date-based-pagination). Just like with all other unified methods throughout the CCXT library, the `since` argument for `fetchMyTrades` must be an **integer timestamp in milliseconds**.

To fetch historical trades, the user will need to traverse the data in portions or "pages" of objects. Pagination often implies *"fetching portions of data one by one"* in a loop.

In many cases a `symbol` argument is required by the exchanges' APIs, therefore you have to loop over all symbols to get all your trades. If the `symbol` is missing and the exchange requires it then CCXT will throw an `ArgumentsRequired` exception to signal the requirement to the user. And then the `symbol` has to be specified. One of the approaches is to filter the relevant symbols from the list of all symbols by looking at non-zero balances as well as transactions (withdrawals and deposits). Also, the exchanges will have a limit on how far back in time you can go.

In most cases users are **required to use at least some type of [pagination](#pagination)** in order to get the expected results consistently.



```python
# fetch_my_trades(symbol=None, since=None, limit=None, params={})

if exchange.has['fetchMyTrades']:
    exchange.fetch_my_trades(symbol=None, since=None, limit=None, params={})
```

Returns ordered array `[]` of trades (most recent trade last).

#### Trade Structure

Trades denote the exchange of one currency for another, unlike [transactions](#transaction-structure), which denote a transfer of a given coin.


- The work on `'fee'` and `'fees'` info is still in progress, fee info may be missing partially or entirely, depending on the exchange capabilities.
- The `fee` currency may be different from both traded currencies (for example, an ETH/BTC order with fees in USD).
- The `cost` of the trade means `amount * price`. It is the total *quote* volume of the trade (whereas `amount` is the *base* volume). The cost field itself is there mostly for convenience and can be deduced from other fields.
- The `cost` of the trade is a _"gross"_ value. That is the value pre-fee, and the fee has to be applied afterwards.

### Trades By Order Id


```python
# fetch_order_trades(id, symbol=None, since=None, limit=None, params={})

if exchange.has['fetchOrderTrades']:
    exchange.fetch_order_trades(order_id, symbol=None, since=None, limit=None, params={})
```

## Ledger

The ledger is simply the history of changes, actions done by the user or operations that altered the user's balance in any way, that is, the history of movements of all funds from/to all accounts of the user which includes

- deposits and withdrawals (funding)
- amounts incoming and outcoming in result of a trade or an order
- trading fees
- transfers between accounts
- rebates, cashbacks and other types of events that are subject to accounting.

Data on ledger entries can be retrieved using

- `fetchLedgerEntry ()` for a ledger entry
- `fetchLedger ( code )` for multiple ledger entries of the same currency
- `fetchLedger ()` for all ledger entries


Parameters

- **id** (String) *required* Ledger entry id
- **code** (String) Unified CCXT currency code, required (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"type": "deposit"}`)

Returns

- A [ledger entry structure](#ledger-entry-structure)


Parameters

- **code** (String) Unified CCXT currency code; *required* if fetching all ledger entries for all assets at once is not supported (e.g. `"USDT"`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve withdrawals for (e.g. `1646940314000`)
- **limit** (Integer) The number of [ledger entry structures](#ledger-entry-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [ledger entry structures](#ledger-entry-structure)

### Ledger Entry Structure


#### Notes On Ledger Entry Structure

The type of the ledger entry is the type of the operation associated with it. If the amount comes due to a sell order, then it is associated with a corresponding trade type ledger entry, and the referenceId will contain associated trade id (if the exchange in question provides it). If the amount comes out due to a withdrawal, then is associated with a corresponding transaction.

- `trade`
- `transaction`
- `fee`
- `rebate`
- `cashback`
- `referral`
- `transfer`
- `airdrop`
- `whatever`
- ...

The `referenceId` field holds the id of the corresponding event that was registered by adding a new item to the ledger.

The `status` field is there to support for exchanges that include pending and canceled changes in the ledger. The ledger naturally represents the actual changes that have taken place, therefore the status is `'ok'` in most cases.

The ledger entry type can be associated with a regular trade or a funding transaction (deposit or withdrawal) or an internal `transfer` between two accounts of the same user. If the ledger entry is associated with an internal transfer, the `account` field will contain the id of the account that is being altered with the ledger entry in question. The `referenceAccount` field will contain the id of the opposite account the funds are transferred to/from, depending on the `direction` (`'in'` or `'out'`).

## Deposit

In order to deposit cryptocurrency funds to an exchange you must get an address from the exchange for the currency you want to deposit using `fetchDepositAddress`. You can then call the `withdraw` method with the specified currency and address.

To deposit fiat currency on an exchange you can use the `deposit` method with data retrieved from the `fetchDepositMethodId` method.
*this deposit feature is currently supported on coinbase only, feel free to report any issues you find*

- `deposit ()`


Parameters

- **id** (String) *required* Deposit id
- **code** (String) Fiat currency code, required (e.g. `"USD"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"account": "fiat"}`)

Returns

- A [transaction structure](#transaction-structure)

- `fetchDepositMethodId ()`


Parameters

- **id** (String) *required* Deposit id
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"account": "fiat"}`)

Returns

- A [deposit id structure](#deposit-id-structure)

- `fetchDepositMethodIds ()`


Parameters

- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"account": "fiat"}`)

Returns

- An array of [deposit id structures](#deposit-id-structure)

### Deposit Id Structure

The deposit id structure returned from `fetchDepositMethodId`, `fetchDepositMethodIds` look like this:


Data on deposits made to an account can be retrieved using

- `fetchDeposit ()` for a single deposit
- `fetchDeposits ( code )` for multiple deposits of the same currency
- `fetchDeposits ()` for all deposits to an account


Parameters

- **id** (String) *required* Deposit id
- **code** (String) Unified CCXT currency code, required (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"network": "TRX"}`)

Returns

- A [transaction structure](#transaction-structure)


Parameters

- **code** (String) Unified CCXT currency code (e.g. `"USDT"`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve deposits for (e.g. `1646940314000`)
- **limit** (Integer) The number of [transaction structures](#transaction-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [transaction structures](#transaction-structure)

## Withdrawal

The `withdraw` method can be used to withdraw funds from an account

Some exchanges require a manual approval of each withdrawal by means of 2FA (2-factor authentication). In order to approve your withdrawal you usually have to either click their secret link in your email inbox or enter a Google Authenticator code or an Authy code on their website to verify that withdrawal transaction was requested intentionally.

In some cases you can also use the withdrawal id to check withdrawal status later (whether it succeeded or not) and to submit 2FA confirmation codes, where this is supported by the exchange. See [their docs](#exchanges) for details.


```python
withdraw(code, amount, address, tag=None, params={})
```

Parameters

- **code** (String) *required* Unified CCXT currency code (e.g. `"USDT"`)
- **amount** (Float) *required* The amount of currency to withdraw (e.g. `20`)
- **address** (String) *required* The recipient address of the withdrawal (e.g. `"TEY6qjnKDyyq5jDc3DJizWLCdUySrpQ4yp"`)
- **tag** (String) Required for some networks (e.g. `"52055"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"network": "TRX"}`)

Returns

- A [transaction structure](#transaction-structure)

---

Data on withdrawals made to an account can be retrieved using

- `fetchWithdrawal ()` for a single withdrawal
- `fetchWithdrawals ( code )` for multiple withdrawals of the same currency
- `fetchWithdrawals ()` for all withdrawals from an account


Parameters

- **id** (String) *required* Withdrawal id
- **code** (String) Unified CCXT currency code (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"network": "TRX"}`)


Parameters

- **code** (String) Unified CCXT currency code (e.g. `"USDT"`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve withdrawals for (e.g. `1646940314000`)
- **limit** (Integer) The number of [transaction structures](#transaction-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [transaction structures](#transaction-structure)

### Deposit And Withdrawal Networks

It is also possible to pass the parameters as the fourth argument with or without a specified tag


```python
withdraw(code, amount, address, { 'tag': tag, 'network': 'ETH' })
```

The following aliases of `network` allow for withdrawing crypto on multiple chains

| Currency | Network |
|:---:|:---:|
| ETH  | ERC20 |
| TRX  | TRC20 |
| BSC  | BEP20 |
| BNB  | BEP2  |
| HT   | HECO  |
| OMNI | OMNI  |

You may set the value of `exchange.withdraw ('USDT', 100, 'TVJ1fwyJ1a8JbtUxZ8Km95sDFN9jhLxJ2D', { 'network': 'TRX' })` in order to withdraw USDT on the TRON chain, or 'BSC' to withdraw USDT on Binance Smart Chain. In the table above BSC and BEP20 are equivalent aliases, so it doesn't matter which one you use as they both will achieve the same effect.

### Transaction Structure

Transactions denote a transfer of a given coin, unlike [trades](#trade-structure), which denote the exchange of one currency for another.

- *deposit structure*
- *withdrawal structure*


#### Notes On Transaction Structure

- `addressFrom` or `addressTo` may be `undefined/None/null`, if the exchange in question does not specify all sides of the transaction
- The semantics of the `address` field is exchange-specific. In some cases it can contain the address of the sender, in other cases it may contain the address of the receiver. The actual value depends on the exchange.
- The `updated` field is the UTC timestamp in milliseconds of the most recent change of status of that funding operation, be it `withdrawal` or `deposit`. It is necessary if you want to track your changes in time, beyond a static snapshot. For example, if the exchange in question reports `created_at` and `confirmed_at` for a transaction, then the `updated` field will take the value of `Math.max (created_at, confirmed_at)`, that is, the timestamp of the most recent change of the status.
- The `updated` field may be `undefined/None/null` in certain exchange-specific cases.
- The `fee` substructure may be missing, if not supplied within the reply coming from the exchange.
- The `comment` field may be `undefined/None/null`, otherwise it will contain a message or note defined by the user upon creating the transaction.
- Be careful when handling the `tag` and the `address`. The `tag` is **NOT an arbitrary user-defined string** of your choice! You cannot send user messages and comments in the `tag`. The purpose of the `tag` field is to address your wallet properly, so it must be correct. You should only use the `tag` received from the exchange you're working with, otherwise your transaction might never arrive to its destination.
- The `type` field may be `deposit/withdrawal` or, in some cases (when the exchange's endpoint returns both internal transfers and blockchain transactions, e.g. `ccxt.coinlist`), could be `transfer`.

### fetchDeposits Examples


```python
# fetch_deposits(code = None, since = None, limit = None, params = {})

if exchange.has['fetchDeposits']:
    deposits = exchange.fetch_deposits(code, since, limit, params)
else:
    raise Exception (exchange.id + ' does not have the fetch_deposits method')
```

### fetchWithdrawals Examples



```python
# fetch_withdrawals(code = None, since = None, limit = None, params = {})

if exchange.has['fetchWithdrawals']:
    withdrawals = exchange.fetch_withdrawals(code, since, limit, params)
else:
    raise Exception (exchange.id + ' does not have the fetch_withdrawals method')
```

### fetchTransactions Examples



```python
# fetch_transactions(code = None, since = None, limit = None, params = {})

if exchange.has['fetchTransactions']:
    transactions = exchange.fetch_transactions(code, since, limit, params)
else:
    raise Exception (exchange.id + ' does not have the fetch_transactions method')
```

## Deposit Addresses

The address for depositing can be either an already existing address that was created previously with the exchange or it can be created upon request. In order to see which of the two methods are supported, check the `exchange.has['fetchDepositAddress']` and `exchange.has['createDepositAddress']` properties.


Parameters

- **code** (String) *required* Unified CCXT currency code (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- an [address structure](#address-structure)

---

Some exchanges may also have a method for fetching multiple deposit addresses at once or all of them at once.


Parameters

- **code** (\[String\]) Array of unified CCXT currency codes. May or may not be required depending on the exchange (e.g. `["USDT", "BTC"]`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- an array of [address structures](#address-structure)


Parameters

- **code** (String) *required* Unified CCXT currency code (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- an array of [address structures](#address-structure)

### Address Structure

The address structures returned from `fetchDepositAddress`, `fetchDepositAddresses`, `fetchDepositAddressesByNetwork` and `createDepositAddress` look like this:


With certain currencies, like AEON, BTS, GXS, NXT, SBD, STEEM, STR, XEM, XLM, XMR, XRP, an additional argument `tag` is usually required by exchanges. Other currencies will have the `tag` set to `undefined / None / null`. The tag is a memo or a message or a payment id that is attached to a withdrawal transaction. The tag is mandatory for those currencies and it identifies the recipient user account.

Be careful when specifying the `tag` and the `address`. The `tag` is **NOT an arbitrary user-defined string** of your choice! You cannot send user messages and comments in the `tag`. The purpose of the `tag` field is to address your wallet properly, so it must be correct. You should only use the `tag` received from the exchange you're working with, otherwise your transaction might never arrive to its destination.

**The `network` field is relatively new, it may be `undefined / None / null` or missing entirely in certain cases (with some exchanges), but will be added everywhere eventually. It is still in the process of unification.**
