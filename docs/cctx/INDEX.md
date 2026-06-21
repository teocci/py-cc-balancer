# CCXT Manual — Agent Navigation Index

> **Purpose**: Help AI agents find the right document chunk in **one hop** without scanning every file.
> **Use**: Match the user's intent / API symbol / task keyword against the tables below, then load only the linked file.
> **Source**: [ccxt/wiki/Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) — Python-only, language noise removed.
> **Stats**: 18 chunks · 4,379 lines · ~62K tokens total · single-file fallback at [`_ccxt-manual-python-only.md`](./_ccxt-manual-python-only.md) (~62K tokens).

---

## 🚀 Fast Start — Pick One Question

| If the user is asking… | Go to |
|---|---|
| "How do I install / what is ccxt / what's the architecture?" | [`01-overview.md`](./01-overview.md) |
| "How do I create an exchange instance / set API keys / use testnet?" | [`02-exchanges.md`](./02-exchanges.md) |
| "What exchanges are supported?" | [`02-exchanges.md`](./02-exchanges.md) (compact ID list at top) |
| "How do markets / symbols / currencies work? What's precision?" | [`03-markets-intro-to-symbols-and-market-ids.md`](./03-markets-intro-to-symbols-and-market-ids.md) |
| "What's the difference between market id and unified symbol?" | [`03-markets-intro-to-symbols-and-market-ids.md`](./03-markets-intro-to-symbols-and-market-ids.md) → *Symbols And Market Ids* |
| "How do I get the order book / ticker / OHLCV / public trades?" | [`07-public-api-intro-to-exchange-status.md`](./07-public-api-intro-to-exchange-status.md) |
| "How do funding rates / borrow rates / leverage tiers / open interest work?" | [`08-public-api-borrow-rates-to-long-short-ratio.md`](./08-public-api-borrow-rates-to-long-short-ratio.md) |
| "How do I authenticate / set up API keys / override nonce?" | [`10-private-api-intro-to-account-balance.md`](./10-private-api-intro-to-account-balance.md) |
| "How do I query my orders / what's the order structure?" | [`11-private-api-intro-to-order-structure.md`](./11-private-api-intro-to-order-structure.md) |
| "How do I place / edit an order? Stop-loss / take-profit / trigger orders?" | [`12-private-api-placing-orders-to-editing-orders.md`](./12-private-api-placing-orders-to-editing-orders.md) |
| "How do I cancel an order?" | [`13-private-api-canceling-orders.md`](./13-private-api-canceling-orders.md) |
| "How do I get my trade history / ledger / deposits / withdrawals?" | [`14-private-api-my-trades-to-deposit-addresses.md`](./14-private-api-my-trades-to-deposit-addresses.md) |
| "How do I transfer funds / check fees / set leverage / set margin mode?" | [`15-private-api-transfers-to-leverage.md`](./15-private-api-transfers-to-leverage.md) |
| "How do futures / contracts / positions / proxy / string-math work?" | [`16-private-api-contract-trading-to-string-math.md`](./16-private-api-contract-trading-to-string-math.md) |
| "I'm getting an error / what does this exception mean / how to retry?" | [`17-error-handling.md`](./17-error-handling.md) |
| "Something doesn't work / how do I debug / verbose mode?" | [`18-troubleshooting.md`](./18-troubleshooting.md) |
| "I need the implicit (auto-generated) REST endpoint methods" | [`05-implicit-api.md`](./05-implicit-api.md) |
| "How does pagination work / how to override unified params?" | [`06-unified-api.md`](./06-unified-api.md) |

---

## 🔍 API Symbol → File Map

Look up the method / property the user mentioned. Load the linked file.

### Public market data methods

> **Convention note**: The manual documents methods in camelCase (e.g. `fetchOrderBook`). In Python ccxt, the same method is `fetch_order_book`. Both forms work — the snake_case is the Python alias. Below, `camelCase → snake_case` is shown.

