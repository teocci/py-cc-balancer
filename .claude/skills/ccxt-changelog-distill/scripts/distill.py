'''Distill ccxt release notes into a candidate list for the cctx digest.

Reads either the JSON array emitted by ``gh api repos/ccxt/ccxt/releases --paginate``
or a markdown release-notes dump, keeps only releases above the ccxt version pinned in
``pyproject.toml``, and mechanically reduces ~1,800 bullets to a few hundred candidates
for an agent to judge into ``docs/cctx/19-changelog-impact.md``.

This script does the deterministic bulk reduction only. It deliberately keeps bullets a
regex cannot safely rule out (see ``HARD_NOISE_RE``); the judgment call belongs to the
agent running the ``ccxt-changelog-distill`` skill.

Key functions:
    main: CLI entry point.
    select_candidates: The parse -> filter -> bucket pipeline.
    run_self_check: Inline assertions guarding this module's known traps.
'''

__all__ = [
    'Candidate',
    'DistillError',
    'Release',
    'Stats',
    'main',
    'select_candidates',
]

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

CHANGED_SECTION = "What's Changed"
GO_TAG_PREFIX = 'go/'
VERSION_TAG_PREFIX = 'v'
BULLET_PREFIX = '* '
DEFAULT_PYPROJECT = 'pyproject.toml'
PULL_URL_TEMPLATE = 'https://github.com/ccxt/ccxt/pull/{number}'
# The output carries em dashes and '·'; a Windows console defaults to a legacy
# codepage (cp949/cp1252) that cannot encode them, so stdout is forced to UTF-8.
OUTPUT_ENCODING = 'utf-8'

CCXT_PIN_RE = re.compile(r'^ccxt\s*==\s*(?P<version>[0-9]+(?:\.[0-9]+)*)$')
VERSION_RE = re.compile(r'^[0-9]+(?:\.[0-9]+)*$')
SECTION_RE = re.compile(r'^##\s+(?P<name>.+?)\s*$')
RELEASE_HEADER_RE = re.compile(
    r'^#\s+\[(?P<tag>[^\]]+)\]\([^)]*\)\s+-\s+(?P<date>\d{4}-\d{2}-\d{2})\s*$'
)
# Bullets arrive in two shapes. The Releases API returns the author's raw text
# ('by @ttodua in https://github.com/ccxt/ccxt/pull/28618'); a rendered dump has
# been through changelog-from-release, which linkifies it ('by [@ttodua](url) in
# [#28618](url)'). Both must clean to the same string, or the two inputs disagree.
AUTHOR_RE = re.compile(r'\s+by \[@[^\]]+\]\([^)]*\)(?:\[bot\])?')
AUTHOR_PLAIN_RE = re.compile(r'\s+by @[A-Za-z0-9._-]+(?:\[bot\])?')
PR_REF_RE = re.compile(r'\s+in \[#(?P<number>\d+)\]\([^)]*\)')
PR_PLAIN_RE = re.compile(r'\s+in https?://\S*?/pull/(?P<number>\d+)\b')
MD_LINK_RE = re.compile(r'\[(?P<text>[^\]]*)\]\([^)]*\)')
BREAKING_RE = re.compile(r'^[a-z]+(?:\([^)]*\))?!:')
CONVENTIONAL_PREFIX_RE = re.compile(
    r'^(?:feat|fix|refactor|perf|chore|build|test|docs|style|ci)(?:\([^)]*\))?!?:'
)

# Provably inert for a Python consumer: dependency bumps, docs, tests, CI, and
# other-language codegen. Nothing matching this can alter our runtime.
HARD_NOISE_RE = re.compile(
    r'^(?:chore|build)\(deps(?:-dev)?\)'
    r'|^(?:docs|test|tests|ci|style)[:(]'
    r'|^(?:chore|fix|feat|refactor|perf|build)\((?:go|php|java|csharp|cs|dotnet|c#)\)'
    r'|^(?:php|go|java|csharp|dotnet)\s*:'
    r'|dependabot',
    re.IGNORECASE,
)

