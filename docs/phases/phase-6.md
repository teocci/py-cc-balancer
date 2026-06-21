# Phase 6 — Rebalance decision logic (core, pure)

- **Objective:** Deterministic `decide(pair, snapshot) -> RebalanceDecision` with all guards.
- **Deliverables:** `managers/rebalance_manager.py` — guards (ordered): `ABNORMAL_PRICE`, `MARKET_UNAVAILABLE`, optional `TOO_SOON`, `WITHIN_BAND`, `BELOW_MIN_NOTIONAL`, `INSUFFICIENT_BALANCE`, max-trade clamp. Each guard a helper ≤30 lines.
- **Definition of Done:** full decision matrix green (within/outside band, BUY/SELL sizing, min-notional, insufficient balance, abnormal price, clamp, precision rounding); function pure (no mocks).
- **Out of scope:** Placing orders, I/O.
