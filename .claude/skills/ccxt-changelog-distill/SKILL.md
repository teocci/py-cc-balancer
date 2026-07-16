---
name: ccxt-changelog-distill
description: Regenerate docs/cctx/19-changelog-impact.md — the task-oriented digest of ccxt changes above our pinned version. Run after bumping the ccxt pin in pyproject.toml, or when checking whether the cctx manual is stale.
triggers:
  - "bump ccxt"
  - "update ccxt"
  - "ccxt pin"
  - "regenerate ccxt changelog"
  - "refresh cctx digest"
  - "what changed in ccxt since our pin"
  - "is the cctx manual stale"
---

# ccxt-changelog-distill

Rebuilds `docs/cctx/19-changelog-impact.md` from ccxt's upstream release notes.

The point is token economy: upstream ships ~11,000 release bullets across 239 releases (~390K
tokens). `distill.py` does the deterministic reduction to ~330 candidates (~7K tokens); you spend
judgment only on those. **Never read raw release notes into context** — that is what the script is
for.

## Required inputs

Before running, confirm:
- `gh auth status` succeeds (or you have a local markdown dump for `--dump`).
- The ccxt pin in `pyproject.toml` — the script reads it, but you need it to sanity-check output.
- Whether this run follows a **pin bump**. If so, read the Notes at the bottom first: chunks
  `01`-`18` become stale in a way this skill does not fix.
- A scratchpad path for intermediates. They never belong in `docs/`.

## Step 1 — Confirm the floor

```bash
grep -o 'ccxt==[0-9.]*' pyproject.toml
grep -o 'ccxt==[0-9.]*' docs/cctx/19-changelog-impact.md   # if it exists
```

If the two differ, the digest is stale — that mismatch *is* the signal to regenerate. If they match
and no new ccxt release exists, stop; there is nothing to do.

## Step 2 — Acquire the release notes

```bash
SCRATCH='<scratchpad>'
gh api repos/ccxt/ccxt/releases --paginate > "$SCRATCH/releases.json"
.venv/Scripts/python -c "import json;print(len(json.load(open(r'$SCRATCH/releases.json',encoding='utf-8'))),'releases')"
```

Expect **≥239** releases. A lower number means `--paginate` truncated — stop and retry; a partial
fetch silently shortens the range while the stats still look plausible.

Never write this file into `docs/`. If `gh` is unavailable, use `--dump <path>` against a local
markdown export instead. Do **not** fall back to `WebFetch`: 239 releases is not viable that way,
and a partial fetch is worse than a loud failure.

## Step 3 — Run the distiller

```bash
V=.venv/Scripts/python
D=.claude/skills/ccxt-changelog-distill/scripts/distill.py

$V $D --self-check                                            # must print 14/14 passed
$V $D --releases "$SCRATCH/releases.json" --out "$SCRATCH/candidates.md"
```

Read `candidates.md` (~7K tokens). **This is the only large read in the workflow.**

The script is deliberately permissive: it keeps bullets a regex cannot safely rule out. Deciding
what actually matters is Step 4's job, not the regex's.

## Step 4 — Semantic pass

Judge each candidate against our real surface. All ccxt use lives in
`src/ccbalancer/stores/exchange.py` — read it if anything is unclear.

**KEEP** if the change touches:
- One of our 9 calls: `check_required_credentials`, `load_markets`, `fetch_balance`, `fetch_ticker`,
  `fetch_open_orders`, `fetch_ohlcv`, `create_order`, `cancel_order`, `set_sandbox_mode`.
- One of our 4 caught exceptions — `NetworkError`, `InsufficientFunds`, `InvalidOrder`, `BaseError`
  — or their retried subclasses. **Exchange error-mapping changes always qualify**: they decide
  which class a venue error raises, which decides whether we retry.
- A config key we set: `apiKey`, `secret`, `password`, `timeout`, `enableRateLimit`,
  `options.adjustForTimeDifference`.
- A structure field we read: market `precision.amount` / `active`; ticker `last`/`bid`/`ask`;
  balance `free`/`total`; order `id`/`symbol`/`clientOrderId`/`average`/`filled`/`fee.cost`/
  `fee.currency`/`side`/`amount`/`price`; OHLCV indices 0,2,3,4,5.
- ccxt's **Python dependency graph or import behavior** — we ship a PyInstaller bundle that
  collects ccxt (`packaging/ccbalancer.spec`), so a new C-extension dep is a build break no test
  catches.
- bybit/binance/okx request or response mapping for any of the above.

**DROP** if it is language-internal (`strictNullChecks`, transpiler, Go/PHP/Java/C# codegen,
`node-fetch`/undici), touches a method we never call, an exchange outside `SUPPORTED_EXCHANGES`, or
is docs/site/ccxt-cli/skills.

Worked drops from real data:

| Candidate | Verdict |
|---|---|
| `fix(base): reduce strictNullChecks errors in base infra` | DROP — TypeScript type-checking; no Python runtime effect |
| `fix(base): go Precise.Div must truncate toward zero` | DROP — Go output only |
| `fix(okx): reduce strictNullChecks errors + transpiler-safe ternaries` | DROP — names our exchange, changes nothing observable |
| `feat(base): replace node-fetch with native fetch (undici)` | DROP — JS transport |
| `fix(binance): fetchTradesMethod` | DROP — we never call `fetch_trades` |
| `refactor: default precision` | KEEP — we read `market['precision']['amount']` |
| `bybit errors mapping` | KEEP — decides our retry boundary |

**Every `!:` bullet must be resolved.** It lands either as a digest entry or as a row in "Breaking
Changes That Do NOT Affect Us" with a stated reason. Never drop one silently — Step 8's check
enforces this by exit code.

