---
name: phase-start
description: Scaffold the tracking structure for an approved plan — allocate phase/item ids, create detail stubs, add index rows, and write the PLAN.md ledger with dependencies and release grouping. Run right after a plan is approved, before implementation. Docs-only; never commits or bumps the version.
triggers:
  - "scaffold this plan"
  - "start these phases"
  - "plan approved"
  - "set up tracking"
  - "begin implementation"
---

# phase-start

Turn an approved plan into tracking structure. Deterministic id-allocation, stub creation, index
rows, and the `PLAN.md` ledger run in `scripts/scaffold.py`; you supply the plan spec and then fill
the stub bodies.

**Read first:** base conventions `../phase-flow/references/conventions.md` and project overrides
`docs/conventions/tracking.md` (the hierarchy, phase-sizing heuristic, and templates).

## Steps
1. **Assemble the plan spec** from the approved plan. Decompose the work into
   **context-window-sized phases** (conventions §2), each bundling one or a few items. Capture
   dependencies and release grouping (the cadence). Ask the user only if grouping/deps weren't
   stated. Spec shape (JSON):
   ```json
   {
     "approved": "<YYYY-MM-DD>", "branch": "<branch>", "cadence": "per-phase | batched",
     "phases": [
       {"title": "…", "depends": [], "release": "R1",
        "items": [{"kind": "improvement|fix", "title": "…", "summary": "one-line",
                   "objective": "…", "related": "siblings …"}]}
     ]
   }
   ```
   `depends` entries are 0-based indices into this spec's `phases` array.
2. **Run the scaffold** (writes stubs + index rows + `PLAN.md`; allocates next-free ids):
   ```bash
   .venv/Scripts/python .claude/skills/phase-start/scripts/scaffold.py --spec <spec.json>
   ```
   Preview first with `--dry-run` to see the ids and files it will create.
3. **Fill the stub bodies** — for each created detail file, write the Objective/Approach (or
   Symptom) from the plan. Leave frontmatter `Status: 🚧 IN PROGRESS` / `Version: (pending)`;
   `phase-complete` stamps those at finalize/release.
4. **Report** the scaffolded phases and which are unblocked to start (run `phase-flow`'s
   `order.py --suggest` for the execution order). **Do not** commit, bump the version, or touch
   `CHANGELOG.md` — scaffolding is docs-only.

## Verification
- [ ] `PLAN.md` lists every phase with items, `Depends`, `Release`, and `pending` status
- [ ] Each phase/item has a detail stub and an in-progress index row
- [ ] `PROGRESS.md` phase table gained a `planned` row per phase
- [ ] No version bump, no `CHANGELOG.md` edit, no git actions

## Notes
- Ids are allocated next-free by scanning the indexes; never reuse an id.
- If a plan changes mid-flight, re-running scaffold allocates *new* ids — prefer editing `PLAN.md`
  and the stubs directly for small adjustments.
