# Paper account runbook — rehearse live execution with no real money

A [backtest](backtest.md) proves the *strategy math* over historical candles; it never touches auth,
order placement, rejections, partial fills, or reconciliation. A **paper account** is the other axis:
a live-shaped account you drive command-by-command that exercises the real execution plumbing —
confirm-token issue/consume, order objects, the write-ahead order store, and the reconcile loop —
but places no real orders and moves no real money.

> **Backtest vs paper — complementary, not alternatives.** `simulation run` is a batch backtest that
> answers *"would the strategy have made money?"*. A paper account answers *"does the live order
> machinery work safely?"*. Run the backtest to choose a strategy; run a paper account to rehearse
> executing it. Neither replaces the capped [live smoke-test](live-smoke-test.md), which is the only
> thing that validates real credentials and a real venue.

## How it works

A paper account keeps a **real** underlying exchange id (e.g. `binance`) used only for **public**
market data — prices, markets, OHLCV need no API key — and carries a `paper` flag. Balances and
orders are simulated in a persistent per-account book (`accounts/<id>/paper_book.json`). A resting
limit order fills at its limit price once the live ticker crosses it, reported through the same
`fetch_order` contract a real venue gives the reconciler — so a paper account exercises the real
write-ahead + reconcile path with **no** change to any command. Only the market-data reads touch the
network.

## 1. Create and fund the paper account

```bash
ccbalancer auth login --paper --exchange binance --no-testnet --paper-capital 10000
#   --paper        : no credentials collected, no live verification
#   --exchange     : the real venue whose PUBLIC prices drive the simulated book
#   --account NAME : name the account (default: paper)
#   --paper-capital: initial all-stable balance (default 10000; --paper-quote sets the asset, default USDT)
```

`auth login --paper` (name defaults to `paper`; override with `--account <name>`) seeds the book and
makes the account active (like any first account). It stores no secrets — `auth list` shows the
account with no key/secret.

## 2. Drive the live commands — unchanged, against `--account paper`

```bash
ccbalancer pair add BTC/USDT --account paper --target 80/20 --band 5 --min-notional 10
ccbalancer status   --account paper            # simulated balance + real live price
ccbalancer plan     --account paper --json     # the rebalance decision + a confirm token
```

`status`/`plan` read the live public ticker and the simulated book. `plan` issues the same
confirm-token handshake as a real account.

## 3. Rehearse an execute → reconcile cycle

```bash
ccbalancer rebalance --account paper --execute --confirm <token-from-plan>
ccbalancer orders    --account paper           # the maker limit, usually resting (open, filled 0)
ccbalancer reconcile --account paper           # books the fill once the live ticker crosses the limit
```

A maker limit usually **rests** — exactly as live. It fills only when the market reaches the limit;
`reconcile` (and the reconcile step inside each `rebalance`) books the delta into the paper account's
`ledger.jsonl` and advances `state.json`, the same code path a real account uses. Fills are never
booked on submission.

```bash
ccbalancer performance --account paper         # cost-basis P&L over the simulated fills
ccbalancer decisions   --account paper         # the decision log for the rehearsal
```

## 4. Restart a rehearsal

```bash
ccbalancer paper reset --account paper --paper-capital 10000
#   re-seeds the book to a fresh all-stable balance (re-login keeps the same book, so use reset)
```

## What this validates (and what it doesn't)

- **Validates:** the confirm-token issue/consume handshake, order objects and the write-ahead order
  store, the cancel-and-replace flow, and the reconcile loop that books only real fills — all against
  live prices.
- **Does not validate:** real credentials/auth, a real venue's acceptance/rejection and true
  liquidity, real partial fills, or fees/slippage beyond the flat paper maker fee. Those are the
  domain of the capped [live smoke-test](live-smoke-test.md). And it does not judge strategy
  profitability — that is the [backtest](backtest.md).
