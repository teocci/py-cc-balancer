# Phase 12 — Regime signal + agent flags/milestones

- **Objective:** Surface *should the target ratio change?* (signal #3) and let the agent register
  persistent watch-conditions — Layer-2 defines, Layer-1 computes.
- **Deliverables:**
  - `managers/regime_manager.py` — price-variance-since-target-set vs `target_review_band_pct` →
    `RegimeSignal`: flag + deterministic heuristic suggested ratio(s) + what-if scenarios (value/risk
    under e.g. 80/20 vs 50/50 vs 25/75). Never auto-changes the ratio.
  - `stores/flags_store.py` (`flags.json`) + `managers/flags_manager.py` — register/evaluate milestones
    and watch-conditions against current snapshots, report hits.
  - `models/` — `RegimeSignal`, `Milestone` (frozen+slots).
  - `config.py`/`constants.py` — `target_review_band_pct`.
  - Wire `regime [--pair]` (read) and `flag {add|list|remove}` (write) in `cli.py`.
- **Definition of Done:** regime flag fires at `target_review_band_pct`; suggested ratio + scenarios are
  deterministic for fixed inputs; agent can `flag add` a milestone and see it reported hit when its
  condition is met; all JSON carries `schema_version`.
- **Out of scope:** The agent's choice of new ratio (that is Layer 2).
