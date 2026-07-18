# Phase 20 — Sub-daily timeframes + Binance fallback fetcher

- **Phase ID:** 20
- **Version:** (pending)
- **Date:** (pending)
- **Tests:** (pending)
- **Status:** 🚧 IN PROGRESS

## Objective

Extend the backtest to sub-daily timeframes (1m/5m/15m). Build the Binance REST klines fallback
fetcher (`stores/history_fetch.py`, adapted from the prototype, constants centralized) for deep 1m/5m
backfill where ccxt pagination is impractical, and wire multi-timeframe alignment (decision timeframe
vs finer fill-resolution timeframe). Network stays in the stores layer. Delivers I-15.

## What was built

(fill during work)

## Files changed

| File | Change |
|---|---|

## Verification

(fill during work)
