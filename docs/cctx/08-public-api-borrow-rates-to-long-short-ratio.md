# Public API — Borrow Rates → Long Short Ratio

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 435 lines · ~3,455 tokens · 13,822 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [Borrow Rates](#borrow-rates)
- [Borrow Rate History](#borrow-rate-history)
- [Leverage Tiers](#leverage-tiers)
- [Funding Rate](#funding-rate)
- [Funding Interval](#funding-interval)
- [Funding Rate History](#funding-rate-history)
- [Open Interest](#open-interest)
- [Historical Volatility](#historical-volatility)
- [Underlying Assets](#underlying-assets)
- [Settlement History](#settlement-history)
- [Liquidations](#liquidations)
- [Greeks](#greeks)
- [Option Chain](#option-chain)
- [Long Short Ratio](#long-short-ratio)

---

## Borrow Rates

*margin only*

When short trading or trading with leverage on a spot market, currency must be borrowed. Interest is accrued for the borrowed currency.

Data on the borrow rate for a currency can be retrieved using

- `fetchCrossBorrowRate ()` for a single currencies borrow rate
- `fetchCrossBorrowRates ()` for all currencies borrow rates
- `fetchIsolatedBorrowRate ()` for a trading pairs borrow rate
- `fetchIsolatedBorrowRates ()` for all trading pairs borrow rates
- `fetchBorrowRatesPerSymbol ()` for the borrow rates of currencies in individual markets


Parameters

- **code** (String) Unified CCXT currency code, required (e.g. `"USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"settle": "USDT"}`)

Returns

- A [borrow rate structure](#borrow-rate-structure)


Parameters

- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"startTime": 1610248118000}`)

Returns

- A dictionary of [borrow rate structures](#borrow-rate-structure) with unified currency codes as keys


Parameters

- **symbol** (String) Unified CCXT market symbol, required (e.g. `"BTC/USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"settle": "USDT"}`)

Returns

- An [isolated borrow rate structure](#isolated-borrow-rate-structure)


Parameters

- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"startTime": 1610248118000}`)

Returns

- A dictionary of [isolated borrow rate structures](#isolated-borrow-rate-structure) with unified market symbols as keys

### Isolated Borrow Rate Structure


### Borrow Rate Structure


## Borrow Rate History

*margin only*

The `fetchBorrowRateHistory` method retrieves a history of a currencies borrow interest rate at specific time slots


Parameters

- **code** (String) *required* Unified CCXT currency code (e.g. `"USDT"`)
- **since** (Integer) Timestamp for the earliest borrow rate (e.g. `1645807945000`)
- **limit** (Integer) The maximum number of [borrow rate structures](#borrow-rate-structure) to retrieve (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [borrow rate structures](#borrow-rate-structure)

## Leverage Tiers

*contract only*

- Leverage Tier methods are private on **binance**

The `fetchLeverageTiers()` method can be used to obtain the maximum leverage for a market at varying position sizes. It can also be used to obtain the maintenance margin rate, and the max tradeable amount for a market when that information is not available from the market object

While you can obtain the absolute maximum leverage for a market by accessing `market['limits']['leverage']['max']`, for many contract markets, the maximum leverage will depend on the size of your position.

You can access those limits by using

- `fetchMarketLeverageTiers()` (single symbol)
- `fetchLeverageTiers([symbol1, symbol2, ...])` (multiple symbols)
- `fetchLeverageTiers()` (all market symbols)


Parameters

- **symbol** (String) *required* Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- a [leverage-tiers-structure](#leverage-tiers-structure)


Parameters

- **symbols** (\[String\]) Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- an array of [leverage-tiers-structures](#leverage-tiers-structure)

### Leverage Tiers Structure


In the example above:

- stakes below 133.33       = a max leverage of 75
- stakes from 200 + 1000    = a max leverage of 50
- a stake amount of 150     = a max leverage of (10000 / 150)   = 66.66
- stakes between 133.33-200 = a max leverage of (10000 / stake) = 50.01 -> 74.99

**Note for htx users:** htx uses both leverage and amount to determine maintenance margin rates: https://www.htx.com/support/en-us/detail/900000089903

## Funding Rate

*contract only*

Data on the current, most recent, and next funding rates can be obtained using the methods

- `fetchFundingRates ()` for all market symbols
- `fetchFundingRates ([ symbol1, symbol2, ... ])` for multiple market symbols
- `fetchFundingRate (symbol)` for a single market symbol


Parameters

- **symbol** (String) *required* Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- a [funding rate structure](#funding-rate-structure)


Parameters

- **symbols** (\[String\]) An optional array/list of unified CCXT symbols (e.g. `["BTC/USDT:USDT", "ETH/USDT:USDT"]`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [funding rate structures](#funding-rate-structure) indexed by market symbols

## Funding Interval

*contract only*

Retrieve the current funding interval using the following methods:

- `fetchFundingInterval (symbol)` for a single market symbol
- `fetchFundingIntervals ()` for all market symbols
- `fetchFundingIntervals ([ symbol1, symbol2, ... ])` for multiple market symbols


Parameters

- **symbol** (String) *required* Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A [funding rate structure](#funding-rate-structure)


Parameters

- **symbols** (\[String\]) An optional array/list of unified CCXT symbols (e.g. `["BTC/USDT:USDT", "ETH/USDT:USDT"]`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [funding rate structures](#funding-rate-structure)

### Funding Rate Structure


## Funding Rate History

*contract only*


Parameters

- **symbol** (String) Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **since** (Integer) Timestamp for the earliest funding rate (e.g. `1645807945000`)
- **limit** (Integer) The maximum number of funding rates to retrieve (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [funding rate history structures](#funding-rate-history-structure)

### Funding Rate History Structure


## Open Interest

*contract only*

Use the `fetchOpenInterest` method to get the current open interest for a symbol from the exchange. Use `fetchOpenInterests` to get the current open interest for multiple symbols


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An [open interest structure](#open-interest-structure)


- **symbols** ([String]) An optional array/list of unified CCXT symbols (e.g. `["BTC/USDT:USDT", "ETH/USDT:USDT"]`). Leave as `undefined` for all symbols.
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- A dictionary of [open interest structures](#open-interest-structure)

### Open Interest History

*contract only*

Use the `fetchOpenInterestHistory` method to get a history of open interest for a symbol from the exchange.


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USDT:USDT"`)
- **timeframe** (String) Check exchange.timeframes for available values
- **since** (Integer) Timestamp for the earliest open interest record (e.g. `1645807945000`)
- **limit** (Integer) The maximum number of [open interest structures](#open-interest-structures) to retrieve (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

**Note for OKX users:** instead of a unified symbol okx.fetchOpenInterestHistory expects a unified currency code in the **symbol** argument (e.g. `'BTC'`).

Returns

- An array of [open interest structures](#open-interest-structure)

### Open Interest Structure


## Historical Volatility

*option only*

Use the `fetchVolatilityHistory` method to get the volatility history for the code of an options underlying asset from the exchange.


Parameters

- **code** (String) *required* Unified CCXT currency code (e.g. `"BTC"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [volatility history structures](#volatility-structure)

### Volatility Structure


## Underlying Assets

*contract only*

Use the `fetchUnderlyingAssets` method to get the market id's of underlying assets for a contract market type from the exchange.


Parameters

- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"instType": "OPTION"}`)
- **params.type** (String) Unified marketType, the default is 'option' (e.g. `"option"`)

Returns

- An [underlying assets structure](#underlying-assets-structure)

### Underlying Assets Structure


## Settlement History

*contract only*

Use the `fetchSettlementHistory` method to get the public settlement history for a contract market from the exchange. Use `fetchMySettlementHistory` to get only your settlement history


Parameters

- **symbol** (String) Unified CCXT symbol (e.g. `"BTC/USDT:USDT-230728-25500-P"`)
- **since** (Integer) Timestamp for the earliest settlement (e.g. `1694073600000`)
- **limit** (Integer) The maximum number of settlements to retrieve (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- An array of [settlement history structures](#settlement-history-structure)

### Settlement History Structure


## Liquidations

*margin and contract only*

Use the `fetchLiquidations` method to get the public liquidations of a trading pair from the exchange. Use `fetchMyLiquidations` to get only your liquidation history


Parameters

- **symbol** (String) Unified CCXT symbol (e.g. `"BTC/USDT:USDT-231006-25000-P"`)
- **since** (Integer) Timestamp for the earliest liquidation (e.g. `1694073600000`)
- **limit** (Integer) The maximum number of liquidations to retrieve (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"until": 1645807945000}`)

Returns

- An array of [liquidation structures](#liquidation-structure)

### Liquidation Structure


## Greeks

*option only*

Use the `fetchGreeks` method to get the public greeks and implied volatility of an options trading pair from the exchange. Use `fetchAllGreeks` to get the greeks for all symbols or multiple symbols.
The greeks measure how factors like the underlying assets price, time to expiration, volatility, and interest rates, affect the price of an options contract.


Parameters

- **symbol** (String) Unified CCXT symbol (e.g. `"BTC/USD:BTC-240927-40000-C"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "options"}`)

Returns

- A [greeks structure](#greeks-structure)


Parameters

- **symbols** (String) Unified CCXT symbol (e.g. `"BTC/USD:BTC-240927-40000-C"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "options"}`)

// for example
fetchAllGreeks () // all symbols
fetchAllGreeks ([ 'BTC/USD:BTC-240927-40000-C', 'ETH/USD:ETH-240927-4000-C' ]) // an array of specific symbols

Returns

- A list of [greeks structure](#greeks-structure)

### Greeks Structure


## Option Chain

*option only*

Use the `fetchOption` method to get the public details of a single option contract from the exchange.


Parameters

- **symbol** (String) Unified CCXT market symbol (e.g. `"BTC/USD:BTC-240927-40000-C"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "options"}`)

Returns

- An [option chain structure](#option-chain-structure)

Use the `fetchOptionChain` method to get the public option chain data of an underlying currency from the exchange.


Parameters

- **code** (String) Unified CCXT currency code (e.g. `"BTC"`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"category": "options"}`)

Returns

- A list of [option chain structures](#option-chain-structure)

### Option Chain Structure


## Long Short Ratio

*contract only*

Use the `fetchLongShortRatio` method to fetch the current long short ratio of a symbol and use the `fetchLongShortRatioHistory` to fetch the history of long short ratios for a symbol.

- `fetchLongShortRatio (symbol, period)` for the current ratio of a single market symbol
- `fetchLongShortRatioHistory (symbol, period, since, limit)` for the history of ratios of a single market symbol


Parameters

- **symbol** (String) *required* Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **period** (String) The period to calculate the ratio from (e.g. `"24h"`)
- **params** (Dictionary) Parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- a [long short ratio structure](#long-short-ratio-structure)


Parameters

- **symbol** (String) Unified CCXT symbol (e.g. `"BTC/USDT:USDT"`)
- **period** (String) The period to calculate the ratio from (e.g. `"24h"`)
- **since** (Integer) Timestamp for the earliest ratio (e.g. `1645807945000`)
- **limit** (Integer) The maximum number of ratios to retrieve (e.g. `10`)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"endTime": 1645807945000}`)

Returns

- an array of [long short ratio structures](#long-short-ratio-structure)

### Long Short Ratio Structure