# Our ccxt surface, mirrored from src/ccbalancer/stores/exchange.py. Update this
# alongside that file -- it is the machine-readable statement of what we touch.
SURFACE_RE = re.compile(
    r'\b(?:bybit|binance|okx)\b'
    r'|\(base\)|^base\s*:'
    r'|\bpython\b'
    r'|!:'
    r'|check_?[Rr]equired[Cc]redentials|load_?[Mm]arkets|fetch_?[Bb]alance'
    r'|fetch_?[Tt]icker|fetch_?[Oo]pen_?[Oo]rders|fetch_?OHLCV|fetch_?[Oo]hlcv'
    r'|create_?[Oo]rder|cancel_?[Oo]rder|set_?[Ss]andbox_?[Mm]ode|sandbox|testnet'
    r'|requiredCredentials|enableRateLimit|adjustForTimeDifference|rateLimit'
    r'|NetworkError|InsufficientFunds|InvalidOrder|BaseError|RateLimitExceeded'
    r'|DDoSProtection|ExchangeNotAvailable|RequestTimeout|OrderNotFound'
    r'|safeTicker|safeOrder|safeBalance|safeMarket|parseOrder|parseTicker|parseBalance'
    r'|precision|parseJson|Precise',
    re.IGNORECASE,
)

# ccxt's own Python dependencies are our problem: packaging/ccbalancer.spec collects
# ccxt into a PyInstaller bundle, so a new C-extension dep can break the build in a
# way no unit test catches.
PY_DEPS_RE = re.compile(
    r'\b(?:ecdsa|coincurve|cryptography|toolz|ethereum|eth-\w+|setup\.py|pyproject'
    r'|wheel|pypi|orjson|uvloop|winloop|aiohttp|requests|cryptos|pycryptodome)\b',
    re.IGNORECASE,
)

BUCKET_BREAKING = 'breaking'
BUCKET_BASE = 'base'
BUCKET_PYTHON = 'python'
BUCKET_OTHER = 'other'
EXCHANGE_BUCKETS = ('bybit', 'binance', 'okx')
BUCKET_ORDER = (BUCKET_BREAKING, BUCKET_BASE, *EXCHANGE_BUCKETS, BUCKET_PYTHON, BUCKET_OTHER)

EXCHANGE_RE = {name: re.compile(rf'\b{name}\b', re.IGNORECASE) for name in EXCHANGE_BUCKETS}
BASE_SCOPE_RE = re.compile(r'\(base\)|^base\s*:', re.IGNORECASE)
PYTHON_SCOPE_RE = re.compile(r'\bpython\b|\(py\)', re.IGNORECASE)

_CONTRIB_FIXTURE = (
    "## What's Changed\n"
    '* fix(bybit): real bullet by [@x](https://github.com/x) in '
    '[#1](https://github.com/ccxt/ccxt/pull/1)\n'
    '\n'
    '## New Contributors\n'
    '* [@vsaraikin](https://github.com/vsaraikin) made their first contribution in '
    '[#29187](https://github.com/ccxt/ccxt/pull/29187)\n'
)
# The same upstream bullet as the Releases API returns it (plain) and as a
# rendered dump carries it (linkified). Both must clean to an identical string.
_BULLET_PLAIN = (
    'fix(base): safeTicker - preserve legitimate zero change (fixes #25971) '
    'by @carlotestor in https://github.com/ccxt/ccxt/pull/29105'
)
_BULLET_FIXTURE = (
    'fix(base): safeTicker - preserve legitimate zero change (fixes '
    '[#25971](https://github.com/ccxt/ccxt/issues/25971)) by '
    '[@carlotestor](https://github.com/carlotestor) in '
    '[#29105](https://github.com/ccxt/ccxt/pull/29105)'
)


class DistillError(Exception):
    '''Raised when the inputs cannot be parsed or the ccxt pin cannot be found.'''


@dataclass(frozen=True, slots=True)
class Release:
    '''One upstream ccxt release.

    Attributes:
        tag: Raw tag name, e.g. 'v4.5.65', '4.4.52', or 'go/v4.4.61'.
        version: Numeric version for ordering; None for go/ or unparseable tags.
        date: Publication date as 'YYYY-MM-DD'.
        bullets: Bullet bodies from the "What's Changed" section only.
    '''

    tag: str
    version: tuple[int, ...] | None
    date: str
    bullets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    '''A cleaned bullet that survived mechanical filtering.

    Attributes:
        tag: Release tag the bullet landed in.
        date: Release date.
        bucket: Topic bucket name from BUCKET_ORDER.
        text: Cleaned bullet text, PR number retained as '(#29105)'.
        pr: Upstream PR number as a string, or None if the bullet cited none.
    '''

    tag: str
    date: str
    bucket: str
    text: str
    pr: str | None


