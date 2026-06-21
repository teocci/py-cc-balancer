# Phase 1 — Domain primitives

- **Objective:** Immutable types + error taxonomy + enums.
- **Deliverables:** `exceptions.py` (`AppError` + subclasses); `constants.py` (`CCB_PREFIX`, file names, exit codes, defaults, env keys); `enums/` (`OrderSide`, `SkipReason`, `OutputFormat`); `models/` frozen+slots dataclasses: `PairConfig`, `AssetBalance`, `PairSnapshot`, `ProposedOrder`, `RebalanceDecision`, `RebalanceState`, `HistoryEvent`, `ExecutionResult`.
- **Definition of Done:** import smoke green; dataclasses reject mutation; `SkipReason` covers all decision reasons (`OK`, `WITHIN_BAND`, `BELOW_MIN_NOTIONAL`, `INSUFFICIENT_BALANCE`, `ABNORMAL_PRICE`, `MARKET_UNAVAILABLE`, `TOO_SOON`).
- **Out of scope:** Logic using these types.
