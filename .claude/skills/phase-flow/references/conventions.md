# Phase-flow conventions (reusable base)

The shared, **project-agnostic** methodology for the `phase-*` skill family
(`phase-start`, `phase-status`, `phase-complete`, `phase-flow`). ~80–90% of this transfers
unchanged to a new project. Anything project-specific (concrete file paths, the version-file
location, the test command, format deviations) lives in a project's
**`docs/conventions/tracking.md`**, which *overrides and extends* this file.

> **Resolution order (always):** base conventions (this file) → project `tracking.md` overrides.
> A script or skill reads the base rule, then applies any override keyed by the same name.
> If `tracking.md` is absent, the base applies as-is.

Placeholders written as `<NAME>` are defined by `tracking.md` (see
[Project bindings](#project-bindings-tracking-md-must-define)).

---

## 1. The hierarchy

```
Release  vX.Y.Z   ── one or many phases ──▶  <CHANGELOG> (public) + <RELEASE_INDEX> (internal)
  └─ Phase  P-N    ── one or many items  ──▶  <PROGRESS> index + <PLAN> active plan
       └─ Item  I-N / F-N                ──▶  <IMPROVEMENTS> / <FIXES>
```

- **Release** — a versioned, published unit. One or many phases. Recorded publicly in
  `<CHANGELOG>` and indexed internally in `<RELEASE_INDEX>`.
- **Phase (`P-N`)** — the **unit of one working iteration** (see sizing below). One or many
  items, or greenfield build work with no items. Indexed in `<PROGRESS>`; planned in `<PLAN>`.
- **Item** — a single **improvement (`I-N`)** or **fix (`F-N`)** inside a phase. Indexed in
  `<IMPROVEMENTS>` / `<FIXES>`.

## 2. Phase-sizing heuristic (model-agnostic)

A phase must **fit comfortably in one working-context window with headroom** — small enough to
plan, implement, test, and finalize in a single iteration before context saturation degrades
quality. This is deliberately **not** a fixed token count: a larger-context model (e.g. 1M) may
carry a bigger phase than a 250K model. When decomposing:

- Split work so each phase is independently testable and finalizable.
- Prefer more small phases over one large phase; a phase you cannot finish in one sitting is too big.
- Greenfield: a phase is a coherent build slice (a subsystem/command). Post-prototype: a phase
  bundles one or a few small items that share a theme.

## 3. Lifecycle & skill responsibilities

| Stage | Skill | Mutates? | What happens |
|---|---|---|---|
| Decompose & order (plan mode) | `phase-flow` | no | Propose phase breakdown + execution order + parallel groups |
| Scaffold | `phase-start` | docs only | Allocate ids, create detail stubs, index rows, write `<PLAN>` |
| Observe | `phase-status` | no | Report state + coherence; surface drift |
| Finalize a phase | `phase-complete` (A) | docs | Fill details, mark done, accrue `<CHANGELOG>` Unreleased |
| Cut a release | `phase-complete` (B) | docs + git | Bump version, roll changelog, index release, commit/tag/push |
| Advance (NEXT) | `phase-flow` | `<PLAN>` cursor | Pick next unblocked phase(s); guard release boundaries |

**Boundaries:** `phase-start` never bumps/commits. `phase-status` never mutates.
`phase-flow` never edits detail/index files — it routes and moves the cursor. Only
`phase-complete` bumps the version, touches `<CHANGELOG>` version sections, or runs git.

## 4. Division of labor: scripts vs model

Deterministic, mechanical work runs in a **script** (`<skill>/scripts/*.py`) to save tokens and
avoid drift; judgment/prose stays with the **model**.

- **Scripts:** id allocation, table-row insertion/updates, version bump, changelog roll, status
  parsing, topological ordering, coherence assertions.
- **Model:** phase decomposition, detail-file bodies (Objective/Approach/Symptom/…), changelog
  bullet wording, theme lines, commit messages.

Scripts read project bindings from `tracking.md` so the skill body stays portable.

## 5. ID schemes & version map

- Phases `P-<n>`, improvements `I-<n>`, fixes `F-<n>` — monotonic, **never reused**. Allocate the
  next free id by scanning the relevant index.
- **Version bump** off the current `<VERSION>` for a *release* (the union of its phases' items):
  - contains any improvement / feature / greenfield phase → **minor** (`x.Y.0`)
  - fix-only → **patch** (`x.y.Z`)
  - a fix riding with an improvement **inherits the minor** (no separate patch)
- SemVer, no pre-release/build tags unless `tracking.md` says otherwise.

## 6. Tracking files & templates

All internal files are written **token-efficiently for AI-agent consumption**. `<CHANGELOG>` is
the **only** human-facing/public file.

### 6.1 Item index rows
- **Improvements** (`<IMPROVEMENTS>`): `| ID | Idea | Notes |`; `ID` is a link
  `[I-N](improvements/I-N.md)`. Status is tracked **inline in Notes** — in progress carries no
  done-marker; finalized appends `✅ Done in vX.Y.Z.`
- **Fixes** (`<FIXES>`): `| ID | Symptom | Root cause | Fix | Phase |`; `ID` is a link. The last
  column holds the phase id or the release version; left blank until finalized.

### 6.2 Detail files
Frontmatter block (bold key list), then sections. In progress → `**Status:** 🚧 IN PROGRESS` and
`**Version:** (pending)`; finalized → `**Status:** ✅ DONE (NNN tests; live-verified).` with the
real version.

- **Improvement** `improvements/I-N.md`:
  ```markdown
  # I-N — <Title>

  - **Improvement ID:** I-N
  - **Version:** <version|(pending)>
  - **Date:** <YYYY-MM-DD>
  - **Status:** <🚧 IN PROGRESS | ✅ DONE (NNN tests; live-verified).>
  - **Related work:** <links to siblings / delivered fix>

  ## Objective
  ## Approach
  ## Files changed
  | File | Change |
  |---|---|

  ## Verification
  ```
- **Fix** `fixes/F-N.md`: same frontmatter with `**Fix ID:**`; sections
  `## Symptom` / `## Root cause` / `## Fix` / `## Files changed` (table) / `## Verification`.
- **Phase** `phases/phase-N.md` (retrospective style): frontmatter `**Phase ID:** / **Version:** /
  **Date:** / **Tests:**`, then `## Objective` / `## What was built` / `## Files changed` (table) /
  `## Verification` / optional `## Notes / follow-ups`.

### 6.3 `<PROGRESS>` (internal phase index)
- Header: `**Current version:**`, `**Active phase:**` (one-line prose naming the in-flight
  release + items + test count), pointer to detail files.
- **Phase status table:** `| Phase | Title | Status |` — status is lowercase prose
  (`planned` / `in progress` / `done`). **No emoji, no version column, no "Quick Status" table.**
- `## Next action` section.
- Reverse-chronological `> Phase N (done): …` blockquotes — one dense paragraph per finished
  phase (the resume narrative). Added by `phase-complete`.

### 6.4 `<CHANGELOG>` (public — Keep a Changelog + SemVer)
- `## [Unreleased]` at top accrues bullets as phases finalize (Part A).
- A release promotes it to `## [X.Y.Z] - YYYY-MM-DD` with an optional theme paragraph and
  `### Added` / `### Changed` / `### Fixed` subsections; each bullet is **id-prefixed**
  (`- I-6: …`, `- F-5: …`). Leave a fresh empty `## [Unreleased]`.

### 6.5 `<PLAN>` (active plan ledger — internal)
```markdown
# Active Plan

**Approved:** <YYYY-MM-DD>  **Branch:** <branch>  **Cadence:** <per-phase | batched | note>

| Phase | Items    | Depends | Release | Version   | Status      |
|-------|----------|---------|---------|-----------|-------------|
| P-15  | I-5      | —       | R1      | 0.3.0     | released    |
| P-16  | I-6      | P-15    | R2      | (pending) | in-progress |
| P-17  | I-7, F-4 | P-15    | R3      | (pending) | pending     |
```
- `Status ∈ {pending, in-progress, done, released}`. `Depends` is `—` or a comma-list of phase ids.
- `Release` groups phases into releases (a shared tag = batched cadence; unique tags = per-phase).
- **Cursor** = the topmost row not yet `released` whose `Depends` are all `done`.
- When every row is `released`, reset the file to a `No active plan.` stub.

### 6.6 `<RELEASE_INDEX>` (release → phases, internal)
`| Release | Date | Phases | Theme |`, newest first. One row per cut release. The detailed
public notes live in `<CHANGELOG>`; this file is the terse index.

## 6b. Release track vs chore track (what does NOT get a release)

The phase → version → CHANGELOG → tag machinery governs **product iterations only**. Not every
commit is a release; forcing tooling/process work through `phase-complete` would wrongly bump the
version and cut a tag.

- **Release track** → a phase, finalized/released by `phase-complete` (version bump + `<CHANGELOG>`
  + `<RELEASE_INDEX>` row + tag). Use when the change is a **shipped-product iteration** a user or
  agent would see in release notes: product source behavior/CLI, packaging-as-a-deliverable,
  user-facing docs bundled with a version. Tracking-file edits made *while delivering a phase*
  (`<PLAN>`, detail stubs) ride the release commit — `phase-complete` sweeps them via `git add -A`.
- **Chore track** → a plain **Conventional Commit**, with **no** version bump, **no** `<CHANGELOG>`
  entry, **no** `<RELEASE_INDEX>` row, **no** tag, **no** phase. Use for developer tooling and
  process. **As a rule, everything under `.claude/` is chore-track** — skills, `rules/`,
  `settings.json`, hooks, commands — because it is agent/dev configuration, never shipped product.
  Also chore-track: meta or planning docs, CI/build tweaks not tied to a release, and refactors
  with no user-visible effect. Commit types: `chore:` / `docs:` / `ci:` / `build:` / `refactor:` /
  `test:`. Path hints: `.claude/**` → `chore(...)`; meta docs → `docs`; `.github/**` → `ci:`.

**Decision rule:** *"Would this appear in product release notes, or change shipped behavior?"*
Yes → release track. No → chore track.

Chore commits never touch `<VERSION>` or the `<CHANGELOG>` version sections, so `check_coherence.py`
stays green across them — the two tracks do not interfere.

## 7. Commit & release convention

- Release commit: `release: vX.Y.Z — <theme> (IDs)` (em-dash; ids in parentheses).
- Other commits: Conventional Commits with an id scope where relevant
  (`fix(F-3): …`, `feat: Phase 12 — …`, `docs(...): …`).
- **Never** add `Co-Authored-By` or other AI trailers.
- Releases are **tag-driven**: after the release commit, `git tag vX.Y.Z` and push the current
  branch + the tag. Pushing the tag is what triggers the release workflow.

## 8. Version bump mechanics

- The version lives in exactly one place, `<VERSION_FILE>` (`<VERSION_ATTR>`). Bump **only** there.
- If the project derives its package version dynamically from that attribute (common), **never**
  add a literal version elsewhere (e.g. a build file) — doing so is a bug. `tracking.md` states
  the specific hazard for the project.

## 9. Guardrails

- **Tests green before any finalize.** Never finalize/release on a failing suite (`<TEST_CMD>`).
- **Coherence gate before commit/tag** (see `phase-status/scripts/check_coherence.py`): version
  is semver; no forbidden literal version; top `<CHANGELOG>` heading == `<VERSION>`; released-group
  detail files are `✅ DONE` with matching version; `<RELEASE_INDEX>` top row == `<VERSION>`.
- **No secrets in the diff** (grep for key/secret/token/password/passphrase patterns).
- **No premature advance:** `phase-flow` refuses NEXT past a phase that closes a release group but
  isn't `released` yet.

## Project bindings (`tracking.md` must define)

| Placeholder | Meaning |
|---|---|
| `<PACKAGE>` | Import/package name |
| `<VERSION_FILE>` / `<VERSION_ATTR>` | Where `__version__` lives; the attribute path |
| `<TEST_CMD>` | Command that runs the suite |
| `<PROGRESS>` `<PLAN>` `<RELEASE_INDEX>` `<CHANGELOG>` `<IMPROVEMENTS>` `<FIXES>` | Concrete file paths |
| detail dirs | `phases/`, `improvements/`, `fixes/` locations |
| overrides | any format deviation or extra rule specific to the project |