@dataclass(frozen=True, slots=True)
class Stats:
    '''Coverage counters proving nothing was silently dropped.

    Attributes:
        releases_scanned: Every release header seen in the input.
        go_skipped: go/-prefixed releases excluded from version comparison.
        releases_above_floor: Releases newer than the floor.
        bullets_above_floor: Bullets belonging to those releases.
        hard_dropped: Bullets removed by HARD_NOISE_RE.
        candidates: Bullets emitted for the agent to judge.
        unclassified_bare: Bullets with no conventional prefix and no surface
            keyword -- the acknowledged blind spot.
        duplicates: Bullets suppressed as a repeat of an earlier release's PR.
        floor: The version floor used.
        first_tag: Oldest release above the floor.
        last_tag: Newest release above the floor.
    '''

    releases_scanned: int
    go_skipped: int
    releases_above_floor: int
    bullets_above_floor: int
    hard_dropped: int
    candidates: int
    unclassified_bare: int
    duplicates: int
    floor: str
    first_tag: str
    last_tag: str


def parse_version(tag: str) -> tuple[int, ...] | None:
    '''Parse a release tag into a comparable version tuple.

    Handles the upstream's inconsistent tagging: 129 of 239 tags omit the 'v'
    prefix, and 8 are Go-only releases that must not be version-compared at all.

    Returns:
        Version parts as ints, or None if the tag is a go/ release or is not a
        plain dotted-numeric version.
    '''
    if tag.startswith(GO_TAG_PREFIX):
        return None
    normalized = tag.removeprefix(VERSION_TAG_PREFIX)
    if not VERSION_RE.fullmatch(normalized):
        return None
    return tuple(int(part) for part in normalized.split('.'))


def extract_bullets(body: str) -> tuple[str, ...]:
    '''Collect bullets from a release body's "What's Changed" section only.

    Scoping by section is what excludes the "New Contributors" blocks, whose
    bullets are format-identical to real ones.
    '''
    bullets: list[str] = []
    in_changed = False
    for line in body.splitlines():
        section = SECTION_RE.match(line)
        if section is not None:
            in_changed = section.group('name') == CHANGED_SECTION
            continue
        if in_changed and line.startswith(BULLET_PREFIX):
            bullets.append(line[len(BULLET_PREFIX) :].strip())
    return tuple(bullets)


def read_releases_json(path: Path) -> list[Release]:
    '''Build releases from a `gh api repos/ccxt/ccxt/releases --paginate` array.'''
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise DistillError(f'{path} is not valid JSON: {exc}') from exc
    if not isinstance(payload, list):
        raise DistillError(f'{path} must hold a JSON array of releases')
    return [
        Release(
            tag=(tag := str(item.get('tag_name', ''))),
            version=parse_version(tag),
            date=str(item.get('published_at', ''))[:10],
            bullets=extract_bullets(str(item.get('body') or '')),
        )
        for item in payload
    ]


def _split_dump(text: str) -> list[tuple[str, str, str]]:
    '''Split a markdown dump into (tag, date, body) segments, one per release.'''
    segments: list[tuple[str, str, str]] = []
    tag = date = ''
    body: list[str] = []
    for line in text.splitlines():
        header = RELEASE_HEADER_RE.match(line)
        if header is None:
            body.append(line)
            continue
        if tag:
            segments.append((tag, date, '\n'.join(body)))
        tag, date, body = header.group('tag'), header.group('date'), []
    if tag:
        segments.append((tag, date, '\n'.join(body)))
    return segments


def read_releases_dump(path: Path) -> list[Release]:
    '''Build releases from a rendered markdown release-notes dump.'''
    segments = _split_dump(path.read_text(encoding='utf-8'))
    if not segments:
        raise DistillError(f'{path} contains no `# [tag](url) - YYYY-MM-DD` headers')
    return [
        Release(tag=tag, version=parse_version(tag), date=date, bullets=extract_bullets(body))
        for tag, date, body in segments
    ]


