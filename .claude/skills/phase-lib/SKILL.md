---
name: phase-lib
description: Shared code library for the phase-* skill family — NOT invoked directly. It ships `tracklib.py` (tracking-config loader, PLAN.md parser, markdown-table engine, CHANGELOG/version/git helpers), which the phase-start / phase-status / phase-flow / phase-complete scripts import via a uniform bootstrap. There is nothing to run here; skip it when picking a skill to invoke.
---

# phase-lib

The phase-* family's **single shared code library**. This is a code home, not a workflow — there is
no command to run and no reason to invoke this skill. The `phase-*` scripts import from it.

## What it holds

- `scripts/tracklib.py` — the one canonical copy of the family's shared helpers (config/paths loader
  reading `docs/conventions/tracking.md`, `PLAN.md` parsing, the generic markdown-table read/edit
  engine, `CHANGELOG`/version/git utilities). It previously existed as four byte-identical copies,
  one per phase-* skill; it now lives here once. The git helpers are **read-only** by design
  (`git_porcelain`, `git_branch`, `git_ahead_behind`, `git_latest_tag`) — every git *mutation* (branch/merge/tag/push/
  worktree) stays in the SKILL.md runbooks, never in a script. Branch/integration policy keys
  (`release_branch`, `integration`, `concurrency`) load from the same bindings block.

## How consumers import it (uniform bootstrap)

Every skill script lives at `.claude/skills/<skill>/scripts/`, so `parents[2]` is always the shared
`skills/` dir. A consumer adds this block before importing — copy it verbatim; do **not** duplicate
`tracklib.py` itself:

```python
# skill scripts live at .claude/skills/<skill>/scripts/ → parents[2] is the shared skills/ dir
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase-lib' / 'scripts'))
import tracklib as tl  # noqa: E402
```

`# noqa: E402` suppresses "import not at top of file" — the import must follow the `sys.path.insert`.
The insert adds the *directory*, so any future module placed in `phase-lib/scripts/` is importable
off the same line without extra bootstrap. This is `__file__`-relative and zero-install (no package
to `pip install`); the library travels with its consumers, so copy the family, not one skill dir.

See `.claude/rules/15-skills.md` → "Shared Foundation Library Skills" for when this pattern applies.
