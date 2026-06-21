---
name: phase-complete
description: Finalize a completed phase or fix — update PROGRESS.md, CHANGELOG.md, FIXES.md or IMPROVEMENTS.md, bump version, and commit. Run after all tests pass and live testing is done.
triggers:
  - "phase complete"
  - "mark phase done"
  - "finalize phase"
  - "bump version"
  - "release this phase"
  - "commit this fix"
---

# phase-complete

Runs the standard 5-step finalization sequence after a phase or fix is fully done (all unit tests pass, live-tested where applicable).

## Required inputs

Before running, confirm:
- Phase/fix ID (e.g. `I-11`, `F-9`)
- Version number (e.g. `0.24.0` for improvement, `0.23.1` for fix)
- One-line description for CHANGELOG (e.g. `I-11: wb campaign bulk-edit command`)
- Date (today's date in `YYYY-MM-DD`)

## Step 1 — Write the detail file

- **Phase** → `docs/phases/phase-<N>.md`
- **Fix** → `docs/fixes/F-<N>.md` (filename matches the `F-<N>` id in `docs/FIXES.md`)
- **Improvement** → `docs/phases/<id>-<slug>.md`

Include:
- ID, version, date, test count
- For a phase/improvement: objective + what was built (bullet list)
- For a fix: Symptom / Root cause / Fix sections
- Files changed (table)
- Any live test results or notable behaviors

## Step 2 — Update docs/PROGRESS.md phase index

Find the phase row in the Phase Index table. Change status from `🔲 PLANNED` or `🔄 IN PROGRESS` to `✅ DONE` and fill in the version column. Update the Quick Status table: version number, test count.

## Step 3 — Append to CHANGELOG.md

Add at the top of the file (below the header), after the previous entry:

```markdown
## vX.Y.Z (YYYY-MM-DD)
- <phase-id>: <one-line description>
```

## Step 4 — Clean up docs/FIXES.md or docs/IMPROVEMENTS.md

If this was a fix: update the row in `docs/FIXES.md` index table (status → ✅ DONE, version filled in). Remove any detail stub below the table — that content now lives in `docs/phases/`.

If this was an improvement: same for `docs/IMPROVEMENTS.md`.

## Step 5 — Bump version and commit

Edit `src/wb/__init__.py`:
```python
__version__ = 'X.Y.Z'
```

Edit `pyproject.toml`:
```toml
version = 'X.Y.Z'
```

Then commit:
```bash
git add -A
git commit -m "release: vX.Y.Z — <theme>"
```

## Step 6 — Tag and push

Create the version tag on the release commit and push both the branch and the tag:

```bash
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

This triggers the GitHub Release workflow (`.github/workflows/release.yml`), which builds the bundles and publishes the release.

## Verification checklist

- [ ] `docs/phases/<id>.md` exists and has full detail
- [ ] `docs/PROGRESS.md` Quick Status version matches new version
- [ ] `docs/PROGRESS.md` phase row shows ✅ DONE
- [ ] `CHANGELOG.md` has new entry at top
- [ ] `docs/FIXES.md` or `docs/IMPROVEMENTS.md` row shows ✅ DONE
- [ ] `src/wb/__init__.py` `__version__` matches new version
- [ ] `pyproject.toml` `version` matches new version
- [ ] Commit message format: `release: vX.Y.Z — <theme>`
- [ ] Tag `vX.Y.Z` created and pushed
- [ ] Branch pushed to `origin/main`

## Notes

- This skill is project-agnostic. The paths (`docs/PROGRESS.md`, `src/wb/__init__.py`, etc.) are WB CLI-specific but the methodology transfers to any project using the same three-zone documentation layout.
- Never commit unless all tests pass (`pytest tests/unit/ -v`).
- Never add `Co-Authored-By` trailers to commit messages.
