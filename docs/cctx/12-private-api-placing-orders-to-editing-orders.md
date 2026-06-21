# Private API — Placing Orders → Editing Orders

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 431 lines · ~6,833 tokens · 27,332 chars
> **See also**: [Index](./README.md)

**Sections in this file:**

- [Placing Orders](#placing-orders)
- [Editing Orders](#editing-orders)

---

### Placing Orders

There are different types of orders that a user can send to the exchange, regular orders eventually land in the orderbook of a corresponding symbol, others orders may be more advanced. Here is a list outlining various types of orders:

- [Limit Orders](#limit-orders) – regular orders having an `amount` in base currency (how much you want to buy or sell) and a `price` in quote currency (for which price you want to buy or sell).
- [Market Orders](#market-orders) – regular orders having an `amount` in base currency (how much you want to buy or sell)
  - [Market Buys](#market-buys) – some exchanges require market buy orders with an `amount` in quote currency (how much you want to spend for buying)
- [Trigger Orders](#conditional-orders) aka *conditional orders* – an advanced type of order used to wait for a certain condition on a market and then react automatically: when a `triggerPrice` is reached, the trigger order gets triggered and then a regular limit `price` or market price order is placed, that eventually results in entering a position or exiting a position
- [Stop Loss Orders](#stop-loss-orders) – almost the same as trigger orders, but used to close a position to stop further losses on that position: when the price reaches `triggerPrice` then the stop loss order is triggered that results in placing another regular limit or market order to close a position at a specific limit `price` or at market price (a position with a stop loss order attached to it).
- [Take Profit Orders](#take-profit-orders) – a counterpart to stop loss orders, this type of order is used to close a position to take existing profits on that position: when the price reaches `triggerPrice` then the take profit order is triggered that results in placing another regular limit or market order to close a position at a specific limit `price` or at market price (a position with a take profit order attached to it).
- [StopLoss And TakeProfit Orders Attached To A Position](#stoploss-and-takeprofit-orders-attached-to-a-position) – advanced orders, consisting of three orders of types listed above: a regular limit or market order placed to enter a position with stop loss and/or take profit orders that will be placed upon opening that position and will be used to close that position later (when a stop loss is reached, it will close the position and will cancel its take profit counterpart, and vice versa, when a take profit is reached, it will close the position and will cancel its stop loss counterpart, these two counterparts are also known as "OCO orders – one cancels the other), apart from the `amount` (and `price` for the limit order) to open a position it will also require a `triggerPrice` for a stop loss order (with a limit `price` if it's a stop loss limit order) and/or a `triggerPrice` for a take profit order (with a limit `price` if it's a take profit limit order).
- [Trailing Orders](#trailing-orders) – an order that is automatically adjusted relative to an open position, `trailingAmount` can be set to trail a specified quote amount behind the open position or `trailingPercent` can be set to trail a specified percent behind the open position, when the market price of the position is equal to the trailing order this results in entering a new position or exiting a position depending on if the trailing order has the `reduceOnly` parameter set to true or not.

Placing an order always requires a `symbol` that the user has to specify (which market you want to trade).

To place an order use the `createOrder` method. You can use the `id` from the returned unified [order structure](#order-structure) to query the status and the state of the order later. If you need to place multiple orders simultaneously, you can check the availability of the `createOrders` method.



Parameters

- **symbol** (String) *required* Unified CCXT market symbol
  - Make sure the symbol in question exists with the target exchange and is available for trading.
- **side** *required* a string literal for the direction of your order.
  **Unified sides:**
  - `buy` give quote currency and receive base currency; for example, buying `BTC/USD` means that you will receive bitcoins for your dollars.
  - `sell` give base currency and receive quote currency; for example, buying `BTC/USD` means that you will receive dollars for your bitcoins.
- **type** a string literal type of order
  **Unified types:**
  - [market](#market-orders) not allowed by some exchanges, see [their docs](#exchanges) for details
  - [limit](#limit-orders)
  - see #custom-order-params and #other-order-types for non-unified types
- **amount**, how much of currency you want to trade usually, but not always, in units of the base currency of the trading pair symbol (the units for some exchanges are dependent on the side of the order: see their API docs for details.)
- **price** the price at which the order is to be fullfilled at in units of the quote currency (ignored in market orders)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- A successful order call returns a [order structure](#order-structure)

**Notes on createOrder**

- Some exchanges will allow to trade with limit orders only.

Some fields from the returned order structure may be `undefined / None / null` if that information is not returned from the exchange API's response. The user is guaranteed that the `createOrder` method will return a unified [order structure](#order-structure) that will contain at least the order `id` and the `info` (a raw response from the exchange "as is"):


##### Common pitfalls

- There is a common error that happens when creating orders for contract markets:

```
"must be greater than minimum amount precision of 1"
```

This error happens when the exchange is expecting a natural number of contracts (1,2,3, etc) in the `amount` argument of `createOrder`. The [market structure](#market-structure) has a key called `contractSize`. Each contract is worth a certain amount of the base asset that is determined by the `contractSize`. The number of contracts multiplied by the `contractSize` is equal to the base amount. `Base amount = (contracts * contractSize)` so to derive the number of contracts you should enter in the `amount` argument you can solve for contracts: `contracts = (Base amount / contractSize)`.

Here is an example of finding the `contractSize`:
```python
await exchange.loadMarkets()
symbol = 'BTC/USDT:USDT'
market = exchange.market(symbol)
print(market['contractSize'])

# Let's say you want to convert 0.5 BTC to the number of contracts:
number_contracts = round((0.5 * 1) / market['contractSize'])
```

#### Limit Orders

Limit orders placed on the order book of the exchange for a price specified by the trader. They are fullfilled(closed) when there are no orders in the same market at a better price, and another trader creates a [market order](#market-orders) or an opposite order for a price that matches or exceeds the price of the limit order.

Limit orders may not be fully filled. This happens when the filling order is for a smaller amount than the amount specified by the limit order.


#### Market Orders

*also known as*

- market price orders
- spot price orders
- instant orders

Market orders are executed immediately by fulfilling one of more already existing orders from the ask side of the exchanges order book. The orders that your market order fulfills are chosen from th top of the order book stack, meaning your market order is fulfilled at the best price available. When placing a market order you don't need to specify the price of the order, and if the price is specified, it will be ignored.

You are not guaranteed that the order will be executed for the price you observe prior to placing your order. There are multiple reasons for this, including:

- **price slippage** a slight change of the price for the traded market while your order is being executed. Reasons for price slippage include, but are not limited to

    - networking roundtrip latency
    - high loads on the exchange
    - price volatility

- **unequivocal order sizes** if a market order is for an amount that is larger than the size of the top order on the order book, then after the top order is filled, the market order will proceed to fill the next order in the order book, which means the market order is filled at multiple prices


**Note, that some exchanges will not accept market orders (they allow limit orders only).** In order to detect programmatically if the exchange in question does support market orders or not, you can use the `.has['createMarketOrder']` exchange property:


```python
if exchange.has['createMarketOrder']:
    ...
```

#### Market Buys

In general, when placing a `market buy` or `market sell` order the user has to specify just the amount of the base currency to buy or sell. However, with some exchanges market buy orders implement a different approach to calculating the value of the order.

Suppose you're trading BTC/USD and the current market price for BTC is over 9000 USD. For a market buy or market sell you could specify an `amount` of 2 BTC and that would result in _plus or minus_ 18000 USD (more or less ;)) on your account, depending on the side of the order.

**With market buys some exchanges require the total cost of the order in the quote currency!** The logic behind it is simple, instead of taking the amount of base currency to buy or sell some exchanges operate with _"how much quote currency you want to spend on buying in total"_.

To place a market buy order with those exchanges you would not specify an amount of 2 BTC, instead you should somehow specify the total cost of the order, that is, 18000 USD in this example. The exchanges that treat `market buy` orders in this way have an exchange-specific option `createMarketBuyOrderRequiresPrice` that allows specifying the total cost of a `market buy` order in two ways.

The first is the default and if you specify the `price` along with the `amount` the total cost of the order would be calculated inside the lib from those two values with a simple multiplication (`cost = amount * price`). The resulting `cost` would be the amount in USD quote currency that will be spent on this particular market buy order.


The second alternative is useful in cases when the user wants to calculate and specify the resulting total cost of the order himself. That can be done by setting the `createMarketBuyOrderRequiresPrice` option to `false` to switch it off:


More about it:

- https://github.com/ccxt/ccxt/issues/564#issuecomment-347458566
- https://github.com/ccxt/ccxt/issues/4914#issuecomment-478199357
- https://github.com/ccxt/ccxt/issues/4799#issuecomment-470966769
- https://github.com/ccxt/ccxt/issues/5197#issuecomment-496270785

#### Emulating Market Orders With Limit Orders

It is also possible to emulate a `market` order with a `limit` order.

**WARNING this method can be risky due to high volatility, use it at your own risk and only use it when you know really well what you're doing!**

Most of the time a `market sell` can be emulated with a `limit sell` at a very low price – the exchange will automatically make it a taker order for market price (the price that is currently in your best interest from the ones that are available in the order book). When the exchange detects that you're selling for a very low price it will automatically offer you the best buyer price available from the order book. That is effectively the same as placing a market sell order. Thus market orders can be emulated with limit orders (where missing).

The opposite is also true – a `market buy` can be emulated with a `limit buy` for a very high price. Most exchanges will again close your order for best available price, that is, the market price.

However, you should never rely on that entirely, **ALWAYS test it with a small amount first!** You can try that in their web interface first to verify the logic. You can sell the minimal amount at a specified limit price (an affordable amount to lose, just in case) and then check the actual filling price in trade history.

#### Limit Orders

Limit price orders are also known as *limit orders*. Some exchanges accept limit orders only. Limit orders require a price (rate per unit) to be submitted with the order. The exchange will close limit orders if and only if market price reaches the desired level.


<a name="Stop Orders" id="Stop Orders"></a><a name="Trigger Orders" id="Trigger Orders"></a>

#### Conditional Orders

Coming from traditional trading, the term "Stop order" has been a bit ambigious, so instead of it, in CCXT we use term "Trigger" order. When symbol's price reaches your "trigger"("stop") price, the order is activated as `market` or `limit` order, depending which one you had chosen.

We have different classification of trigger orders:
1) standalone [Trigger order](#trigger-order) to buy/sell coin (open/close position)
2) standalone [Stop Loss](#stop-loss-orders) or [Take Profit](#take-profit-orders) designed to close open positions.
3) a Stop Loss or Take Profit order attached to a primary order ([Conditional Trigger Order](#stopLoss-and-takeProfit-orders-attached-to-a-position)).


##### Trigger order

Traditional "stop" order (which you might see across exchanges' websites) is now called "trigger" order across CCXT library. Implemented by adding a `triggerPrice` parameter. They are independent basic trigger orders that can open or close a position.

* To ensure exchange supports this functionality, check `exchange.features` or use helper method `exchange.featureValue('BTC/USDT', 'createOrder', 'triggerPrice')`.
* Typically, it is activated when price of the underlying asset/contract crosses the `triggerPrice` from **any direction**. However, some exchanges' API require to set `triggerDirection` too, which triggers order depending whether price is above or below `triggerPrice`. For example, if you want to trigger  limit order (buy 0.1 `ETH` at limit price `1500`) once pair price crosses `1700`:



```python
params = {
    'triggerPrice': 1700,
}
order = exchange.create_order('ETH/USDT', 'market', 'buy', 0.1, 1500, params)
```
<a name="trigger-direction" id="trigger-direction"></a>
Typically, exchange automatically determines `triggerPrice`'s direction (whether it is "above" or "below" current price), however, some exchanges require that you provide `triggerDirection` with either `ascending` or `descending` values:

```
params = {
    'triggerPrice': 1700,
    'triggerDirection': 'ascending', // order will be triggered when price goes upward and touches 1700
}
```

Note, you can also add `reduceOnly: true` param to the trigger order (with a possible `triggerDirection: 'ascending/descending'` param), so it would act as "stop-loss" or "take-profit" order. However, for some exchanges we support "stop-loss" and "take-profit" trigger order types, which automatically involve `reduceOnly` and `triggerDirection` handling (see them below).

##### Stop Loss Orders

The same as Trigger Orders, but the direction matters. Implemented by specifying a `stopLossPrice` parameter (for the stop loss triggerPrice), and also automatically implemented `triggerDirection` on behalf of user, so instead of regular Trigger Order, you can use this as an alternative.

* To ensure exchange supports this functionality, check `exchange.features` or use helper method `exchange.featureValue('BTC/USDT', 'createOrder', 'stopLossPrice')`.

Suppose you entered a long position (you bought) at 1000 and want to protect yourself from losses from a possible price drop below 700. You would place a stop loss order with triggerPrice at 700. For that stop loss order either you would specify a limit price or it will be executed at market price.

```
    | price  | amount
----|----------------
    |  1500 | 200
    |  1400 | 300
  a |  1300 | 100
  s |  1200 | 200
  k |  1100 | 300
    |  1000 | 100 <--- you bought to enter a long position here at 1000
    |   900 | 100
----|---------------- last price is 900
    |   800 | 100
    |   700 | 200 <------- you place a stop loss order here at 700 <----------------------+
  b |   600 | 100       when your stopLossPrice is reached from above                     |
  i |   500 | 300   it will close your position at market price below 700 ----------------+
  d |   400 | 200 <- or it will be executed at your limit price lower that stopLossPrice -+
    |   300 | 100
    |   200 | 100
```

Suppose you entered a short position (you sold) at 700 and want to protect yourself from losses from a possible price pump above 1300. You would place a stop loss order with triggerPrice at 1300. For that stop loss order either you would specify a limit price or it will be executed at market price.

```
    | price  | amount
----|----------------
    |  1500 | 200
    |  1400 | 300 <------------------------------------------------------------------------+
  a |  1300 | 100 <------ you place a stop loss order here at 1300 <---------------------+ |
  s |  1200 | 200      when your stopLossPrice is reached from below                     | |
  k |  1100 | 300   it will close your position at market price above 1300 --------------+ |
    |  1000 | 100    or it will be executed at your limit price higher than stopLossPrice -+
    |   900 | 100
----|---------------- last price is 900 (you sold at 700)
    |   800 | 100
    |   700 | 200 <--- you sold to enter a short position here at 700
  b |   600 | 100
  i |   500 | 300
  d |   400 | 200
    |   300 | 100
    |   200 | 100
```

Stop Loss orders are activated when the price of the underlying asset/contract:

* drops below the `stopLossPrice` from above, for sell orders. (eg: to close a long position, and avoid further losses)
* rises above the `stopLossPrice` from below, for buy orders (eg: to close a short position, and avoid further losses)



```python
# for a stop loss order
params = {
    'stopLossPrice': 55.45,  # your stop loss price
}

order = exchange.create_order (symbol, type, side, amount, price, params)
```

##### Take Profit Orders

The same as Stop Loss Orders, but the direction matters. Implemented by specifying a `takeProfitPrice` parameter (for the take profit triggerPrice).

Suppose you entered a long position (you bought) at 1000 and want to get your profits from a possible price pump above 1300. You would place a take profit order with triggerPrice at 1300. For that take profit order either you would specify a limit price or it will be executed at market price.

```
    | price  | amount
----|----------------
    |  1500 | 200
    |  1400 | 300 <------------------------------------------------------------------------------+
  a |  1300 | 100 <--- it will close your position at market price above 1300                    |
  s |  1200 | 200        when your takeProfitPrice is reached from below                         |
  k |  1100 | 300   or it will be executed at your limit price higher than your takeProfitPrice -+
    |  1000 | 100 <-  you bought to enter a long position here at 1000
    |   900 | 100
----|---------------- last price is 900
    |   800 | 100
    |   700 | 200
  b |   600 | 100
  i |   500 | 300
  d |   400 | 200
    |   300 | 100
    |   200 | 100
```

Suppose you entered a short position (you sold) at 700 and want to get your profits from a possible price drop below 600. You would place a take profit order with triggerPrice at 600. For that take profit order either you would specify a limit price or it will be executed at market price.

```
    | price  | amount
----|----------------
    |  1500 | 200
    |  1400 | 300
  a |  1300 | 100
  s |  1200 | 200
  k |  1100 | 300
    |  1000 | 100
    |   900 | 100
----|---------------- last price is 900 (you sold at 700)
    |   800 | 100
    |   700 | 200 <--- you sold to enter a short position here at 700
  b |   600 | 100 <------ you place a take profit order here at 600
  i |   500 | 300     when your takeProfitPrice is reached from above
  d |   400 | 200     it will be close your position at market price below 600
    |   300 | 100 <- or it will be executed at your limit price lower than your takeProfitPrice
    |   200 | 100
```

Take Profit orders are activated when the price of the underlying:

* rises above the `takeProfitPrice` from below, for sell orders (eg: to close a long position, at a profit)
* drops below the `takeProfitPrice` from above, for buy orders (eg: to close a short position, at a profit)



```python
# for a take profit order
params = {
    'takeProfitPrice': 120.45,  # your take profit price
}

order = exchange.create_order (symbol, type, side, amount, price, params)
```

#### StopLoss And TakeProfit Orders Attached To A Position

**Take Profit** / **Stop Loss** Orders which are tied to a position-opening primary order. Implemented by supplying a dictionary parameters for `stopLoss` and `takeProfit` describing each respectively.

* By default stopLoss and takeProfit order amounts will be the same as primary order but in the opposite direction.
* Attached trigger orders are conditional on the primary order being executed.
* Not supported by all exchanges. To check whether stop-loss is supported, use such approach:
```
exchange.featureValue('BTC/USDT', 'createOrder', 'stopLoss') // if stopLoss supported
exchange.featureValue('BTC/USDT', 'createOrder', 'stopLoss.price') // if limit price is supported for stoploss
```



```python
params = {
    'stopLoss': {
        'triggerPrice': 12.34,  # at what price it will trigger
        'price': 12.00,  # if exchange supports, 'price' param would be limit price (for market orders, don't include this param)
    },
    'takeProfit': {
        # similar params here
    }
}
order = exchange.create_order ('SOL/USDT', 'limit', 'buy', 0.5, 13, params)
```

For exchanges, where it is not possible to use attached SL &TP, after submitting an entry order, you can immediatelly submit another order (even though position might not be open yet) with `stopLossPrice/takeProfitPrice` in `parmas`, (or `triggerPrice` and `reduceOnly: true`),  so it can still act as a stoploss order for your upcoming position (note, this approach might not work for some exchanges).

Example:

```
    symbol = 'ADA/USDT:USDT'
    main_order = await binance.create_order(symbol, 'market', 'buy', 50) # open position
    tp_order = await binance.create_order(symbol, 'limit', 'sell', 50, 1.5, {"takeProfitPrice": 1.6}) # take profit order
    sl_order = await binance.create_order(symbol, 'limit', 'sell', 50, 0.24, {"stopLossPrice": 0.25}) # stop loss order
```

#### Trailing Orders

**Trailing** Orders trail behind an open position. Implemented by supplying float parameters for `trailingPercent` or `trailingAmount`.

* A trailing order continually adjusts the order price at a fixed percent or fixed quote amount away from the current market price.
* A trailing order trails behind a position as it moves in one direction, but not in the opposite direction.
* If the position value rises, the trailing order changes, but if the position value drops the trailing order stays the same until the order is executed.
* A trailing order can be placed independently after opening a position.
* Implemented by filling in either the `trailingPercent` or `trailingAmount` parameter depending on the exchange.
* The price argument can be used as the `trailingTriggerPrice`, and the type argument can be used to differentiate between limit and market trailing orders if needed.

*Not supported by all exchanges.*

*Note: This is still under unification and is a work in progress*



```python
symbol = 'BTC/USDT:USDT'
type = 'market'
side = 'sell'
amount = 1.0
price = None
params = {
    'trailingPercent': 1.0, # percentage away from the current market price 1.0 is equal to 1%
    # 'trailingAmount': 100.0, # quote amount away from the current market price
    # 'trailingTriggerPrice': 44500.0, # the price to trigger activating a trailing stop order
    # 'reduceOnly': True, # set to True if you want to close a position, set to False if you want to open a new position
}
order = exchange.create_order (symbol, type, side, amount, price, params)
```

#### Custom Order Params

Some exchanges allow you to specify optional parameters for your order. You can pass your optional parameters and override your query with an associative array using the `params` argument to your unified API call. All custom params are exchange-specific, of course, and aren't interchangeable, do not expect those custom params for one exchange to work with another exchange.



```python
# add a custom order flag
kraken.create_market_buy_order('BTC/USD', 1, {'trading_agreement': 'agree'})
```

##### User-defined `clientOrderId`


The user can specify a custom `clientOrderId` field can be set upon placing orders with the `params`. Using the `clientOrderId` one can later distinguish between own orders. This is only available for the exchanges that do support `clientOrderId` at this time. For the exchanges that don't support it will either throw an error upon supplying the `clientOrderId` or will ignore it setting the `clientOrderId` to `undefined/None/null`.



```python
exchange.create_order(symbol, type, side, amount, price, {
    'clientOrderId': 'World',
})
```

##### Hedge mode for order

If exchange supports [feature](#features) for `hedged` orders, user can pass `params['hedged'] = true` in `createOrder` to open a `hedged` position instead of default `one-way` mode order. However, if exchange supports `.has['setPositionMode']` then those exchanges might not support `hedged` param directly through `createOrder`, instead on such exchange you need to change the account-mode at first using [setPositionMode()](#set-position-mode) and then run `createOrder` (without `hedged` param) and it will place hedged order by default.



### Editing Orders

To edit an order, you can use the `editOrder` method


Parameters

- **id** (String) *required* Order id (e.g. `1645807945000`)
- **symbol** (String) *required* Unified CCXT market symbol
- **side** (String) *required* the direction of your order.
  **Unified sides:**
  - `buy` give quote currency and receive base currency; for example, buying `BTC/USD` means that you will receive bitcoins for your dollars.
  - `sell` give base currency and receive quote currency; for example, buying `BTC/USD` means that you will receive dollars for your bitcoins.
- **type** (String) *required* type of order
  **Unified types:**
  - [`market`](#market-orders) not allowed by some exchanges, see [their docs](#exchanges) for details
  - [`limit`](#limit-orders)
  - see #custom-order-params and #other-order-types for non-unified types
- **amount** (Number) *required* how much of currency you want to trade usually, but not always, in units of the base currency of the trading pair symbol (the units for some exchanges are dependent on the side of the order: see their API docs for details.)
- **price** (Float) the price at which the order is to be fullfilled at in units of the quote currency (ignored in market orders)
- **params** (Dictionary) Extra parameters specific to the exchange API endpoint (e.g. `{"settle": "usdt"}`)

Returns

- An [order structure](#order-structure)