def read_pinned_ccxt(pyproject_path: Path) -> tuple[int, ...]:
    '''Read the exact ccxt version pinned in pyproject.toml.

    Returns:
        The pinned version as a comparable tuple of ints.

    Raises:
        DistillError: If ccxt is absent or not pinned with '=='.
    '''
    try:
        with pyproject_path.open('rb') as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise DistillError(f'cannot read {pyproject_path}: {exc}') from exc
    for entry in data.get('project', {}).get('dependencies', []):
        match = CCXT_PIN_RE.match(str(entry).strip())
        if match is not None:
            return parse_version(match.group('version'))
    raise DistillError(f'no `ccxt==<version>` pin found in {pyproject_path}')


def is_candidate(body: str) -> bool:
    '''Return whether a bullet may touch our ccxt surface.

    Hard noise is rejected first; everything else that names our surface or ccxt's
    Python dependencies is kept for the agent to judge. Deliberately permissive --
    a regex must not make the "does this matter" call.
    '''
    if HARD_NOISE_RE.search(body):
        return False
    return bool(SURFACE_RE.search(body) or PY_DEPS_RE.search(body))


def is_unclassified_bare(body: str) -> bool:
    '''Return whether a bullet is a bare title with no prefix and no surface keyword.'''
    if HARD_NOISE_RE.search(body) or is_candidate(body):
        return False
    return not CONVENTIONAL_PREFIX_RE.match(body)


def clean_bullet(body: str) -> str:
    '''Strip author attribution and unwrap links, retaining the PR number.

    Accepts both the API's plain-text shape and a rendered dump's linkified shape.
    The PR number survives as a trailing '(#29105)' because it is the join key that
    makes digest completeness verifiable as a set difference.
    '''
    pr = _pr_of(body)
    text = body
    for pattern in (PR_REF_RE, PR_PLAIN_RE, AUTHOR_RE, AUTHOR_PLAIN_RE):
        text = pattern.sub('', text)
    text = MD_LINK_RE.sub(lambda m: m.group('text'), text)
    text = ' '.join(text.split())
    return f'{text} (#{pr})' if pr is not None else text


def bucket_of(body: str) -> str:
    '''Classify a bullet into one topic bucket, breaking taking precedence.'''
    if BREAKING_RE.match(body):
        return BUCKET_BREAKING
    for name, pattern in EXCHANGE_RE.items():
        if pattern.search(body):
            return name
    if BASE_SCOPE_RE.search(body):
        return BUCKET_BASE
    if PYTHON_SCOPE_RE.search(body) or PY_DEPS_RE.search(body):
        return BUCKET_PYTHON
    return BUCKET_OTHER


def _pr_of(body: str) -> str | None:
    '''Return the PR number a bullet cites in either input shape, or None.'''
    for pattern in (PR_REF_RE, PR_PLAIN_RE):
        match = pattern.search(body)
        if match is not None:
            return match.group('number')
    return None


def select_candidates(
    releases: list[Release], floor: tuple[int, ...]
) -> tuple[list[Candidate], Stats]:
    '''Reduce every release above ``floor`` to a judged-by-agent candidate list.'''
    above = sorted(
        (r for r in releases if r.version is not None and r.version > floor),
        key=lambda r: r.version,
    )
    counters = {'hard': 0, 'bare': 0, 'bullets': 0, 'dupes': 0}
    candidates: list[Candidate] = []
    seen_prs: set[str] = set()
    for release in above:
        counters['bullets'] += len(release.bullets)
        _collect_release(release, candidates, seen_prs, counters)
    candidates.sort(key=lambda c: (BUCKET_ORDER.index(c.bucket), c.date, c.text))
    return candidates, _build_stats(releases, above, candidates, counters, floor)


