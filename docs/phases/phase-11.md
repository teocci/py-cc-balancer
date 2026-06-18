# Phase 11 — Performance & cost-basis (`performance`)

- **Objective:** Tell the agent whether the strategy is *working* — true cost-basis P&L (signal #2).
- **Deliverables:**
  - `managers/performance_manager.py` — injected `ledger_store` + exchange tickers; compute realized
    P&L per rebalance (from fills + fees), unrealized P&L now (current price vs cost basis), and ROI
    per pair + portfolio totals. Decimal math.
  - `models/` — `PerformanceSnapshot`, `Fill` (frozen+slots).
  - Wire `performance [--pair]` (read) and `performance --history` (audit) in `cli.py`.
- **Definition of Done:** P&L reconciles on a scripted fill sequence with known realized + unrealized +
  fees; `performance --json` returns per-pair + portfolio totals; ROI correct to the cent (Decimal);
  unrealized works from baselines even with an empty ledger.
- **Out of scope:** Regime signal (Phase 12); tax-lot accounting beyond cost-basis.
