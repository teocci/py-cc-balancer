---
name: phase-flow
description: Orchestrate the phase lifecycle and own execution sequencing. Detects state via phase-status, suggests execution order over the dependency DAG, advances the NEXT cursor to the next unblocked phase(s), and routes to phase-start / phase-complete. The entry point after a plan is approved and the handler for NEXT. Holds the reusable base conventions.
triggers:
  - "NEXT"
  - "next"
  - "what's next"
  - "suggest order"
  - "run the workflow"
  - "continue"
---

# phase-flow

The router and sequencing engine for the `phase-*` family. It never edits detail/index files —
it reports, sequences, and moves the `PLAN.md` cursor, delegating mutation to the other skills.

**Conventions hub:** the reusable base lives here in `references/conventions.md`; every `phase-*`
skill reads it, then applies project overrides from `docs/conventions/tracking.md`.

## Report first, then act
1. **Read state** (read-only):
   ```bash
   .venv/Scripts/python .claude/skills/phase-status/scripts/status.py
   ```
2. **Route** by the situation (first match wins):

   | Situation | Action |
   |---|---|
   | Work is **not a product iteration** (tooling / `.claude/` / meta-docs / CI) | → **chore track**: commit plainly, no `phase-complete` (below) |
   | No active plan / user approved a plan / "start" | → run **`phase-start`** to scaffold |
   | User asks "where/status" | → run **`phase-status`** (report only) |
   | User wants to finalize/release a worked phase | → run **`phase-complete`** |
   | **NEXT** and the just-worked phase is finalized | → **advance** (below) |
   | **NEXT** but the current phase closes a release group and isn't `released` | → **refuse**; point at `phase-complete` Part B |
   | All plan rows `released` | → report plan complete; reset `PLAN.md` to the `No active plan.` stub |

## Release track vs chore track (route before finalizing)
Before treating any work as a release, apply the decision rule (base conventions §6b):
*"Would this appear in product release notes, or change shipped behavior?"*
- **Yes → release track:** it's a phase — use `phase-complete`.
- **No → chore track:** do **not** run `phase-complete` (it would wrongly bump the version + tag).
  Commit directly with a Conventional Commit — `chore:` / `docs:` / `ci:` / `build:` / `refactor:`
  / `test:`. **Everything under `.claude/` (skills, `rules/`, `settings.json`, hooks, commands) is
  chore-track** → `chore(...)`; meta docs → `docs`; `.github/**` → `ci:`. No version bump, no
  CHANGELOG, no RELEASE.md row, no tag. Coherence stays green (chore commits don't touch the
  version/CHANGELOG).

## Sequencing (the order engine)
Use `order.py` for both plan-mode ordering and NEXT selection:
```bash
.venv/Scripts/python .claude/skills/phase-flow/scripts/order.py --suggest   # full order as waves
.venv/Scripts/python .claude/skills/phase-flow/scripts/order.py --next      # phases ready now
```
- **In plan mode** (`--suggest`): propose an execution order. A wave with more than one phase is
  parallelizable — those phases are independent and can run in **separate sessions**.
- **On NEXT** (`--next`): the ready set is phases whose dependencies are all `done` and that aren't
  done yet. Guard: the just-worked phase must be finalized (`PLAN` `done`, tree clean) before
  advancing. If several phases are ready and independent, tell the user they can run in parallel.

## The NEXT loop (why it survives sessions)
The cursor is **not** in conversation memory — it is re-derived from `PLAN.md` every time
(topmost non-`released` row whose deps are all `done`). So NEXT works across new sessions,
compaction, and interleaved commands. Cadence is the `Release` grouping in `PLAN.md`, decided once
at scaffold and re-read each time — nothing to remember.

## Worked scenario (per-phase cadence: P-15[I-5] → P-16[I-6] → P-17[I-7,F-4])
```
approve → phase-start (scaffold PLAN.md)
work I-5 → phase-complete A+B → v0.3.0 tagged
NEXT → order.py --next → P-16 ready → implement I-6
work I-6 → phase-complete A+B → v0.4.0
NEXT → P-17 ready → implement I-7 + F-4
work both → phase-complete (Part A twice, Part B once) → v0.5.0 (F-4 inherits the minor)
NEXT → no phases left → plan complete → reset PLAN.md
```

## Notes
- This skill routes and sequences; it does not stamp files or run git. Only `phase-complete` does.
- Direct use of `phase-start` / `phase-status` / `phase-complete` is fine; the orchestrator is a
  convenience entry point, not a mandatory chokepoint.