def _collect_release(
    release: Release, candidates: list[Candidate], seen_prs: set[str], counters: dict[str, int]
) -> None:
    '''Append one release's surviving bullets to ``candidates``, updating counters.'''
    for body in release.bullets:
        if HARD_NOISE_RE.search(body):
            counters['hard'] += 1
            continue
        if is_unclassified_bare(body):
            counters['bare'] += 1
            continue
        if not is_candidate(body):
            continue
        pr = _pr_of(body)
        if pr is not None and pr in seen_prs:
            counters['dupes'] += 1
            continue
        if pr is not None:
            seen_prs.add(pr)
        candidates.append(
            Candidate(
                tag=release.tag,
                date=release.date,
                bucket=bucket_of(body),
                text=clean_bullet(body),
                pr=pr,
            )
        )


def _build_stats(
    releases: list[Release],
    above: list[Release],
    candidates: list[Candidate],
    counters: dict[str, int],
    floor: tuple[int, ...],
) -> Stats:
    '''Assemble the coverage counters for the selection just performed.'''
    return Stats(
        releases_scanned=len(releases),
        go_skipped=sum(1 for r in releases if r.tag.startswith(GO_TAG_PREFIX)),
        releases_above_floor=len(above),
        bullets_above_floor=counters['bullets'],
        hard_dropped=counters['hard'],
        candidates=len(candidates),
        unclassified_bare=counters['bare'],
        duplicates=counters['dupes'],
        floor='.'.join(str(part) for part in floor),
        first_tag=above[0].tag if above else '',
        last_tag=above[-1].tag if above else '',
    )


def _render_header(stats: Stats) -> list[str]:
    '''Render the stats preamble shared by the markdown output.'''
    return [
        f'# ccxt release candidates — above {stats.floor}',
        '',
        f'floor: {stats.floor} · releases_scanned: {stats.releases_scanned} · '
        f'go_skipped: {stats.go_skipped}',
        f'releases_above_floor: {stats.releases_above_floor} '
        f'({stats.first_tag} … {stats.last_tag})',
        f'bullets_above_floor: {stats.bullets_above_floor} · '
        f'hard_dropped: {stats.hard_dropped} · duplicates: {stats.duplicates} · '
        f'candidates: {stats.candidates} · unclassified_bare: {stats.unclassified_bare}',
        '',
    ]


def render_markdown(candidates: list[Candidate], stats: Stats) -> str:
    '''Render candidates as bucketed markdown for an agent to read.'''
    lines = _render_header(stats)
    for bucket in BUCKET_ORDER:
        rows = [c for c in candidates if c.bucket == bucket]
        if not rows:
            continue
        lines.append(f'## {bucket} ({len(rows)})')
        lines.extend(f'- `{c.tag}` {c.date} — {c.text}' for c in rows)
        lines.append('')
    return '\n'.join(lines)