| Symbol | File | Notes |
|---|---|---|
| `fetchTicker → fetch_ticker(symbol)` | [`07`](./07-public-api-intro-to-exchange-status.md) | Single ticker |
| `fetchTickers → fetch_tickers(symbols=None)` | [`07`](./07-public-api-intro-to-exchange-status.md) | Many / all tickers |
| `fetchOrderBook → fetch_order_book(symbol, limit=None, params={})` | [`07`](./07-public-api-intro-to-exchange-status.md) | Bid/ask stack |
| `fetchOHLCV → fetch_ohlcv(symbol, timeframe='1m', since=None, limit=None, params={})` | [`07`](./07-public-api-intro-to-exchange-status.md) | Candlesticks |
| `fetchMarkOHLCV → fetch_mark_ohlcv(...)` / `fetchIndexOHLCV → fetch_index_ohlcv(...)` | [`07`](./07-public-api-intro-to-exchange-status.md) | Mark / Index OHLCV |
| `fetchTrades → fetch_trades(symbol, since=None, limit=None, params={})` | [`07`](./07-public-api-intro-to-exchange-status.md) | Public trade flow |
| `fetchStatus → fetch_status(params={})` | [`07`](./07-public-api-intro-to-exchange-status.md) | Exchange status |
| `fetchTime → fetch_time(params={})` | [`07`](./07-public-api-intro-to-exchange-status.md) | Server time |
| `fetchFundingRate → fetch_funding_rate(symbol)` / `fetchFundingRateHistory → fetch_funding_rate_history(...)` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | Perp funding |
| `fetchFundingInterval → fetch_funding_interval(symbol)` / `fetchFundingIntervals → fetch_funding_intervals(...)` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchBorrowRate → fetch_borrow_rate(...)` / `fetchBorrowRateHistory → fetch_borrow_rate_history(...)` (also `fetchCrossBorrowRate(s)`, `fetchIsolatedBorrowRate(s)`) | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchLeverageTiers → fetch_leverage_tiers(...)` / `fetchMarketLeverageTiers → fetch_market_leverage_tiers(...)` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchOpenInterest → fetch_open_interest(...)` / `fetchOpenInterestHistory → fetch_open_interest_history(...)` / `fetchOpenInterests` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchVolatilityHistory → fetch_volatility_history(...)` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | Options |
| `fetchUnderlyingAssets → fetch_underlying_assets(...)` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | Options |
| `fetchSettlementHistory → fetch_settlement_history(...)` / `fetchMySettlementHistory` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchLiquidations → fetch_liquidations(...)` / `fetchMyLiquidations` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchGreeks → fetch_greeks(...)` / `fetchAllGreeks` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | Options |
| `fetchOptionChain → fetch_option_chain(...)` / `fetchOption` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | Options |
| `fetchLongShortRatio → fetch_long_short_ratio(...)` / `fetchLongShortRatioHistory` | [`08`](./08-public-api-borrow-rates-to-long-short-ratio.md) | |
| `fetchADLRank → fetch_adl_rank(...)` | [`09`](./09-public-api-auto-de-leverage.md) | |

### Private / authenticated methods

> Same camelCase → snake_case convention as above.

