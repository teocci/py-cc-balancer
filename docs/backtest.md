# Backtest engine — how to read results, and what it can't tell you

The `simulation` command backtests a configured pair's rebalance strategy over historical candles.
Use it for **strategy research** — comparing bands, targets, fees, and timeframes on past data. It is
**not** execution validation: a green backtest says a strategy *would have* rebalanced a certain way
against recorded bars, not that it will fill, get accepted, or stay solvent live. The residual risk a
backtest cannot remove is covered by the [live smoke-test runbook](live-smoke-test.md).

See [`DESIGN.md`](DESIGN.md) → *Backtest engine (offline)* for the architecture (fetch → run →
report) and the network-only-in-stores invariant.

## Workflow

```bash
# 1. Fetch history into the resumable store (1m/5m via Binance REST fallback, else ccxt).
ccbalancer simulation fetch BTC/USDT --start 2022-09-01 --end 2026-01-01
#    default timeframes: 15m, 1h, 4h, 1d — add --timeframe 1m/5m for deep sub-daily.

# 2. Replay the configured pair deterministically (compute only, no network).
ccbalancer simulation run BTC/USDT --timeframe 1d --start 2022-09-01 --end 2026-01-01 \
    --capital 10000 --fee-rate 0.001 --json
#    optional: --fill-timeframe 1h resolves fills on finer bars within each daily interval.

# 3. Report P&L / ROI / per-year breakdown for the run (offline).
ccbalancer simulation report <run_id>
```

## How to read a result

- **`final_value` vs `capital`** is the headline: ROI = `(final_value − capital) / capital`. But a
  single ROI over one window hides *when* the gains happened.
- **Per-year breakdown** is the honest lens. A strategy that made all its money in one bull year and
  bled the rest is fragile; realized P&L per year exposes that. Always read the per-year split before
  trusting the headline.
- **`fills` vs `orders_placed`** shows how often the strategy *wanted* to trade vs how often a bar
  actually crossed the limit. A large gap means most orders rested and re-quoted — the strategy is
  sensitive to the fill assumption below.
- **`rejects`** counts orders below `--min-cost`. Persistent rejects mean the strategy proposes
  sub-minimum legs it can never execute → drift that **never converges**. This is a red flag, not
  noise.
- **Determinism:** identical inputs produce a byte-identical ledger and the same `run_id`. If two runs
  you expected to match differ, an input differed (capital, fees, band, timeframe, range).

## Limitations — read before trusting a number

1. **Bar-fill assumption (the big one).** A fill is *approximated* from a bar's range: a BUY fills if
   a later bar's low ≤ the limit, a SELL if a later high ≥ the limit, always **at the limit price**.
   Real fills depend on order-book liquidity, queue position, and maker/taker dynamics a candle can't
   show. Touching a price ≠ getting filled there. Finer `--fill-timeframe` bars tighten the
   approximation (fills resolve within the decision interval, at the crossing finer bar) but never
   make it proof of liquidity.
2. **No look-ahead — but only within the model.** An order never resolves on its own decision bar; it
   resolves on strictly-later bars. The engine cannot peek at the future. It *can* still be optimistic
   about fills (see #1).
3. **Cycle dependence / overfitting.** Results are hostage to the window. A 2022→2026 run spans a full
   crypto cycle; a 2023-only run does not. Tuning band/target until one window looks great is
   curve-fitting — validate across multiple, disjoint windows and read the per-year split.
4. **Fee realism.** `--fee-rate` is a flat maker rate on each fill's notional. It does not model
   taker fees, tier changes, funding, slippage, or spread. Real costs are usually higher.
5. **Gaps and data provenance.** The store records coverage and interior gaps in `manifest.json`; a
   gap means missing bars, and a decision interval spanning a gap resolves fills over a wider window.
   The 1m/5m Binance REST fallback always sources from **Binance** even when `data_exchange` is
   another venue, so deep sub-daily candles can be cross-venue relative to the higher timeframes under
   the same symbol — set `data_exchange = binance` to keep provenance consistent.
6. **Strategy scope only.** The backtest exercises the pure `decide()` path. It does **not** exercise
   auth, live order placement, real rejections, partial fills, or state reconciliation — and a known
   live-execution gap ([F-6](fixes/F-6.md): fills booked on submission without order-status
   reconciliation) is bypassed entirely by the replay loop. Those are validated only live.

## The honest framing

A good backtest **narrows** the strategy space and surfaces obvious failure modes (never-converging
drift, fee erosion, cycle fragility). It does not certify a strategy for live capital. Before running
real orders, complete the capped [live smoke-test](live-smoke-test.md).
