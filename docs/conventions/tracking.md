# Project tracking conventions — ccbalancer

Project **override layer** for the `phase-*` skills. The reusable base lives in
`.claude/skills/phase-flow/references/conventions.md`; this file binds its `<PLACEHOLDERS>` to
ccbalancer's real paths and records project-specific hazards. Scripts read the `[bindings]`
block below (via `tomllib`); the prose captures deviations a script can't encode.

> Resolution order: **base conventions → this file**. Where they disagree, this file wins.

## Bindings

```toml
package = "ccbalancer"
version_file = "src/ccbalancer/__init__.py"
version_attr = "__version__"
# pyproject.toml derives the package version dynamically from version_attr
# (dynamic = ['version'] + [tool.setuptools.dynamic] version = {attr = 'ccbalancer.__version__'}).
version_dynamic = true
test_cmd = ".venv/Scripts/python -m pytest tests/ -v"
test_cmd_quiet = ".venv/Scripts/python -m pytest tests/ -q"

[paths]
progress = "docs/PROGRESS.md"
plan = "docs/PLAN.md"
release_index = "docs/RELEASE.md"
changelog = "CHANGELOG.md"
improvements = "docs/IMPROVEMENTS.md"
fixes = "docs/FIXES.md"
phases_dir = "docs/phases"
improvements_dir = "docs/improvements"
fixes_dir = "docs/fixes"
```

## Project-specific hazards & deviations

- **Version bump: `src/ccbalancer/__init__.py` `__version__` ONLY.** `pyproject.toml` uses
  `dynamic = ['version']` with `version = {attr = 'ccbalancer.__version__'}`. Adding a literal
  `version = 'X.Y.Z'` to `pyproject.toml` **breaks** the dynamic setup — never do it.
  `check_coherence.py` asserts `pyproject.toml` has no literal `version =`.
- **Tests:** `.venv/Scripts/python -m pytest tests/ -v` (Windows venv binary path, per rule
  `python-environment` — do **not** `activate`). `addopts` deselects the `live` marker by default;
  live tests run with `-m live`. There is **no** `tests/unit/` directory. ~432 tests at v0.2.0.
- **Fixes index `Phase` column** holds either a phase id (`11`, `Auth`) or the release version
  (`0.2.0`) — both are seen historically; prefer the phase id when the fix belongs to a numbered
  phase, else the version.
- **Phase numbering** continues past the greenfield range (0–14). Post-prototype phases (P-15+)
  bundle improvements/fixes and are the normal path now.
- **Release CI:** pushing a `v*` tag triggers `.github/workflows/release.yml` (build + smoke on
  Win/Linux/macOS, publish portable zips). `git push origin <branch>` then `git push origin vX.Y.Z`.
- **RELEASE.md** is the internal release→phases index (revived); `CHANGELOG.md` is the public record.
- **`docs/RELEASE.md`** historically used `## X.Y.Z - date` prose notes; the revived form is the
  index table `| Release | Date | Phases | Theme |`.

## Commit / trailers

- Release commit: `release: vX.Y.Z — <theme> (IDs)`. Never add `Co-Authored-By` (repo policy;
  `includeCoAuthoredBy:false` globally). Keep `.claude/settings.json` staged by default.