def render_json(candidates: list[Candidate], stats: Stats) -> str:
    '''Render the identical records as JSON for mechanical verification.'''
    payload = {
        'stats': {
            'releases_scanned': stats.releases_scanned,
            'go_skipped': stats.go_skipped,
            'releases_above_floor': stats.releases_above_floor,
            'bullets_above_floor': stats.bullets_above_floor,
            'hard_dropped': stats.hard_dropped,
            'candidates': stats.candidates,
            'unclassified_bare': stats.unclassified_bare,
            'duplicates': stats.duplicates,
            'floor': stats.floor,
            'first_tag': stats.first_tag,
            'last_tag': stats.last_tag,
        },
        'candidates': [
            {
                'tag': c.tag,
                'date': c.date,
                'bucket': c.bucket,
                'text': c.text,
                'pr': c.pr,
                'url': PULL_URL_TEMPLATE.format(number=c.pr) if c.pr else None,
            }
            for c in candidates
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def collect_unclassified(releases: list[Release], floor: tuple[int, ...]) -> list[Candidate]:
    '''Return the bare-title bullets that ``select_candidates`` counts but drops.'''
    rows: list[Candidate] = []
    for release in releases:
        if release.version is None or release.version <= floor:
            continue
        rows.extend(
            Candidate(
                tag=release.tag,
                date=release.date,
                bucket=BUCKET_OTHER,
                text=clean_bullet(body),
                pr=_pr_of(body),
            )
            for body in release.bullets
            if is_unclassified_bare(body)
        )
    return rows


def run_self_check() -> int:
    '''Assert the traps this script exists to avoid. Returns a process exit code.'''
    checks: list[tuple[str, bool]] = [
        ('string-sort trap', parse_version('4.4.100') > parse_version('4.4.94')),
        ('v-prefix equivalence', parse_version('v4.5.7') == parse_version('4.5.7')),
        ('go releases rejected', parse_version('go/v4.4.61') is None),
        ('short-tuple ordering', parse_version('4.0.3') < parse_version('4.4.94')),
        ('contributors excluded', len(extract_bullets(_CONTRIB_FIXTURE)) == 1),
        ('surface beats churn', is_candidate('fix(base): reduce strictNullChecks errors')),
        (
            'py deps kept',
            is_candidate('Remove vendored ecdsa static dependency, use coincurve + cryptography'),
        ),
        ('deps bumps dropped', not is_candidate('chore(deps): bump undici from 7.27.2 to 7.28.0')),
        ('pr number retained', clean_bullet(_BULLET_FIXTURE).endswith('(#29105)')),
        ('author stripped', 'carlotestor' not in clean_bullet(_BULLET_FIXTURE)),
        ('breaking bucketed', bucket_of('fix(aftermath)!: delist') == BUCKET_BREAKING),
        # The two inputs must agree. The API serves plain text; a dump serves the
        # linkified rendering of the same bullet. Divergence here silently strips
        # PR numbers from the API path and breaks digest completeness checking.
        ('plain pr extracted', _pr_of(_BULLET_PLAIN) == '29105'),
        ('plain author stripped', 'carlotestor' not in clean_bullet(_BULLET_PLAIN)),
        ('inputs agree', clean_bullet(_BULLET_PLAIN) == clean_bullet(_BULLET_FIXTURE)),
    ]
    failures = [name for name, ok in checks if not ok]
    for name in failures:
        print(f'FAIL: {name}', file=sys.stderr)
    print(f'self-check: {len(checks) - len(failures)}/{len(checks)} passed')
    return 1 if failures else 0


def _build_parser() -> argparse.ArgumentParser:
    '''Build the CLI parser.'''
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--releases', type=Path, help='JSON array from `gh api ... /releases`')
    source.add_argument('--dump', type=Path, help='rendered markdown release-notes dump')
    parser.add_argument('--pyproject', type=Path, default=Path(DEFAULT_PYPROJECT))
    parser.add_argument('--since', help='override the version floor, e.g. 4.4.94')
    parser.add_argument('--out', type=Path, help='write here instead of stdout')
    parser.add_argument('--json', action='store_true', help='emit machine-readable records')
    parser.add_argument('--include-unclassified', action='store_true')
    parser.add_argument('--self-check', action='store_true')
    return parser


def _resolve_floor(args: argparse.Namespace) -> tuple[int, ...]:
    '''Resolve the version floor from --since or the pyproject pin.'''
    if args.since is None:
        return read_pinned_ccxt(args.pyproject)
    floor = parse_version(args.since)
    if floor is None:
        raise DistillError(f'--since {args.since!r} is not a dotted-numeric version')
    return floor


def _render(args: argparse.Namespace, releases: list[Release], floor: tuple[int, ...]) -> str:
    '''Select candidates and render them in the requested format.'''
    candidates, stats = select_candidates(releases, floor)
    if args.include_unclassified:
        candidates.extend(collect_unclassified(releases, floor))
    return render_json(candidates, stats) if args.json else render_markdown(candidates, stats)


def main(argv: list[str] | None = None) -> int:
    '''Run the distiller. Returns a process exit code.'''
    args = _build_parser().parse_args(argv)
    if args.self_check:
        return run_self_check()
    if args.releases is None and args.dump is None:
        print('error: one of --releases, --dump, or --self-check is required', file=sys.stderr)
        return 2
    try:
        releases = (
            read_releases_json(args.releases)
            if args.releases is not None
            else read_releases_dump(args.dump)
        )
        output = _render(args, releases, _resolve_floor(args))
    except DistillError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    if args.out is None:
        sys.stdout.reconfigure(encoding=OUTPUT_ENCODING)
        print(output)
    else:
        args.out.write_text(output + '\n', encoding=OUTPUT_ENCODING)
    return 0


if __name__ == '__main__':
    sys.exit(main())
