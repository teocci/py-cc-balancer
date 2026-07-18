# Skills vs. Python Repos

## Why This Rule Exists

Rules `01`–`14` and [python-environment.md](python-environment.md) were written for **Python
repos/packages**. Most agentic work now runs through **skills**, which are a different shape. Read
this before applying the other rules to skill code — several of their defaults are wrong for skills.

## A Skill Is Not a Repo

- A skill's Python lives in `<skill>/scripts/`, next to `SKILL.md` (and an optional
  `requirements.txt`). It is a **small, self-contained toolkit**, not a package under
  `src/mypackage/`.
- The **host project can be anything or nothing** — a Go service, a docs/video/TTS project, or a
  standalone personal skill with no host project at all. The rules must still hold for the skill's
  Python regardless of what the host project is written in.
- Do **not** scaffold a repo layout (`src/`, `stores/`, `managers/`, `pyproject.toml`, package
  `__init__.py` exports) for a skill. Keep it flat.

## Shared Foundation Library Skills

The "each skill is flat and self-contained" default above has one escape hatch: a **skill family**
that shares real code. When two or more skills ship and evolve **together** and would otherwise each
carry a copy of the same **substantial** module, extract that module into **one dedicated library
skill** the others import. This is DRY across a family — not a license to over-abstract. Do **not**
reach for it for a one-off snippet, or for skills meant to be individually portable.

**The pattern.** The library lives once in a dedicated skill's `scripts/`. That skill is
**non-invokable**: its SKILL.md `description` states it is a code library imported by its siblings,
not invoked directly, so the model won't false-trigger it. Consumers **import** the module; they do
not copy it.

**The uniform bootstrap.** Every skill script lives at `.claude/skills/<skill>/scripts/`, a layout
this rule fixes as an invariant — so `parents[2]` is always the shared `skills/` dir. A consumer
adds this before importing (copy the stub verbatim; never duplicate the library itself):

```python
# skill scripts live at .claude/skills/<skill>/scripts/ -> parents[2] is the shared skills/ dir
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '<lib-skill>' / 'scripts'))
import <module> as <alias>  # noqa: E402
```

- `__file__`-relative and **zero-install** on purpose: no package to `pip install`, so the family
  stays clone-and-run. The `sys.path.insert` adds the *directory*, so any number of modules in the
  library's `scripts/` are importable off the same line — no extra bootstrap.
- `# noqa: E402` is required: the import follows executable code (`sys.path.insert`), which trips
  pycodestyle E402 ("import not at top of file"); the marker suppresses that one lint on the line.
- The **alternative** — make the library an editable-installed package (`pip install -e`) so
  consumers just `import <module>` with no stub — is more conventional in an ordinary repo, but it
  adds a mandatory setup step (fresh clone → `ModuleNotFoundError` until installed) and breaks
  clone-and-run. Reach for it only if zero-stub call sites are worth that setup cost.

**Portability guardrail.** The unit of portability is now the **family** — the library and its
consumers travel together. Copy the family, not one member.

**Prose vs. code.** Cross-skill *prose* references use a relative link or a `plugin:skill` marker
(never `@`-force-load, which burns context before it's needed); cross-skill *code* uses the import
bootstrap above. And a foundation skill de-duplicates **code that is actually copied** — prose that
is already single-source-and-referenced (a shared `references/*.md` the siblings link to) stays where
it lives; don't relocate it for symmetry.

In this repo, the `phase-*` family is the worked example: `phase-lib` owns the shared `tracklib`
module, `phase-flow` keeps the shared `conventions.md` prose (already single-source), and
`phase-start` / `phase-status` / `phase-complete` / `phase-flow` import `tracklib` via the bootstrap.

## The Venv Still Applies (Always)

A skill's Python **still runs under a `.venv`** — even when the host project is non-Python. Never
the system interpreter. All venv mechanics (location, `.gitignore`, standalone fallback, declaring
deps) live in one place: **[python-environment.md](python-environment.md)**. This file does not
restate them.

## Why a Skill Ships Scripts

A skill's `scripts/` exist to move work off the token stream and into code. When a step is
better done by a script than by the agent reasoning inline, a script should earn its place by:

- **Determinism** — a script gives the same output for the same input every time; prefer it for
  anything the LLM would otherwise do probabilistically (parsing, math, formatting, validation,
  file/data transforms).
- **Token efficiency** — offload bulk/mechanical work to code instead of spending tokens on it.
- **Reusability** — a small, well-scoped script is callable across invocations and skills; a
  one-off inline reasoning pass is not.
- **Agent-optimized I/O** — by default, scripts should **consume and emit machine-friendly,
  token-lean I/O** (compact JSON, stable keys, structured records) that another agent or script
  can parse directly — not prose meant for a person. Keep it lean **without dropping signal the
  agent needs to act**, especially on errors: emit a structured, actionable error, not a wall of
  text and not a bare exit code.

**Exception — human-facing output.** When the skill (or its orchestrator) is meant to produce
content for a person — a report, a message, a rendered document — that output should be
human-friendly, not token-optimized. Optimize the *internal* hops between scripts/agents for
tokens; optimize the *final human deliverable* for the reader.

## How Each Rule Applies to a Skill

| Rule | Applies to a skill? |
|------|---------------------|
| [02-python-style.md](02-python-style.md) | **As-is** |
| [03-python-modern.md](03-python-modern.md) | **As-is** |
| [05-security.md](05-security.md) | **As-is** |
| [06-no-spaghetti.md](06-no-spaghetti.md) | **As-is** |
| [10-error-handling.md](10-error-handling.md) | **As-is** |
| [12-documentation.md](12-documentation.md) | **As-is** |
| [python-environment.md](python-environment.md) | **As-is** — see its Scope section for skills |
| [01-pre-implementation.md](01-pre-implementation.md) | **Judgment** — keep the analysis brief for a small script |
| [04-no-hardcoding.md](04-no-hardcoding.md) | **Judgment** — config via env/args; no `config.toml` base-dir chain |
| [07-module-organization.md](07-module-organization.md) | **Judgment** — size targets apply, but `__all__`/`__init__.py` package exports and the circular-import DAG guidance are **N/A** (a script is not a package) |
| [09-performance.md](09-performance.md) | **Judgment** — only when the skill actually processes large data |
| [11-testing.md](11-testing.md) | **Judgment** — only if the skill ships tests |
| [08-project-structure.md](08-project-structure.md) | **N/A** — skills don't use the `src/mypackage/` layout |
| [13-credentials.md](13-credentials.md) | **Partial** — no `auth` subcommands / keyring lifecycle; only its **Invariants** apply |
| [14-file-locations.md](14-file-locations.md) | **N/A** — a skill owns no `~/.<tool>/` base dir |
