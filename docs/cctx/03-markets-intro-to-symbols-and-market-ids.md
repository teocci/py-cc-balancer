# Markets — intro → Symbols And Market Ids

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 448 lines · ~7,917 tokens · 31,668 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [intro](#intro)
- [Currency Structure](#currency-structure)
- [Network Structure](#network-structure)
- [Market Structure](#market-structure)
- [Active Status](#active-status)
- [Precision And Limits](#precision-and-limits)
- [Loading Markets](#loading-markets)
- [Symbols And Market Ids](#symbols-and-market-ids)

---

- [Currency Structure](#currency-structure)
- [Market Structure](#market-structure)
- [Precision And Limits](#precision-and-limits)
- [Loading Markets](#loading-markets)
- [Symbols And Market Ids](#symbols-and-market-ids)
- [Market Cache Force Reload](#market-cache-force-reload)

Each exchange is a place for trading some kinds of valuables. The exchanges may use differing terms to call them: _"a currency"_, _"an asset"_, _"a coin"_, _"a token"_, _"stock"_, _"commodity"_, _"crypto"_, "fiat", etc. A place for trading one asset for another is usually called _"a market"_, _"a symbol"_, _"a trading pair"_, _"a contract"_, etc.

In terms of the ccxt library, every exchange offers multiple **markets** within itself. Each market is defined by two or more **currencies**. The set of markets differs from exchange to exchange opening possibilities for cross-exchange and cross-market arbitrage.

## Currency Structure


Each currency is an associative array (aka dictionary) with the following keys:

- `id`. The string or numeric ID of the currency within the exchange. Currency ids are used inside exchanges internally to identify coins during the request/response process.
- `code`. An uppercase string code representation of a particular currency. Currency codes are used to reference currencies within the ccxt library (explained below).
- `name`. A human-readable name of the currency (can be a mix of uppercase & lowercase characters).
- `fee`. The withdrawal fee value as specified by the exchange. In most cases it means a flat fixed amount paid in the same currency. If the exchange does not specify it via public endpoints, the `fee` can be `undefined/None/null` or missing.
- `active`. A boolean indicating whether trading or funding (depositing or withdrawing) for this currency is currently possible, more about it here: [`active` status](#active-status).
- `info`. An associative array of non-common market properties, including fees, rates, limits and other general market information. The internal info array is different for each particular market, its contents depend on the exchange.
- `precision`. Precision accepted in values by exchanges upon referencing this currency. The value of this property depends on [`exchange.precisionMode`](#precision-mode).
- `limits`. The minimums and maximums for amounts (volumes), withdrawals and deposits.

## Network Structure


Each network is an associative array (aka dictionary) with the following keys:

- `id`. The string or numeric ID of the network within the exchange. Network ids are used inside exchanges internally to identify networks during the request/response process.
- `network`. An uppercase string representation of a particular network. Networks are used to reference networks within the ccxt library.
- `name`. A human-readable name of the network (can be a mix of uppercase & lowercase characters).
- `fee`. The withdrawal fee value as specified by the exchange. In most cases it means a flat fixed amount paid in the same currency. If the exchange does not specify it via public endpoints, the `fee` can be `undefined/None/null` or missing.
- `active`. A boolean indicating whether trading or funding (depositing or withdrawing) for this currency is currently possible, more about it here: [`active` status](#active-status).
- `info`. An associative array of non-common market properties, including fees, rates, limits and other general market information. The internal info array is different for each particular market, its contents depend on the exchange.
- `precision`. Precision accepted in values by exchanges upon referencing this currency. The value of this property depends on [`exchange.precisionMode`](#precision-mode).
- `limits`. The minimums and maximums for amounts (volumes), withdrawals and deposits.

## Market Structure


Each market is an associative array (aka dictionary) with the following keys:

- `id`. The string or numeric ID of the market or trade instrument within the exchange. Market ids are used inside exchanges internally to identify trading pairs during the request/response process.
- `symbol`. An uppercase string code representation of a particular trading pair or instrument. This is usually written as `BaseCurrency/QuoteCurrency` with a slash as in `BTC/USD`, `LTC/CNY` or `ETH/EUR`, etc. Symbols are used to reference markets within the ccxt library (explained below).
- `base`. A unified uppercase string code of base fiat or crypto currency. This is the standardized currency code that is used to refer to that currency or token throughout CCXT and throughout the Unified CCXT API, it's the language that CCXT understands.
- `quote`. A unified uppercase string code of quoted fiat or crypto currency.
- `baseId`. An exchange-specific id of the base currency for this market, not unified. Can be any string, literally. This is communicated to the exchange using the language the exchange understands.
- `quoteId`. An exchange-specific id of the quote currency, not unified.
- `active`. A boolean indicating whether or not trading this market is currently possible, more about it here: [`active` status](#active-status).
- `maker`. Float, 0.0015 = 0.15%. Maker fees are paid when you provide liquidity to the exchange i.e. you *market-make* an order and someone else fills it. Maker fees are usually lower than taker fees. Fees can be negative, this is very common amongst derivative exchanges. A negative fee means the exchange will pay a rebate (reward) to the user for trading this market (note, 'taker' and 'maker' publicly available fees, not taking into consideration your vip-level/volume/etc. Use [`fetchTradingFees`](#fee-schedule) to get the fees specific to your account).
- `taker`. Float, 0.002 = 0.2%. Taker fees are paid when you *take* liquidity from the exchange and fill someone else's order.
- `percentage`. A boolean true/false value indicating whether `taker` and `maker` are multipliers or fixed flat amounts.
- `tierBased`. A boolean true/false value indicating whether the fee depends on your trading tier (usually, your traded volume over a period of time).
- `info`. An associative array of non-common market properties, including fees, rates, limits and other general market information. The internal info array is different for each particular market, its contents depend on the exchange.
- `precision`. Precision accepted in order values by exchanges upon order placement for price, amount and cost. (The value inside this property depend on the [`exchange.precisionMode`](#precision-mode)).
- `limits`. The minimums and maximums for prices, amounts (volumes) and costs (where cost = price * amount).
- `optionType`. The type of the option, `call` option represents an option with the right to buy and `put` an option with the right to sell.
- `strike`. Price at which an option can be bought or sold when it is exercised.

## Active Status

The `active` flag is typically used in [`currencies`](#currency-structure) and [`markets`](#market-structure). The exchanges might put a slightly different meaning into it. If a currency is inactive, most of the time all corresponding tickers, orderbooks and other related endpoints return empty responses, all zeroes, no data or outdated information. The user should check if the currency is `active` and [reload markets periodically](#market-cache-force-reload).

Note: the `false` value for the `active` property doesn't always guarantee that all of the possible features like trading, withdrawing or depositing are disabled on the exchange. Likewise, neither the `true` value guarantees that all those features are enabled on the exchange. Check the underlying exchanges' documentation and the code in CCXT for the exact meaning of the `active` flag for this or that exchange. This flag is not yet supported or implemented by all markets and may be missing.

**WARNING! The information about the fee is experimental, unstable and may be partial or not available at all.**

## Precision And Limits

**Do not confuse `limits` with `precision`!** Precision has nothing to do with min limits. A precision of `0.01` does not necessarily mean that a minimum limit for market is `0.01`. The opposite is also true: a min limit of `0.01` does not necessarily mean a precision is `0.01`.

Examples:

1.
```
market['limits']['amount']['min'] == 0.05 &&
market['precision']['amount'] == 0.0001 &&
market['precision']['price'] == 0.01
```

  - The *amount value* should be >= 0.05:
  - *Precision of the amount* should be up to 4 digits after dot (0.0001):
  - *Precision of the price* should be up to 2 digits after dot (0.01):
  - 

2. `(market['precision']['amount'] == -1)`

    A negative *precision* might only theoretically happen if exchange's `precisionMode` is `SIGNIFICANT_DIGIT` or `DECIMAL_PRECISION`. It means that the amount should be an integer multiple of 10 (to the absolute power specified):
    In case of `-2` the acceptable values would be multiple of `100` (e.g. 100, 200, ... ), and so on.


#### Precision Mode

Supported precision modes in `exchange['precisionMode']` are:

- `TICK_SIZE` – almost all exchanges use this precision mode. In this mode, the numbers in `market_or_currency['precision']` designate the minimal precision fractions (floats) for rounding or truncating.
- `SIGNIFICANT_DIGITS` – counts non-zero digits only, some exchanges (`bitfinex` and maybe a few other) implement this mode of counting decimals. With this mode of precision, the numbers in `market_or_currency['precision']` designate the Nth place of the last significant (non-zero) decimal digit after the dot.
- `DECIMAL_PLACES` (**DEPRECATED, CCXT no longer uses this mode anywhere**) – counts all digits. With this mode of precision, the numbers in `market_or_currency['precision']` designate the number of decimal digits after the dot for further rounding or truncation.

### Notes On Precision And Limits

The user is required to stay within all limits and precision! The values of the order should satisfy the following conditions:

- Order `amount` >= `limits['amount']['min']`
- Order `amount` <= `limits['amount']['max']`
- Order `price` >= `limits['price']['min']`
- Order `price` <= `limits['price']['max']`
- Order `cost` (`amount * price`) >= `limits['cost']['min']`
- Order `cost` (`amount * price`) <= `limits['cost']['max']`
- Precision of `amount` must be <= `precision['amount']`
- Precision of `price` must be <= `precision['price']`

The above values can be missing with some exchanges that don't provide info on limits from their API or don't have it implemented yet.

### Methods For Formatting Decimals

Each exchange has its own rounding, counting and padding modes.

Supported rounding modes are:

- `ROUND` – will round the last decimal digits to precision
- `TRUNCATE`– will cut off the digits after certain precision

The decimal precision counting mode is available in the `exchange.precisionMode` property.

#### Padding Mode

Supported padding modes are:

- `NO_PADDING` – default for most cases
- `PAD_WITH_ZERO` – appends zero characters up to precision

#### Formatting To Precision

Most of the time the user does not have to take care of precision formatting, since CCXT will handle that for the user when the user places orders or sends withdrawal requests, if the user follows the rules as described on [Precision And Limits](#precision-and-limits). However, in some cases precision-formatting details may be important, so the following methods may be useful in the userland.

The exchange base class contains the `decimalToPrecision` method to help format values to the required decimal precision with support for different rounding, counting and padding modes.





```python
# WARNING! The `decimal_to_precision` method is susceptible to getcontext().prec!
def decimal_to_precision(n, rounding_mode=ROUND, precision=None, counting_mode=DECIMAL_PLACES, padding_mode=NO_PADDING):
```






For examples of how to use the `decimalToPrecision` to format strings and floats, please, see the following files:

- Typescript: https://github.com/ccxt/ccxt/blob/master/ts/src/test/base/functions/test.number.ts
- JavaScript: https://github.com/ccxt/ccxt/blob/master/js/src/test/base/functions/test.number.js
- Python: https://github.com/ccxt/ccxt/blob/master/python/ccxt/test/base/test_number.py
- PHP: https://github.com/ccxt/ccxt/blob/master/php/test/base/test_number.php

**Python WARNING! The `decimal_to_precision` method is susceptible to `getcontext().prec!`**

For users' convenience CCXT base exchange class also implements the following methods:



```python
def amount_to_precision (symbol, amount):
def price_to_precision (symbol, price):
def cost_to_precision (symbol, cost):
def currency_to_precision (code, amount):
```

Every exchange has its own precision settings, the above methods will help format those values according to exchange-specific precision rules, in a way that is portable and agnostic of the underlying exchange. In order to make that possible, markets and currencies have to be loaded prior to formatting any values.

**Make sure to [load the markets with `exchange.loadMarkets()`](#loading-markets) before calling these methods!**

For example:






```python
exchange.load_markets()
symbol = 'BTC/USDT'
amount = 1.2345678  # amount in base currency BTC
price = 87654.321  # price in quote currency USDT
formatted_amount = exchange.amount_to_precision(symbol, amount)
formatted_price = exchange.price_to_precision(symbol, price)
print(formatted_amount, formatted_price)
```


More practical examples that describe the behavior of `exchange.precisionMode`:




## Loading Markets

In most cases you are required to load the list of markets and trading symbols for a particular exchange prior to accessing other API methods. If you forget to load markets the ccxt library will do that automatically upon your first call to the unified API. It will send two HTTP requests, first for markets and then the second one for other data, sequentially. For that reason, your first call to a unified CCXT API method like fetchTicker, fetchBalance, etc will take more time, than the consequent calls, since it has to do more work loading the market information from the exchange API. See [Notes On Rate Limiter](#notes-on-rate-limiter) for more details.

In order to load markets manually beforehand call the `loadMarkets ()` / `load_markets ()` method on an exchange instance. It returns an associative array of markets indexed by trading symbol. If you want more control over the execution of your logic, preloading markets by hand is recommended.





```python
okcoin = ccxt.okcoin()
markets = okcoin.load_markets()
print(okcoin.id, markets)
```






Apart from the market info, the `loadMarkets()` call will also load the currencies from the exchange and will cache the info in the `.markets` and the `.currencies` properties respectively.

The user can also bypass the cache and call unified methods for fetching that information from the exchange endpoints directly, `fetchMarkets()` and `fetchCurrencies()`, though using these methods is not recommended for end-users. The recommended way to preload markets is by calling the `loadMarkets()` unified method. However, new exchange integrations are required to implement these methods if the underlying exchange has the corresponding API endpoints.

### Sharing Markets Between Exchange Instances

To optimize memory usage and reduce redundant API calls, you can share market data between multiple instances of the same exchange. This is especially useful when creating multiple exchange instances or when you want to reuse market data that has already been loaded.





```python
# Create first exchange instance and load markets
exchange1 = ccxt.binance()
exchange1.load_markets()

# Create second exchange instance
exchange2 = ccxt.binance()

# Share markets from first instance to second using the setMarketsFromExchange method
exchange2.set_markets_from_exchange(exchange1)

# Now exchange2 can use the shared markets without loading them
print(exchange2.symbols)  # Available immediately

# When calling load_markets on exchange2, it will use cached markets
exchange2.load_markets()  # No API call, uses shared markets
```






**Benefits of Market Sharing:**
- **Memory Efficiency**: Multiple exchange instances share the same market objects in memory
- **Performance**: Eliminates redundant API calls for market data
- **Resource Conservation**: Reduces network requests and API rate limit usage
- **Persistence**: Market data remains available even if individual exchange instances are destroyed

**Alternative Simple Assignment:**

If you prefer direct property assignment, you can also share markets by directly assigning the `markets` property:


However, using the `setMarketsFromExchange()` method is recommended as it:
- Validates that both exchanges are of the same type
- Ensures all related market data is properly copied
- Provides better error handling

**Important Notes:**
- Only share markets between instances of the same exchange type
- Market sharing is most effective when both instances use the same API credentials and configuration
- The shared market objects will persist in memory as long as at least one reference exists
- Both the `setMarketsFromExchange()` method and direct assignment create shared references, not copies

## Symbols And Market Ids

A currency code is a code of three to five letters, like `BTC`, `ETH`, `USD`, `GBP`, `CNY`, `JPY`, `DOGE`, `RUB`, `ZEC`, `XRP`, `XMR`, etc. Some exchanges have exotic currencies with longer codes.

A symbol is usually an uppercase string literal name of a pair of traded currencies with a slash in between. The first currency before the slash is usually called *base currency*, and the one after the slash is called *quote currency*. Examples of a symbol are: `BTC/USD`, `DOGE/LTC`, `ETH/EUR`, `DASH/XRP`, `BTC/CNY`, `ZEC/XMR`, `ETH/JPY`.

Market ids are used during the REST request-response process to reference trading pairs within exchanges. The set of market ids is unique per exchange and cannot be used across exchanges. For example, the BTC/USD pair/market may have different ids on various popular exchanges, like `btcusd`, `BTCUSD`, `XBTUSD`, `btc/usd`, `42` (numeric id), `BTC/USD`, `Btc/Usd`, `tBTCUSD`, `XXBTZUSD`. You don't need to remember or use market ids, they are there for internal HTTP request-response purposes inside exchange implementations.

The ccxt library abstracts uncommon market ids to symbols, standardized to a common format. Symbols aren't the same as market ids. Every market is referenced by a corresponding symbol. Symbols are common across exchanges which makes them suitable for arbitrage and many other things.

Sometimes the user might notice a symbol like `'XBTM18'` or `'.XRPUSDM20180101'` or some other *"exotic/rare symbols"*. The symbol is **not required** to have a slash or to be a pair of currencies. The string in the symbol really depends on the type of the market (whether it is a spot market or a futures market, a darkpool market or an expired market, etc). Attempting to parse the symbol string is highly discouraged, one should not rely on the symbol format, it is recommended to use market properties instead.

Market structures are indexed by symbols and ids. The base exchange class also has builtin methods for accessing markets by symbols. Most API methods require a symbol to be passed in their first argument. You are often required to specify a symbol when querying current prices, making orders, etc.

Most of the time users will be working with market symbols. You will get a standard userland exception if you access non-existent keys in these dicts.

### Methods For Markets And Currencies




```python
print(exchange.load_markets())

etheur1 = exchange.markets['ETH/EUR']         # get market structure by symbol
etheur2 = exchange.market('ETH/EUR')          # same result in a slightly different way

etheurId = exchange.market_id('ETH/EUR')      # get market id by symbol

symbols = exchange.symbols                    # get a list of symbols
symbols2 = list(exchange.markets.keys())      # same as previous line

print(exchange.id, symbols)                   # print all symbols

currencies = exchange.currencies              # a dictionary of currencies

kraken = ccxt.kraken()
kraken.load_markets()

kraken.markets['BTC/USD']                     # symbol → market (get market by symbol)
kraken.markets_by_id['XXRPZUSD'][0]           # id → market (get market by id)

kraken.markets['BTC/USD']['id']               # symbol → id (get id by symbol)
kraken.markets_by_id['XXRPZUSD'][0]['symbol'] # id → symbol (get symbol by id)
```



### Naming Consistency

There is a bit of term ambiguity across various exchanges that may cause confusion among newcoming traders. Some exchanges call markets as *pairs*, whereas other exchanges call symbols as *products*. In terms of the ccxt library, each exchange contains one or more trading markets. Each market has an id and a symbol. Most symbols are pairs of base currency and quote currency.

```Exchanges → Markets → Symbols → Currencies```

Historically various symbolic names have been used to designate same trading pairs. Some cryptocurrencies (like Dash) even changed their names more than once during their ongoing lifetime. For consistency across exchanges the ccxt library will perform the following known substitutions for symbols and currencies:

- `XBT → BTC`: `XBT` is newer but `BTC` is more common among exchanges and sounds more like bitcoin ([read more](https://www.google.ru/search?q=xbt+vs+btc)).
- `BCC → BCH`: The Bitcoin Cash fork is often called with two different symbolic names: `BCC` and `BCH`. The name `BCC` is ambiguous for Bitcoin Cash, it is confused with BitConnect. The ccxt library will convert `BCC` to `BCH` where it is appropriate (some exchanges and aggregators confuse them).
- `DRK → DASH`: `DASH` was Darkcoin then became Dash ([read more](https://minergate.com/blog/dashcoin-and-dash/)).
- `BCHABC → BCH`: On November 15 2018 Bitcoin Cash forked the second time, so, now there is `BCH` (for BCH ABC) and `BSV` (for BCH SV).
- `BCHSV → BSV`: This is a common substitution mapping for the Bitcoin Cash SV fork (some exchanges call it `BSV`, others call it `BCHSV`, we use the former).
- `DSH → DASH`: Try not to confuse symbols and currencies. The `DSH` (Dashcoin) is not the same as `DASH` (Dash). Some exchanges have `DASH` labelled inconsistently as `DSH`, the ccxt library does a correction for that as well (`DSH → DASH`), but only on certain exchanges that have these two currencies confused, whereas most exchanges have them both correct. Just remember that `DASH/BTC` is not the same as `DSH/BTC`.
- `XRB` → `NANO`: `NANO` is the newer code for RaiBlocks, thus, CCXT unified API will replace the older `XRB` with `NANO` where needed. https://hackernoon.com/nano-rebrand-announcement-9101528a7b76
- `USD` → `USDT`: Some exchanges, like Bitfinex, HitBTC and a few other name the currency as `USD` in their listings, but those markets are actually trading `USDT`. The confusion can come from a 3-letter limitation on symbol names or may be due to other reasons. In cases where the traded currency is actually `USDT` and is not `USD` – the CCXT library will perform `USD` → `USDT` conversion. Note, however, that some exchanges  have both `USD` and `USDT` symbols, for example, Kraken has a `USDT/USD` trading pair.

#### Notes On Naming Consistency

Each exchange has an associative array of substitutions for cryptocurrency symbolic codes in the `exchange.commonCurrencies` property, like:
```
'commonCurrencies' : {
    'XBT': 'BTC',
    'OPTIMISM': 'OP',
    // ... etc
}
```
where key represents actual name how exchange engine refers to that coin, and the value represents what you want to refer to it with through ccxt.

Sometimes the user may notice exotic symbol names with mixed-case words and spaces in the code. The logic behind having these names is explained by the rules for resolving conflicts in naming and currency-coding when one or more currencies have the same symbolic code with different exchanges:

- First, we gather all info available from the exchanges themselves about the currency codes in question. They usually have a description of their coin listings somewhere in their API or their docs, knowledgebases or elsewhere on their websites.
- When we identify each particular cryptocurrency standing behind the currency code, we look them up on [CoinMarketCap](https://coinmarketcap.com).
- The currency that has the greatest market capitalization of all wins the currency code and keeps it. For example, HOT often stand for either `Holo` or `Hydro Protocol`. In this case `Holo` retains the code `HOT`, and `Hydro Protocol` will have its name as its code, literally, `Hydro Protocol`. So, there may be trading pairs with symbols like `HOT/USD` (for `Holo`) and `Hydro Protocol/USD` – those are two different markets.
- If market cap of a particular coin is unknown or is not enough to determine the winner, we also take trading volumes and other factors into consideration.
- When the winner is determined all other competing currencies get their code names properly remapped and substituted within conflicting exchanges via `.commonCurrencies`. **Note, it should be defined before '.loadMarkets()' happens!**
- Unfortunately this is a work in progress, because new currencies get listed daily and new exchanges are added from time to time, so, in general this is a never-ending process of self-correction in a quickly changing environment, practically, in *"live mode"*. We are thankful for all reported conflicts and mismatches you may find.

#### Questions On Naming Consistency

_Is it possible for symbols to change?_

In short, yes, sometimes, but rarely. Symbolic mappings can be changed if that is absolutely required and cannot be avoided. However, all previous symbolic changes were related to resolving conflicts or forks. So far, there was no precedent of a market cap of one coin overtaking another coin with the same symbolic code in CCXT.

_Can we rely on always listing the same crypto with the same symbol?_

More or less ) First, this library is a work in progress, and it is trying to adapt to the everchanging reality, so there may be conflicts that we will fix by changing some mappings in the future. Ultimately, the license says "no warranties, use at your own risk". However, we don't change symbolic mappings randomly all over the place, because we understand the consequences and we'd want to rely on the library as well and we don't like to break the backward-compatibility at all.

If it so happens that a symbol of a major token is forked or has to be changed, then the control is still in the users' hands. The `exchange.commonCurrencies` property can be [overrided upon initialization or later](#overriding-exchange-properties-upon-instantiation), just like any other exchange property.  If a significant token is involved, we usually post instructions on how to retain the old behavior by adding a couple of lines to the constructor params.

#### Consistency Of Base And Quote Currencies

It depends on which exchange you are using, but some of them have a reversed (inconsistent) pairing of `base` and `quote`. They actually have base and quote misplaced  (switched/reversed sides). In that case you'll see a difference of parsed `base` and `quote` currency values with the unparsed `info` in the market substructure.

For those exchanges the ccxt will do a correction, switching and normalizing sides of base and quote currencies when parsing exchange replies. This logic is financially and terminologically correct. If you want less confusion, remember the following rule: **base is always before the slash, quote is always after the slash in any symbol and with any market**.


#### Contract Naming Conventions

We currently load spot markets with the unified `BASE/QUOTE` symbol schema into the `.markets` mapping, indexed by symbol. This would cause a naming conflict for futures and other derivatives that have the same symbol as their spot market counterparts. To accomodate both types of markets in the `.markets` we require the symbols between 'future' and 'spot' markets to be distinct, as well as the symbols between 'linear' and 'inverse' contracts to be distinct.

**Please, check this announcement: [Unified contract naming conventions](https://github.com/ccxt/ccxt/issues/10931)**

CCXT supports the following types of derivative contracts:

- `future` – for expiring futures contracts that have a delivery/settlement date [](https://en.wikipedia.org/wiki/Futures_contract)
- `swap` – for perpetual swap futures that don't have a delivery date [](https://en.wikipedia.org/wiki/Perpetual_futures)
- `option` – for option contracts (https://en.wikipedia.org/wiki/Option_contract)

##### Future

A future market symbol consists of the underlying currency, the quoting currency, the settlement currency and an arbitrary identifier. Most often the identifier is the settlement date of the future contract in `YYMMDD` format:


##### Perpetual Swap (Perpetual Future)


##### Option


### Unified Networks

| Network | CCXT Code  |
|---------------------------------------|--------------|
| Bitcoin                               | BTC          |
| Ethereum                              | ETH (For Ethereum) / ERC20 (For Tokens)          |
| Ripple                                | XRP          |
| Litecoin                              | LTC          |
| Dogecoin                              | DOGE         |
| Stellar                               | XLM          |
| Tron                                  | TRX (For TRX) / TRC20 (For Tokens)         |
| Ethereum Classic                      | ETC          |
| Zcash                                 | ZEC          |
| BSC (Binance Smart Chain)             | BEP20        |
| Monero                                | XMR          |
| Cardano                               | ADA          |
| Tezos                                 | XTZ          |
| Cosmos                                | ATOM         |
| Solana                                | SOL          |
| BNB Beacon Chain                      | BEP2         |
| Polkadot                              | DOT          |
| Algorand                              | ALGO         |
| Avalanche                             | AVAX         |
| Chainlink                             | LINK         |
| Bitcoin Cash                          | BCH          |
| Filecoin                              | FIL          |
| Kusama                                | KSM          |
| Elrond                                | EGLD         |
| THORChain                             | RUNE         |
| Internet Computer                     | ICP          |
| Near Protocol                         | NEAR         |
| Celo                                  | CELO         |
| Hedera Hashgraph                      | HBAR         |
| IOTA                                  | MIOTA        |
| Klaytn                                | KLAY         |
| VeChain                               | VET          |
| Theta Network                         | THETA        |
| Stacks                                | STX          |
| Bitcoin Lightning Network             | LIGHTNING    |
| Optimism                              | OPTIMISM     |
| Arbitrum                              | ARBITRUM     |
| zkSync                                | zkSync       |
| Polygon                               | MATIC        |
| Fantom                                | FTM          |