| Symbol | File | Notes |
|---|---|---|
| `checkRequiredCredentials → check_required_credentials()` | [`10`](./10-private-api-intro-to-account-balance.md) | Verify keys configured |
| `fetchBalance → fetch_balance(params={})` | [`10`](./10-private-api-intro-to-account-balance.md) | Account balance |
| `fetchAccounts → fetch_accounts(params={})` | [`10`](./10-private-api-intro-to-account-balance.md) | Subaccounts |
| `fetchOrder → fetch_order(id, symbol=None, params={})` | [`11`](./11-private-api-intro-to-order-structure.md) | Single order |
| `fetchOrders → fetch_orders(symbol=None, since=None, limit=None, params={})` | [`11`](./11-private-api-intro-to-order-structure.md) | All orders |
| `fetchOpenOrders → fetch_open_orders(...)` / `fetchClosedOrders → fetch_closed_orders(...)` / `fetchCanceledOrders → fetch_canceled_orders(...)` | [`11`](./11-private-api-intro-to-order-structure.md) | Filtered lists |
| `fetchOpenOrder(id, ...) → fetch_open_order(...)` / `fetchClosedOrder(id, ...) → fetch_closed_order(...)` | [`11`](./11-private-api-intro-to-order-structure.md) | Single filtered |
| `createOrder → create_order(symbol, type, side, amount, price=None, params={})` | [`12`](./12-private-api-placing-orders-to-editing-orders.md) | Limit / market / stop / TP / SL |
| `createMarketBuyOrder → create_market_buy_order(...)` / `createMarketSellOrder → create_market_sell_order(...)` | [`12`](./12-private-api-placing-orders-to-editing-orders.md) | Convenience wrappers |
| `createPostOnlyOrder → create_post_only_order(...)` | [`12`](./12-private-api-placing-orders-to-editing-orders.md) | Post-only limit |
| `editOrder → edit_order(id, symbol, type, side, amount=None, price=None, params={})` | [`12`](./12-private-api-placing-orders-to-editing-orders.md) | Modify live order |
| `cancelOrder → cancel_order(id, symbol=None, params={})` | [`13`](./13-private-api-canceling-orders.md) | |
| `cancelAllOrders → cancel_all_orders(symbol=None, params={})` / `cancelAllOrdersAfter → cancel_all_orders_after(...)` | [`13`](./13-private-api-canceling-orders.md) | |
| `cancelOrders(ids, symbol=None, params={}) → cancel_orders(...)` | [`13`](./13-private-api-canceling-orders.md) | Batch |
| `fetchMyTrades → fetch_my_trades(symbol=None, since=None, limit=None, params={})` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | Personal trades |
| `fetchOrderTrades → fetch_order_trades(id, symbol=None, ...)` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | Trades for one order |
| `fetchLedger → fetch_ledger(code=None, since=None, limit=None, params={})` / `fetchLedgerEntry` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | Account ledger |
| `fetchDeposits → fetch_deposits(code=None, since=None, limit=None, params={})` / `fetchDeposit` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | |
| `fetchWithdrawals → fetch_withdrawals(code=None, since=None, limit=None, params={})` / `fetchWithdrawal` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | |
| `fetchTransactions → fetch_transactions(code=None, since=None, limit=None, params={})` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | Combined deposits+withdrawals |
| `fetchDepositAddress → fetch_deposit_address(code, params={})` / `fetchDepositAddressesByNetwork` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | |
| `withdraw(code, amount, address, tag=None, params={})` | [`14`](./14-private-api-my-trades-to-deposit-addresses.md) | |
| `transfer(code, amount, fromAccount, toAccount, params={})` / `transferIn` / `transferOut` | [`15`](./15-private-api-transfers-to-leverage.md) | Subaccount transfer |
| `fetchTradingFee → fetch_trading_fee(...)` / `fetchTradingFees → fetch_trading_fees(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | |
| `fetchTransactionFee → fetch_transaction_fee(...)` / `fetchTransactionFees → fetch_transaction_fees(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | |
| `fetchDepositWithdrawFee → fetch_deposit_withdraw_fee(...)` / `fetchDepositWithdrawFees` | [`15`](./15-private-api-transfers-to-leverage.md) | |
| `fetchBorrowInterest → fetch_borrow_interest(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | |
| `borrowCrossMargin → borrow_cross_margin(...)` / `borrowIsolatedMargin → borrow_isolated_margin(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | borrow_margin variants |
| `repayCrossMargin → repay_cross_margin(...)` / `repayIsolatedMargin → repay_isolated_margin(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | repay_margin variants |
| `fetchMarginMode → fetch_margin_mode(symbol=None, params={})` / `fetchMarginModes` | [`15`](./15-private-api-transfers-to-leverage.md) | |
| `setMarginMode → set_margin_mode(marginMode, symbol=None, params={})` | [`15`](./15-private-api-transfers-to-leverage.md) | `cross` / `isolated` |
| `setMargin → set_margin(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | Adjust margin balance |
| "Set Leverage" section (uses `setLeverage → set_leverage(leverage, symbol=None, params={})`) | [`15`](./15-private-api-transfers-to-leverage.md) → *Set Leverage* | The section is titled "Set Leverage"; the method is documented under that heading. Also related: `addMargin`, `reduceMargin`, `setMargin` (adjust margin on open position) |
| `fetchLeverage → fetch_leverage(...)` / `fetchLeverages → fetch_leverages(...)` | [`15`](./15-private-api-transfers-to-leverage.md) | |
| `fetchPosition → fetch_position(symbol, params={})` | [`16`](./16-private-api-contract-trading-to-string-math.md) | Futures positions |
| `fetchPositions → fetch_positions(symbols=None, since=None, limit=None, params={})` / `fetchAccountPositions` | [`16`](./16-private-api-contract-trading-to-string-math.md) | |
| `fetchPositionHistory → fetch_position_history(...)` / `fetchPositionsHistory` | [`16`](./16-private-api-contract-trading-to-string-math.md) | |
| `fetchPositionADLRank → fetch_position_adl_rank(...)` / `fetchPositionsADLRank` | [`16`](./16-private-api-contract-trading-to-string-math.md) | |
| `fetchFundingHistory → fetch_funding_history(...)` | [`16`](./16-private-api-contract-trading-to-string-math.md) | |
| `fetchConvertQuote → fetch_convert_quote(...)` / `fetchConvertTrade → fetch_convert_trade(...)` / `createConvertTrade → create_convert_trade(...)` / `fetchConvertTradeHistory` | [`16`](./16-private-api-contract-trading-to-string-math.md) | Conversion / one-click convert |

### Properties & helpers

| Symbol | File | Notes |
|---|---|---|
| `exchange.markets` / `exchange.currencies` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | Loaded market dict |
| `exchange.symbols` / `exchange.ids` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | |
| `exchange.market(symbol)` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | Lookup market by symbol |
| `exchange.market_id(symbol)` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | Get raw exchange id |
| `exchange.load_markets(reload=False, params={})` / `loadMarkets` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | Required before most calls |
| `setMarketsFromExchange → set_markets_from_exchange(other)` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) → *Sharing Markets Between Exchange Instances* | Share markets between instances |
| `exchange.amount_to_precision(symbol, amount)` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | |
| `exchange.price_to_precision(symbol, price)` | [`03`](./03-markets-intro-to-symbols-and-market-ids.md) | |
| `exchange.has` (feature dict) | [`06`](./06-unified-api.md), [`11`](./11-private-api-intro-to-order-structure.md) | Capability map |
| `exchange.features` | [`02`](./02-exchanges.md) | Detailed feature flags |
| `exchange.timeframes` | [`07`](./07-public-api-intro-to-exchange-status.md) | Allowed OHLCV timeframes |
| `exchange.options` | [`02`](./02-exchanges.md) | Exchange-specific config |
| `exchange.requiredCredentials` | [`10`](./10-private-api-intro-to-account-balance.md) | |
| `exchange.last_response_headers` | [`06`](./06-unified-api.md) | |
| `exchange.milliseconds()` / `exchange.seconds()` / `exchange.microseconds()` | [`06`](./06-unified-api.md) | Nonce helpers |
| `exchange.enableRateLimit` / `exchange.rateLimit` | [`02`](./02-exchanges.md) | Rate limiter config |
| `exchange.set_sandbox_mode(enable)` / `setSandboxMode` | [`02`](./02-exchanges.md) | Testnet switch |
| `exchange.verbose = True` | [`18`](./18-troubleshooting.md) | Debug HTTP logs |
| Implicit methods — `privatePutOrderIdCancel → private_put_order_id_cancel`, `publicGetTickerPair → public_get_ticker_pair`, etc. | [`05`](./05-implicit-api.md) | Auto-generated from `.api` |

### Async / Pro variants

| Symbol | File |
|---|---|
| `import ccxt.async_support as ccxt` (asyncio) | [`05`](./05-implicit-api.md) → *Synchronous vs Asynchronous Calls* |
| `ccxt.pro.*` (WebSocket streams) | Not in this manual — see [CCXT Pro docs](https://ccxt.pro) |

---

## 🎯 Task-Based Decision Tree

```
User intent
│
├── Setup / config
│   ├── "install / what is ccxt" ─────────────────► 01-overview.md
│   ├── "create instance / API keys / testnet" ────► 02-exchanges.md
│   ├── "rate limit / DDoS protection / Cloudflare" ► 02-exchanges.md → Rate Limit
│   └── "share markets between instances" ─────────► 04-markets-market-cache-force-reload.md
│
├── Market data (public, no auth)
│   ├── "markets / symbols / currencies / precision" ► 03-markets-...md
│   ├── "order book / ticker / OHLCV / trades" ────► 07-public-api-intro-...md
│   ├── "funding / borrow / leverage tiers / OI / greeks / options / LSR" ► 08-...md
│   └── "auto de-leverage" ────────────────────────► 09-public-api-auto-de-leverage.md
│
├── Trading (private, needs auth)
│   ├── "authenticate / nonce / subaccounts / balance" ► 10-private-api-intro-...md
│   ├── "query my orders / order structure" ───────► 11-private-api-intro-to-order-structure.md
│   ├── "create / edit order (limit/market/stop/TP/SL)" ► 12-...-placing-orders-...md
│   ├── "cancel order / cancel all" ───────────────► 13-private-api-canceling-orders.md
│   ├── "my trades / ledger / deposits / withdrawals" ► 14-...-my-trades-...md
│   ├── "transfer / fees / borrow / repay / margin / leverage" ► 15-...-transfers-...md
│   └── "positions / funding history / proxy / contract math" ► 16-...-contract-...md
│
├── Meta-API
│   ├── "implicit REST methods (private_get_*, public_post_*, ...)" ► 05-implicit-api.md
│   ├── "pagination / params override / async" ────► 06-unified-api.md
│   └── "what methods does this exchange support?" ► exchange.has (06) + exchange.features (02)
│
└── Troubleshooting
    ├── "exception hierarchy / retry / NetworkError / ExchangeError" ► 17-error-handling.md
    └── "verbose mode / debugging / FAQ links" ────► 18-troubleshooting.md
```

---

## 🏷️ Keyword Index (lowercased)

Scan for keywords the user might mention. File numbers in parens.

| Keyword(s) | File(s) |
|---|---|
| `api key`, `secret`, `apiKey`, `nonce` | 02, 10 |
| `async`, `asyncio`, `aiohttp`, `async_support` | 05 |
| `balance`, `free`, `used`, `total` | 10 |
| `bid`, `ask`, `spread`, `order book`, `depth` | 07 |
| `candlestick`, `ohlcv`, `timeframe`, `1m`, `1h`, `1d` | 07 |
| `mark price`, `index price`, `premium index` | 07 |
| `ticker`, `last`, `open`, `high`, `low`, `close`, `vwap`, `bidVolume`, `askVolume` | 07 |
| `funding rate`, `funding interval`, `perpetual`, `swap` | 08, 16 |
| `borrow rate`, `leverage tier`, `open interest`, `OI` | 08 |
| `volatility`, `greeks`, `delta`, `gamma`, `theta`, `vega`, `option chain` | 08 |
| `liquidation`, `settlement`, `underlying` | 08 |
| `long short ratio`, `LSR` | 08 |
| `auto de-leverage`, `ADL` | 09, 16 |
| `order`, `createOrder`, `create_order`, `limit`, `market` | 11, 12 |
| `stop loss`, `SL`, `stopLossPrice`, `take profit`, `TP`, `takeProfitPrice`, `triggerPrice`, `triggerDirection` | 12 |
| `post-only`, `ioc`, `fok`, `reduceOnly`, `clientOrderId` | 12 |
| `cancel`, `cancelOrder`, `cancel_order`, `cancel_all_orders` | 13 |
| `trade`, `my trades`, `fetch_my_trades`, `fetch_order_trades` | 14 |
| `ledger`, `ledger entry` | 14 |
| `deposit`, `withdraw`, `withdrawal`, `transaction`, `fetch_deposits`, `fetch_withdrawals`, `fetch_transactions` | 14 |
| `deposit address`, `fetch_deposit_address` | 14 |
| `transfer`, `fromAccount`, `toAccount`, `subaccount` | 15 |
| `fee`, `trading fee`, `transaction fee`, `fee schedule` | 15 |
| `borrow interest`, `borrow_margin`, `repay_margin`, `margin loan` | 15 |
| `margin`, `marginMode`, `cross`, `isolated`, `set_margin_mode`, `fetch_margin_mode` | 15 |
| `leverage`, `set_leverage`, `fetch_leverage` | 15 |
| `position`, `fetch_positions`, `position mode`, `hedge`, `one-way` | 16 |
| `funding history`, `fetch_funding_history` | 16 |
| `conversion`, `convert amount to contracts`, `contractSize` | 16 |
| `proxy`, `https proxy`, `socks`, `aiohttp proxy` | 16 |
| `string math`, `precision math`, `decimal_to_precision` | 16, 03 |
| `precision`, `amount_to_precision`, `price_to_precision`, `tickSize`, `stepSize` | 03 |
| `retry`, `retry mechanism`, `backoff` | 17 |
| `exception`, `error`, `ExchangeError`, `NetworkError`, `AuthenticationError`, `OperationFailed` | 17 |
| `verbose`, `debug`, `logging`, `inspect`, `troubleshoot` | 18 |
| `pagination`, `since`, `limit`, `cursor`, `from_id`, `to_id`, `pagenumber` | 06 |
| `datetime`, `timestamp`, `ISO8601`, `milliseconds`, `parse8601` | 06 |
| `params`, `override params`, `unified params` | 06 |
| `market id`, `unified symbol`, `BTC/USDT`, `base`, `quote` | 03 |
| `network`, `chain`, `ERC20`, `TRC20`, `BEP20` | 03, 14 |
| `testnet`, `sandbox`, `set_sandbox_mode` | 02 |
| `rate limit`, `enableRateLimit`, `rateLimit`, `maxRequestsQueue` | 02 |
| `features`, `exchange.features`, `feature flags` | 02 |
| `instantiate`, `ccxt.binance()`, `exchange class` | 02 |

---

## 📋 File Inventory (sorted by sequence)

| # | File | Lines | ~Tokens | Primary Topic |
|---|---|---|---|---|
| 01 | [`01-overview.md`](./01-overview.md) | 31 | 505 | Architecture, social links |
| 02 | [`02-exchanges.md`](./02-exchanges.md) | 317 | 5,031 | Instantiation, properties, rate limit, testnet, 105 exchange IDs |
| 03 | [`03-markets-intro-to-symbols-and-market-ids.md`](./03-markets-intro-to-symbols-and-market-ids.md) | 448 | 7,917 | Currency/network/market structure, precision, loading, symbols, naming |
| 04 | [`04-markets-market-cache-force-reload.md`](./04-markets-market-cache-force-reload.md) | 22 | 291 | Sharing markets between instances, force reload |
| 05 | [`05-implicit-api.md`](./05-implicit-api.md) | 177 | 3,179 | Implicit REST methods, sync vs async, params, naming conventions |
| 06 | [`06-unified-api.md`](./06-unified-api.md) | 252 | 3,339 | Overriding unified params, pagination (date/id/cursor) |
| 07 | [`07-public-api-intro-to-exchange-status.md`](./07-public-api-intro-to-exchange-status.md) | 413 | 7,004 | Order book, tickers, OHLCV, public trades, time, status |
| 08 | [`08-public-api-borrow-rates-to-long-short-ratio.md`](./08-public-api-borrow-rates-to-long-short-ratio.md) | 435 | 3,455 | Borrow/funding/leverage tiers/OI/volatility/greeks/options/LSR |
| 09 | [`09-public-api-auto-de-leverage.md`](./09-public-api-auto-de-leverage.md) | 19 | 111 | ADL structure |
| 10 | [`10-private-api-intro-to-account-balance.md`](./10-private-api-intro-to-account-balance.md) | 211 | 3,043 | Auth, API keys, nonce override, accounts, balance |
| 11 | [`11-private-api-intro-to-order-structure.md`](./11-private-api-intro-to-order-structure.md) | 149 | 2,992 | Querying orders, order structure |
| 12 | [`12-private-api-placing-orders-to-editing-orders.md`](./12-private-api-placing-orders-to-editing-orders.md) | 431 | 6,833 | Placing orders (limit/market/stop/TP/SL), editing orders |
| 13 | [`13-private-api-canceling-orders.md`](./13-private-api-canceling-orders.md) | 62 | 541 | Cancel order, cancel all, cancel batch |
| 14 | [`14-private-api-my-trades-to-deposit-addresses.md`](./14-private-api-my-trades-to-deposit-addresses.md) | 397 | 5,229 | My trades, ledger, deposits, withdrawals, deposit addresses |
| 15 | [`15-private-api-transfers-to-leverage.md`](./15-private-api-transfers-to-leverage.md) | 430 | 4,274 | Transfers, fees, borrow interest, margin, leverage |
| 16 | [`16-private-api-contract-trading-to-string-math.md`](./16-private-api-contract-trading-to-string-math.md) | 352 | 4,134 | Contract trading, positions, proxy, string math |
| 17 | [`17-error-handling.md`](./17-error-handling.md) | 187 | 2,963 | Retry mechanism, exception hierarchy |
| 18 | [`18-troubleshooting.md`](./18-troubleshooting.md) | 46 | 1,079 | Debugging, verbose mode, FAQ links |
| | [`README.md`](./README.md) | 170 | — | Chunk list with sub-sections |
| | [`_ccxt-manual-python-only.md`](./_ccxt-manual-python-only.md) | 4,431 | ~62,000 | Full single-file Python-only manual (fallback) |

---

## 🤖 Agent Loading Strategy

**Token-budget aware — pick the strategy that fits your context window:**

1. **Tiny budget (<8K tokens)**: Load this `INDEX.md` (~3K tokens) only. Pick the single most relevant chunk and load just that one.
2. **Small budget (8–32K tokens)**: Load `INDEX.md` + 2–4 most relevant chunks for the task.
3. **Medium budget (32–128K tokens)**: Load `INDEX.md` + the whole topic cluster (e.g. all `0X-private-api-*.md` files for a trading task).
4. **Large budget (>128K tokens)**: Skip chunking — load [`_ccxt-manual-python-only.md`](./_ccxt-manual-python-only.md) (~62K tokens) for full cross-section context.

**Recommended agent workflow:**

```
1. Read INDEX.md (this file).
2. Match user query against:
   a. "Fast Start" table (intent-based)
   b. "API Symbol → File Map" (if user mentions a method name)
   c. "Task-Based Decision Tree" (if user describes a workflow)
   d. "Keyword Index" (if user uses domain jargon)
3. Load ONLY the matched chunk(s).
4. If the chunk doesn't fully answer the question, use the chunk's
   internal navigation (its H2/H3 sub-section list at the top) to
   decide whether to load an adjacent chunk.
```

---

## ⚠️ What's NOT in this Manual

- **CCXT Pro / WebSocket streams** — see https://ccxt.pro
- **JS / PHP / Go / C# / Java code samples** — intentionally stripped for Python-only focus
- **Per-exchange quirks** — see the [Exchange Wiki](https://github.com/ccxt/ccxt/wiki/Exchanges) for exchange-specific notes
- **Examples repository** — https://github.com/ccxt/ccxt/tree/master/examples
- **FAQ** — https://github.com/ccxt/ccxt/wiki/FAQ

---

*Generated from [`Manual.md`](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) at commit `master`. Re-run the splitter (`/home/z/my-project/scripts/split_manual.py`) to refresh when the upstream changes.*
