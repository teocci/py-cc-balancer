# Phase 24 — Paper backend + persistent book

- **Phase ID:** 24
- **Version:** 0.6.0
- **Date:** 2026-07-19
- **Tests:** 589
- **Status:** ✅ DONE (589 tests; live-verified).

## Objective

Build the simulated-exchange backend for a paper account: a persistent per-account book plus a PaperExchangeStore that mirrors the full ExchangeStore surface. Reads real PUBLIC market data via a wrapped real ExchangeStore; simulates balances/orders/fills in the book. Reconcile-driven fills — fetch_order reports a fill when a resting limit is crossed by the live ticker — so the unchanged ReconciliationManager books it. No live command or manager changes in this phase.

## What was built

I-18 — the paper (simulated-exchange) backend: `stores/paper_book.py` (persistent balances/orders) and
`stores/paper_exchange.py` (`PaperExchangeStore` — real public prices + a simulated book, reconcile-driven
fills) mirroring the `ExchangeStore` surface. See [I-18](../improvements/I-18.md).

## Files changed

| File | Change |
|---|---|
| `stores/paper_book.py` | New persistent simulated book |
| `stores/paper_exchange.py` | New `PaperExchangeStore` (reconcile-driven fills) |
| `constants.py` | Paper book/capital/quote/fee constants |
| `tests/test_paper_exchange.py` | 13 backend unit tests |

## Verification

`.venv/Scripts/python -m pytest tests/test_paper_exchange.py -v` — book round-trip, resting vs crossing
fills (BUY/SELL), fee math, idempotent re-fetch, insufficient-funds rejection.
