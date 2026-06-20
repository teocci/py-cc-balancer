# Private API — Transfers → Leverage

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 430 lines · ~4,274 tokens · 17,096 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [Transfers](#transfers)
- [Fees](#fees)
- [Borrow Interest](#borrow-interest)
- [Borrow And Repay Margin](#borrow-and-repay-margin)
- [Margin](#margin)
- [Set Margin Mode](#set-margin-mode)
- [Fetch Margin Mode](#fetch-margin-mode)
- [Set Leverage](#set-leverage)
- [Leverage](#leverage)

---

## Transfers

The `transfer` method makes internal transfers of funds between accounts on the same exchange. This can include subaccounts or accounts of different types (`spot`, `margin`, `future`, ...). If an exchange is separated on CCXT into a spot and futures class (e.g. `binanceusdm`, `kucoinfutures`, ...), then the method `transferIn` may be available to transfer funds into the futures account, and the method `transferOut` may be available to transfer funds out of the futures account


Parameters

- **code** (String) Unified CCXT currency code (e.g. `"USDT"`)
- **amount** (Float) The amount of currency to transfer (e.g. `10.5`)
- **fromAccount** (String) The account to transfer funds from.
- **toAccount** (String) The account to transfer funds to.
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)
- **params.symbol** (String) Market symbol when transfering to or from a margin account (e.g. `'BTC/USDT'`)

### Account Types

`fromAccount` and `toAccount` can accept the exchange account id or one of the following unified values:

- `funding` *for some exchanges `funding` and `spot` are the same account*
- `main` *for some exchanges that allow for subaccounts*
- `spot`
- `margin`
- `future`
- `swap`
- `lending`

You can retrieve all the account types by selecting the keys from `exchange.options['accountsByType']

Some exchanges allow transfers to email addresses, phone numbers or to other users by user id.

Returns

- A [transfer structure](#transfer-structure)


Parameters

- **code** (String) Unified CCXT currency code (e.g. `"USDT"`)
- **amount** (Float) The amount of currency to transfer (e.g. `10.5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A [transfer structure](#transfer-structure)


Parameters

- **code** (String) Unified CCXT currency code (e.g. `"USDT"`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve transfers for (e.g. `1646940314000`)
- **limit** (Integer) The number of [transfer structures](#transfer-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [transfer structures](#transfer-structure)


Parameters

- **id** (String) tranfer id (e.g. `"12345"`)
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve transfers for (e.g. `1646940314000`)
- **limit** (Integer) The number of [transfer structures](#transfer-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A [transfer structure](#transfer-structure)

### Transfer Structure

## Fees

**This section of the Unified CCXT API is under development.**

Fees are often grouped into two categories:

- Trading fees. Trading fee is the amount payable to the exchange, usually a percentage of volume traded (filled).
- Transaction fees. The amount payable to the exchange upon depositing and withdrawing as well as the underlying crypto transaction fees (tx fees).

Because the fee structure can depend on the actual volume of currencies traded by the user, the fees can be account-specific. Methods to work with account-specific fees:



The fee methods will return a unified fee structure, which is often present with orders and trades as well. The fee structure is a common format for representing the fee info throughout the library. Fee structures are usually indexed by market or currency.

Because this is still a work in progress, some or all of methods and info described in this section may be missing with this or that exchange.

**DO NOT use the `.fees` property of the exchange instance as most often it contains the predefined/hardcoded info. Actual fees should only be accessed from markets and currencies.**

**NOTE: Previously we used fetchTransactionFee(s) to fetch the transaction fees, which are now DEPRECATED and these functions have been replace by fetchDepositWithdrawFee(s)**

You call `fetchTradingFee` / `fetchTradingFees` to fetch the trading fees, `fetchDepositWithdrawFee` / `fetchDepositWithdrawFees` to fetch the deposit & withdraw fees.

### Fee Structure

Orders, private trades, transactions and ledger entries may define the following info in their `fee` field:


### Fee Schedule





### Trading Fees

Trading fees are properties of markets. Most often trading fees are loaded into the markets by the `fetchMarkets` call. Sometimes, however, the exchanges serve fees from different endpoints.

The `calculateFee` method can be used to precalculate trading fees that will be paid (use `calculateFeeWithRate` if you have a custom trading fee / tier, like VIP-X, instead of the default user fee) . **WARNING! This method is experimental, unstable and may produce incorrect results in certain cases.** You should only use it with caution. Actual fees may be different from the values returned from `calculateFee`, this is just for precalculation.  Do not rely on precalculated values, because market conditions change frequently. It is difficult to know in advance whether your order will be a market taker or maker.


The `calculateFee` method will return a unified fee structure with precalculated fees for an order with specified params.

Accessing trading fee rates should be done via [`fetchTradingFees`](#fee-schedule) which is the recommended approach. If that method is not supported by exchange, then via the `.markets` property, like so:


The markets stored under the `.markets` property may contain additional fee related information:


**WARNING! fee related information is experimental, unstable and may only be partial available or not at all.**

Maker fees are paid when you provide liquidity to the exchange i.e. you *market-make* an order and someone else fills it. Maker fees are usually lower than taker fees. Similarly, taker fees are paid when you *take* liquidity from the exchange and fill someone else's order.

Fees can be negative, this is very common amongst derivative exchanges. A negative fee means the exchange will pay a rebate (reward) to the user for the trading.

Also, some exchanges might not specify fees as percentage of volume, check the `percentage` field of the market to be sure.

#### Trading Fee Schedule

Some exchanges have an endpoint for fetching the trading fee schedule, this is mapped to the unified methods `fetchTradingFees`, and `fetchTradingFee`


Parameters

- **symbol** (String) *required* Unified market symbol (e.g. `"BTC/USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"currency": "quote"}`)

Returns

- A [trading fee structure](#trading-fee-structure)


Parameters

- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"currency": "quote"}`)

Returns

- An array of [trading fee structures](#trading-fee-structure)

#### Trading Fee Structure


### Transaction Fees

Transaction fees are properties of currencies (account balance).

Accessing transaction fee rates should be done via the `.currencies` property. This aspect is not unified yet and is subject to change.


#### Transaction Fee Schedule

Some exchanges have an endpoint for fetching the transaction fee schedule, this is mapped to the unified methods

- `fetchTransactionFee ()` for a single transaction fee schedule
- `fetchTransactionFees ()` for all transaction fee schedules


Parameters

- **code** (String) *required* Unified CCXT currency code, required (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"type": "deposit"}`)
- **params.network** (String) Specify unified CCXT network (e.g. `{"network": "TRC20"}`)

Returns

- A [transaction fee structure](#transaction-fee-structure)


Parameters

- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"type": "deposit"}`)

Returns

- An array of [transaction fee structures](#transaction-fee-structure)

#### Transaction Fee Structure


## Borrow Interest

* margin only

To trade with leverage in spot or margin markets, currency must be borrowed as a loan. This borrowed currency must be payed back with interest. To obtain the amount of interest that has accrued you can use the `fetchBorrowInterest` method


Parameters

- **code** (String) The unified currency code for the currency of the interest (e.g. `"USDT"`)
- **symbol** (String) The market symbol of an isolated margin market, if undefined, the interest for cross margin markets is returned (e.g. `"BTC/USDT:USDT"`)
- **since** (Integer) Timestamp (ms) of the earliest time to receive interest records for (e.g. `1646940314000`)
- **limit** (Integer) The number of [borrow interest structures](#borrow-interest-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [borrow interest structures](#borrow-interest-structure)

### Borrow Interest Structure


## Borrow And Repay Margin

*margin only*

To borrow and repay currency as a margin loan use `borrowCrossMargin`, `borrowIsolatedMargin`, `repayCrossMargin` and `repayIsolatedMargin`.

Parameters

- **code** (String) *required* The unified currency code for the currency to be borrowed or repaid (e.g. `"USDT"`)
- **amount** (Float) *required* The amount of margin to borrow or repay (e.g. `20.92`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"rate": 0.002}`)

Returns

- A [margin loan structure](#margin-loan-structure)

Parameters

- **symbol** (String) *required* The unified CCXT market symbol of an isolated margin market (e.g. `"BTC/USDT"`)
- **code** (String) *required* The unified currency code for the currency to be borrowed or repaid (e.g. `"USDT"`)
- **amount** (Float) *required* The amount of margin to borrow or repay (e.g. `20.92`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"rate": 0.002}`)

Returns

- A [margin loan structure](#margin-loan-structure)

### Margin Loan Structure


## Margin

*margin and contract only*

Note: through the manual we use term "collateral" which means current margin balance, but do not confuse it with "initial margin" or "maintenance margin":
- `collateral (current margin balance) = initial margin + realized & unrealized profit`.

For example, when you had opened an isolated position with **50$** initial margin and the position has unrealized profit of **-15$**, then your position's **collateral** will be **35$**. However, if we take that Maintenance Margin requirement (to keep the position open) by exchange hints **$25** for that position, then your collateral should not drop below it, otherwise the position will be liquidated.

To increase, reduce or set your margin balance (collateral) in an open leveraged position, use `addMargin`, `reduceMargin` and `setMargin` respectively. This is kind of like adjusting the amount of leverage you're using with a position that's already open.

Some scenarios to use these methods include
- if the trade is going against you, you can add margin to, reducing the risk of liquidation
- if your trade is going well you can reduce your position's margin balance and take profits



Parameters

- **symbol** (String) *required* Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **amount** (String) *required* Amount of margin to add or reduce (e.g. `20`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"leverage": 5}`)

Returns

- a [margin structure](#margin-structure)

You can fetch the history of margin adjustments made using the methods above or automatically by the exchange using the following method


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **type** (String) "add" or "reduce"
- **since** (Integer) Timestamp (ms) of the earliest time to retrieve margin adjustments for for (e.g. `1646940314000`)
- **limit** (Integer) The number of [margin structures](#margin-structure) to retrieve (e.g. `5`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"auto": true}`)

Returns

- a [margin structure](#margin-structure)

### Margin Structure


## Set Margin Mode

*contract only*

Updates the type of margin used to be either

- `cross` One account is used to share collateral between markets. Margin is taken from total account balance to avoid liquidation when needed.
- `isolated` Each market, keeps collateral in a separate account


Parameters

- **marginMode** (String) *required* the type of margin used
    **Unified margin types:**
    - `"cross"`
    - `"isolated"`
- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`) *required* on most exchanges. Is not required when the margin mode is not specific to a market
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"leverage": 5}`)

Returns

- response from the exchange

### Exchanges Without setMarginMode

Common reasons for why an exchange might have


include

- the exchange does not offer leveraged trading
- the exchange only offers one of `cross` or `isolated` margin modes, but does not offer both
- margin mode must be set using an exchange specific parameter within `params` when using `createOrder`

### Notes On Suppressed Errors For setMarginMode

Some exchange apis return an error response when a request is sent to set the margin mode to the mode that it is already set to (e.g. Sending a request to set the margin mode to `cross` for the market `BTC/USDT:USDT` when the account already has `BTC/USDT:USDT` set to use cross margin). CCXT doesn't see this as an error because the end result is what the user wanted, so the error is suppressed and the error result is returned as an object.

e.g.


### Notes On The marginMode Parameter

Some methods allow the usage of a `marginMode` parameter that can be set to either `cross` or `isolated`. This can be useful for specifying the `marginMode` directly within the methods params, for use with spot margin or contract markets. To specify a spot margin market, you need to use a unified spot symbol or set the market type to spot, while setting the marginMode parameter to `cross` or `isolated`.

Create a Spot Margin Order:

*Use a unified spot symbol, while setting the marginMode parameter.*



```python
params = {
    'marginMode': 'isolated', # or 'cross'
}
order = exchange.create_order ('ETH/USDT', 'market', 'buy', 0.1, 1500, params)
```

## Fetch Margin Mode

*margin and contract only*

The `fetchMarginMode()` method can be used to obtain the set margin mode for a market. The `fetchMarginModes()` method can be used to obtain the set margin mode for multiple markets at once.

You can access the set margin mode by using:

- `fetchMarginMode()` (single symbol)
- `fetchMarginModes([symbol1, symbol2, ...])` (multiple symbols)
- `fetchMarginModes()` (all market symbols)


Parameters

- **symbol** (String) *required* A unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"subType": "linear"}`)

Returns

- a [margin-mode-structure](#margin-mode-structure)


Parameters

- **symbols** (\[String\]) A list of unified CCXT symbols (e.g. `[ "BTC/USDT:USDT" ]`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"subType": "linear"}`)

Returns

- an array of [margin-mode-structures](#margin-mode-structure)

### Margin Mode Structure


## Set Leverage

*margin and contract only*


Parameters

- **leverage** (Integer) *required* The desired leverage
- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`) *required* on most exchanges. Is not required when leverage is not specific to a market (e.g. If leverage is set for the account and not per market)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"marginMode": "cross"}`)

Returns

- response from the exchange

## Leverage

*margin and contract only*

The `fetchLeverage()` method can be used to obtain the set leverage for a market. The `fetchLeverages()` method can be used to obtain the set leverage for multiple markets at once.

You can access the set leverage by using:

- `fetchLeverage()` (single symbol)
- `fetchLeverages([symbol1, symbol2, ...])` (multiple symbols)
- `fetchLeverages()` (all market symbols)


Parameters

- **symbol** (String) *required* A unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"marginMode": "cross"}`)

Returns

- a [leverage-structure](#leverage-structure)


Parameters

- **symbols** (\[String\]) A list of unified CCXT symbols (e.g. `[ "BTC/USDT:USDT" ]`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"marginMode": "cross"}`)

Returns

- an array of [leverage-structures](#leverage-structure)

### Leverage Structure