## Step 5 — Write the digest

Write `docs/cctx/19-changelog-impact.md`. Keep the existing section order and the header block (`Purpose` /
`Pin` / `Covers` / `Scope` / `Source`), updating the pin, range, release count and bullet count from
the stats the script printed.

Entry format — version tag, PR link, and a mandatory verdict line on every entry:

```markdown
- **`v4.5.48`** · `refactor: default precision` ([#28347](https://github.com/ccxt/ccxt/pull/28347))
  → **For us**: <concrete consequence, citing the file:line it lands on> — **Action**: <none | verify on bump | change code>
```

Group related PRs into one entry rather than repeating a verdict. Keep the two accounting sections —
the breaking ledger and "Deliberately Excluded" — or absence stops being evidence: a reader can no
longer tell "nothing changed" from "nobody checked".

## Step 6 — Update INDEX.md

`docs/cctx/INDEX.md` references chunk 19 in six places — the `Source` line, the `Version` line (which
names the pin), two Fast Start rows, the File Inventory row, the Agent Loading Strategy step 0, and
the "What's NOT in this Manual" caveat. Update the pin everywhere it appears.

Recompute every count from real `wc -l` output — never estimate. The `Lines` column and the `Stats`
line drift silently as chunks are edited:

```bash
.venv/Scripts/python - <<'PY'
import pathlib
files = sorted(p for p in pathlib.Path('docs/cctx').glob('*.md') if p.name[0].isdigit())
tl = tc = 0
for p in files:
    t = p.read_text(encoding='utf-8')
    tl += len(t.splitlines()); tc += len(t)
    print(f'{p.name}: {len(t.splitlines())} lines')
print(f'TOTAL: {len(files)} chunks | {tl:,} lines | ~{tc//4:,} tokens')
PY
```

## Step 7 — Discard the raw notes

```bash
rm -f docs/cctx/CHANGELOG.md                    # only if a legacy raw dump reappeared
rm -f "$SCRATCH/releases.json" "$SCRATCH/candidates.md"
```

`.gitignore` carries a tripwire for `docs/cctx/CHANGELOG.md`. Leave it there.

## Step 8 — Verify

```bash
# breaking-change completeness — exit code is the gate
$V $D --releases "$SCRATCH/releases.json" --json | $V -c "
import json, re, sys
d = json.load(sys.stdin)
breaking = {c['pr'] for c in d['candidates'] if c['bucket'] == 'breaking' and c['pr']}
cited = set(re.findall(r'/pull/(\d+)', open('docs/cctx/19-changelog-impact.md', encoding='utf-8').read()))
missing = breaking - cited
print(f'breaking={len(breaking)} cited={len(breaking & cited)} missing={sorted(missing)}')
sys.exit(1 if missing else 0)"

# entry-format invariant — the two counts must match
grep -c '^- \*\*`v4\.' docs/cctx/19-changelog-impact.md
grep -c '→ \*\*For us\*\*' docs/cctx/19-changelog-impact.md

# pin coherence — must be identical
grep -o 'ccxt==[0-9.]*' pyproject.toml docs/cctx/19-changelog-impact.md
```

## Verification checklist

- [ ] `distill.py --self-check` exits 0
- [ ] `gh api` returned ≥ 239 releases (no silent truncation)
- [ ] Digest `**Pin**` line matches `ccxt==` in `pyproject.toml`
- [ ] Digest `**Covers**` states the full range, release count, and bullets reviewed
- [ ] Every breaking PR from `--json` appears in the digest (set-difference empty, exit 0)
- [ ] Every entry carries a version tag **and** a `→ **For us**` line (counts match)
- [ ] INDEX.md Stats line chunk count and line count recomputed, not estimated
- [ ] INDEX.md Fast Start, File Inventory, and "What's NOT" rows reference `19-changelog-impact.md`
- [ ] `docs/cctx/CHANGELOG.md` does not exist
- [ ] Scratchpad artifacts removed
- [ ] `git status --short docs/cctx/` shows only intended files
- [ ] Digest is ≤ ~8K tokens (`wc -c` ÷ 4)

## Notes

- **The digest is a delta against a moving base.** Chunks `01`-`18` describe ccxt *at the pin*. When
  the pin bumps, entries below the new pin do not vanish — they become *current behavior*, and the
  chunks that contradict them are now wrong. **This skill regenerates the delta; it does not
  reconcile chunks `01`-`18`.** After a bump, walk the outgoing digest's entries and decide per
  entry whether a chunk needs editing. Nothing automates that.
- **Never write raw release notes into `docs/`.** A 390K-token file inside `docs/cctx/` is a context
  bomb: that directory is exactly the glob an agent runs after reading INDEX.md.
- **`SURFACE_RE` in `distill.py` is the machine-readable statement of our ccxt surface**, mirrored by
  hand from `src/ccbalancer/stores/exchange.py`. If our ccxt usage changes — a new method call, a new
  exception caught, a new exchange in `SUPPORTED_EXCHANGES` — update that regex in the same commit,
  or the next regeneration will silently miss the change.
- **The two inputs must agree.** The Releases API serves plain-text bullets
  (`by @x in https://…/pull/N`); a rendered dump serves the linkified form (`by [@x](…) in [#N](…)`).
  `--self-check` asserts both clean to an identical string. If that check ever fails, the API path
  will silently produce no PR numbers and Step 8's completeness gate becomes meaningless.
- `phase-complete` does not apply to a digest refresh — no version bump, no phase ID. Commit plainly,
  e.g. `docs: refresh ccxt digest for <new pin>`.
