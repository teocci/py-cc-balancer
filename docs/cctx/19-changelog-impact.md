# CCXT Upstream Change Impact — Since Our Pin

> **Not a changelog.** This is an *impact assessment*: every entry is a judgment about **our**
> surface, and the large majority of upstream's changes are deliberately absent. For a neutral
> record of what ccxt changed, read <https://github.com/ccxt/ccxt/releases>.
>
> **Purpose**: What changed in ccxt **after** the version we pin — and what each change means for
> *this* project. Read this before bumping the ccxt pin, or when a chunk `01`-`18` seems to
> contradict observed behavior.
> **Pin**: `ccxt==4.4.94` (`pyproject.toml`). Chunks `01`-`18` describe ccxt **at this pin**; this
> file is the delta above it.
> **Covers**: `v4.4.95` … `v4.5.65` — 72 releases, 2025-07-17 → 2026-07-13, 1,840 upstream bullets
> reviewed.
> **Scope**: Only changes touching this project's ccxt surface — the 9 methods, 4 exception classes,
> config keys and structure fields used in `src/ccbalancer/stores/exchange.py`, the three exchanges
> in `SUPPORTED_EXCHANGES`, and the Python wheel we bundle. Everything else is excluded by design;
> the last two sections say exactly what and why.
> **Source**: `GET /repos/ccxt/ccxt/releases`. **Regenerate**: run the `ccxt-changelog-distill` skill.

---

## 🚨 Breaking Changes That Affect Us

**None.** All 10 upstream `!:` changes above the pin are ledgered below as not-our-surface — 6 are
delistings of exchanges we don't support, 2 touch exchanges we don't support, and 2 touch `Precise`,
which we never call directly. The two `Precise` ones are the softest calls in this file; see the
warning under the ledger.

## 🔧 Base / Unified API

- **`v4.5.48`** · `refactor: default precision` ([#28347](https://github.com/ccxt/ccxt/pull/28347))
  → **For us**: the single highest-risk entry here. `portfolio_manager.py:100-101` reads
  `market['precision']['amount']` and feeds it to `precision_to_decimals` in `utils/money.py`, which
  drives every order quantity we round. A change to the *default* precision value changes what that
  field holds when an exchange doesn't specify one. — **Action**: on bump, print
  `market['precision']['amount']` for each configured pair on all three exchanges and diff against
  4.4.94 before trading.

- **`v4.5.65`** · `base: parseJson fast path — requote numbers only when an unsafe integer is present` ([#29119](https://github.com/ccxt/ccxt/pull/29119))
  → **For us**: `parseJson` decides whether numeric JSON fields arrive as `str` or `float`. Every
  price and amount we read (`ticker.last/bid/ask`, `order.average/filled/price`,
  `market.precision.amount`) flows through it, and `utils/money.py` feeds those straight into
  `Decimal` — where `Decimal('0.1')` and `Decimal(0.1)` are *not* the same number. — **Action**: on
  bump, assert the types of those fields, not just their values.

- **`v4.5.65`** · `refactor: guard loadMarkets calls` ([#29111](https://github.com/ccxt/ccxt/pull/29111))
  → **For us**: we call `load_markets(reload)` explicitly (`exchange.py:106`) and depend on the
  market cache for `precision.amount` and `active`. Added guards change when an implicit reload
  fires. Also relevant to `options.adjustForTimeDifference`, whose clock offset ccxt loads *during*
  `loadMarkets` (see `exchange.py:206-210`). — **Action**: verify `load_markets(reload=True)` still
  forces a refetch, and that the time offset is still applied.

- **`v4.5.52`** · `fix(base): avoid params={} mutation in trigger/SL/TP wrappers (Python pollution)` ([#28508](https://github.com/ccxt/ccxt/pull/28508))
  → **For us**: a Python mutable-default-argument bug on the `createOrder` path — the exact path
  `exchange.py:147-153` uses. We build a fresh `params` dict per call, so we were never exposed, but
  this confirms `params` was being mutated across calls upstream. — **Action**: none.

- **`v4.4.97`** · `decimalToPrecision - update all langs` ([#26289](https://github.com/ccxt/ccxt/pull/26289)) · **`v4.4.98`** · `fix(python): decimalToPrecision - precision arg` ([#26547](https://github.com/ccxt/ccxt/pull/26547))
  → **For us**: `decimalToPrecision` is ccxt's rounding helper. We deliberately do **not** use it —
  `utils/money.py:21-44` rounds locally with `Decimal`. Listed because it's the documented
  alternative to our divergence, and a reviewer will ask why we don't use it. — **Action**: none.

- **`v4.5.65`** · `fix(base): safeTicker - preserve legitimate zero change` ([#29105](https://github.com/ccxt/ccxt/pull/29105))
  → **For us**: `safeTicker` is the parser behind `fetch_ticker`. The fix targets the `change`
  field; we read only `last`, `bid`, `ask` (`portfolio_manager.py:57`, `:65-66`), which are
  untouched. Listed because it sits directly on our path. — **Action**: none.

- **`v4.5.8`** · `Precise Reduce, String: int64 handling` ([#26948](https://github.com/ccxt/ccxt/pull/26948))
  → **For us**: `Precise` is ccxt's internal string math. We never call it, but base parsers use it
  to produce the ticker/order values we read. Pairs with the two `precise!` breaking changes in the
  ledger below. — **Action**: none, unless prices look wrong after a bump.

## 🟠 Bybit (our default exchange)

- **`v4.5.30`** · `bybit errors mapping` ([#27587](https://github.com/ccxt/ccxt/pull/27587)) · **`v4.5.35`** · `bybit error mapping` ([#27765](https://github.com/ccxt/ccxt/pull/27765))
  → **For us**: the most consequential Bybit entry. Error mapping decides *which ccxt exception
  class* a given venue error code raises, and `exchange.py:176-190` branches entirely on that:
  `NetworkError` is retried with backoff, `InsufficientFunds`/`InvalidOrder` become domain errors,
  everything else falls to `BaseError`. Remapping a code across that boundary silently changes
  whether we retry — and `create_order` runs with `_NO_RETRIES` precisely because a wrong retry
  risks a duplicate fill. — **Action**: on bump, re-check that the codes for insufficient balance
  and rejected order still map to `InsufficientFunds`/`InvalidOrder`, and that no rejection has
  become a retried `NetworkError`.

- **`v4.5.6`** · `feat(bybit): new fee responses for order endpoints` ([#26821](https://github.com/ccxt/ccxt/pull/26821))
  → **For us**: `execution_manager.py:210`, `:217-218` reads `order['fee']['cost']` and
  `order['fee']['currency']` off the `create_order` response and writes them to the ledger. A
  changed fee response shape means wrong or missing fees in our own accounting — and since we treat
  the create response as terminal (no `fetch_order` follow-up), nothing would correct it later.
  — **Action**: on bump, place one testnet limit order and confirm `fee.cost`/`fee.currency` are
  still populated.

- **`v4.4.96`** · `bybit, okx - unify fetchMarkets options` ([#26391](https://github.com/ccxt/ccxt/pull/26391))
  → **For us**: `load_markets` feeds `market['precision']['amount']` and `market['active']`
  (`portfolio_manager.py:100-108`). A `fetchMarkets` unification can move or rename those.
  — **Action**: covered by the `#28347` precision check above.

## 🟡 Binance

- **`v4.5.27`** · `binance error mapping` ([#27473](https://github.com/ccxt/ccxt/pull/27473))
  → **For us**: same reasoning as the Bybit error-mapping entry — it decides our retry behavior.
  — **Action**: same check, against Binance.

- **`v4.5.65`** · `refactor(binance): normalize options` ([#29152](https://github.com/ccxt/ccxt/pull/29152))
  → **For us**: we set `options: {'adjustForTimeDifference': True}` at construction
  (`exchange.py:210`) to stop local clock drift tripping the venue's `recv_window`. An options
  normalization sweep — applied across ~20 exchanges in `v4.5.65` — can rename or relocate option
  keys, and a silently-ignored key means intermittent auth failures on signed requests, not a loud
  error. This is F-1 territory (`docs/fixes/F-1.md`). — **Action**: on bump, assert
  `client.options['adjustForTimeDifference']` is still read, and smoke-test a private call on
  testnet.

- **`v4.5.7`** · `fix(binance): throw error for futures+sandbox access` ([#26941](https://github.com/ccxt/ccxt/pull/26941))
  → **For us**: we call `set_sandbox_mode(self.testnet)` unconditionally (`exchange.py:213`). This
  makes a previously-silent sandbox misconfiguration raise. — **Action**: on bump, run the testnet
  path for Binance once.

- **`v4.5.57`** · `fix(binance): fetchOpenOrders doesn't support swap market` ([#28774](https://github.com/ccxt/ccxt/pull/28774))
  → **For us**: `fetch_open_orders(symbol)` (`exchange.py:118`) backs `execution_manager.is_ours`,
  which matches our `CCB_PREFIX` on `order['clientOrderId']`. We never set `defaultType`, so the
  venue's default account type governs which market this hits. — **Action**: on bump, confirm
  `fetch_open_orders` still returns spot orders for a configured pair.

- **`v4.5.39`** · `chore(binance): change limit down to 1000 fetchohlcv` ([#27856](https://github.com/ccxt/ccxt/pull/27856)) · **`v4.5.57`** · `fix(binance): reduce fetchOHLCV default limit to 499` ([#28754](https://github.com/ccxt/ccxt/pull/28754))
  → **For us**: we pass `limit` explicitly (`exchange.py:127`), so the *default* change doesn't
  reach us — but the **maximum** does. If our configured indicator lookback exceeds the new cap, we
  silently get fewer candles than `indicators_manager` expects. — **Action**: on bump, assert
  `len(fetch_ohlcv(...))` equals the requested limit.

- **`v4.4.97`** · `fix(binance): fetchMarkets options` ([#26463](https://github.com/ccxt/ccxt/pull/26463))
  → **For us**: same market-structure exposure as the Bybit `#26391` entry. — **Action**: covered by
  the precision check.

## 🔵 OKX

- **`v4.4.98`** · `okx error mapping` ([#26542](https://github.com/ccxt/ccxt/pull/26542))
  → **For us**: same retry-boundary reasoning as Bybit/Binance. — **Action**: same check, against OKX.

- **`v4.5.13`** · `okx parseMarket fixes` ([#27149](https://github.com/ccxt/ccxt/pull/27149)) · **`v4.5.15`** · `fix(okx): empty markets` ([#27216](https://github.com/ccxt/ccxt/pull/27216)) · **`v4.5.57`** · `fix(okx): loadMarkets` ([#28825](https://github.com/ccxt/ccxt/pull/28825))
  → **For us**: three separate `loadMarkets`/`parseMarket` corrections on OKX across the range. We
  depend on that structure for `precision.amount` and `active`. "Empty markets" in particular would
  surface for us as `portfolio_manager.py:77` failing to find a configured symbol. — **Action**:
  on bump, confirm `load_markets()` returns every configured OKX pair.

- **`v4.5.3`** · `fix(okx): default limit for history market candles` ([#26723](https://github.com/ccxt/ccxt/pull/26723)) · **`v4.5.12`** · `fix(okx): fetchohlcv max limits` ([#27013](https://github.com/ccxt/ccxt/pull/27013))
  → **For us**: same OHLCV cap exposure as the Binance entry — OKX's per-request candle ceiling is
  lower than most. — **Action**: same candle-count assertion.

- **`v4.5.8`** · `fix(okx): increase RL coefficient` ([#26973](https://github.com/ccxt/ccxt/pull/26973)) · **`v4.5.23`** · `feat(okx): add apis & update rate limit` ([#27370](https://github.com/ccxt/ccxt/pull/27370))
  → **For us**: we set `enableRateLimit: True` (`exchange.py:205`) and let ccxt pace requests. A
  changed rate-limit coefficient changes our wall-clock time per rebalance cycle, not correctness.
  — **Action**: none; expect timing differences.

- **`v4.5.2`** · `change okx broker code` ([#26689](https://github.com/ccxt/ccxt/pull/26689))
  → **For us**: OKX's broker code rides in the same client-order-id field we tag orders with via
  `quirks.client_order_id_param` (`exchange.py:143-146`, `exchange_quirks.py`). If ccxt prefixes a
  broker code onto `clOrdId`, our `CCB_PREFIX` match in `execution_manager.is_ours` could stop
  recognizing our own orders — which would make us treat live orders as foreign. — **Action**: on
  bump, place a tagged testnet order on OKX and confirm `is_ours()` still matches it.

## 🐍 Python Runtime & Packaging

> This section exists because `packaging/ccbalancer.spec` collects `ccxt` into a **PyInstaller
> one-dir bundle**. ccxt's own dependency graph is therefore our build surface, and nothing here is
> caught by `pytest` — only by building the bundle and running it.

- **`v4.5.65`** · `Remove vendored ecdsa static dependency, use coincurve + cryptography` ([#29131](https://github.com/ccxt/ccxt/pull/29131)) · `Replace ethereum and toolz static dependencies with hand-rolled ABI + EIP-712 encoder` ([#29112](https://github.com/ccxt/ccxt/pull/29112))
  → **For us**: the highest-risk packaging change in the range. `coincurve` and `cryptography` are
  **C-extension** packages; the vendored `ecdsa` they replace was pure Python. PyInstaller must be
  told about their binaries and hidden imports, or the bundle builds cleanly and then fails at
  runtime on a user's machine. Unit tests will not catch this. — **Action**: on bump, rebuild the
  bundle and run `dist/ccbalancer/ccbalancer version` on **all three OSes** via
  `.github/workflows/release.yml` — do not trust a local Windows build alone.

- **`v4.5.65`** · `chore(build): replace python setup.py with root pyproject.toml, pin python dependencies` ([#29093](https://github.com/ccxt/ccxt/pull/29093))
  → **For us**: ccxt now **pins its own dependencies** rather than leaving them open. Our
  `pyproject.toml` pins `ccxt`, `python-dotenv` and `keyring` exactly; if ccxt's new pins conflict
  with ours, `pip install -e '.[dev]'` fails to resolve rather than silently installing something
  odd. — **Action**: on bump, run a clean install into a fresh venv and read the resolver output.

- **`v4.5.65`** · `feat(python): uvloop/winloop/orjson accelerators with safe defaults` ([#29098](https://github.com/ccxt/ccxt/pull/29098)) · `perf(python): uvloop/winloop/orjson accelerators + precision-safe JSON handling` ([#29100](https://github.com/ccxt/ccxt/pull/29100))
  → **For us**: we use **sync** ccxt, so uvloop/winloop are inert. `orjson` is not: it swaps the
  JSON decoder behind every response we parse, which is the same exposure as `parseJson` (#29119)
  above. Both are also new bundle dependencies. — **Action**: same type assertions as #29119; no
  asyncio work needed.

- **`v4.5.64`** · `chore(python): remove vendored sympy, marshmallow_dataclass and typing_inspect` ([#29086](https://github.com/ccxt/ccxt/pull/29086))
  → **For us**: shrinks ccxt's dependency graph, which shrinks our bundle. Strictly good, but it
  changes what PyInstaller collects. — **Action**: covered by the bundle rebuild above.

- **`v4.5.16`** · `feat(python): implement coincurve to improve performance on ecdsa signing` ([#26686](https://github.com/ccxt/ccxt/pull/26686)) · **`v4.5.17`** · `python: downgrade coincurve version to ==20` ([#27247](https://github.com/ccxt/ccxt/pull/27247)) · **`v4.5.19`** · `fix(python): coincurve versions` ([#27280](https://github.com/ccxt/ccxt/pull/27280)) · **`v4.5.57`** · `fix(python): coincurve dependency removal from address generation` ([#28761](https://github.com/ccxt/ccxt/pull/28761))
  → **For us**: `coincurve` was introduced, version-pinned, re-pinned, then partially removed across
  four releases before landing as a hard dependency in `v4.5.65`. That churn is a warning: pin the
  ccxt version, don't track its tip, and expect its C-extension deps to move. — **Action**: none
  beyond the bundle rebuild.

- **`v4.5.21`** · `perf(python): optimization of safe_float, safe_integer, safe_string, safe_value (50% - 70%)` ([#27334](https://github.com/ccxt/ccxt/pull/27334))
  → **For us**: these are the exact parsers producing every field we read. The range also contains
  ~20 further `perf: python <fn>` rewrites (`filter_by` 90%, `parse8601` 190%, `keysort` 80%,
  `precision_from_string` 5x, …). All are advertised as behavior-preserving, but they are a large
  rewrite of the hot path we depend on. — **Action**: none; noted so a post-bump numeric oddity has
  a suspect list.

## 🧾 Breaking Changes That Do NOT Affect Us

All 10 upstream `!:` changes above the pin, with reasons. Nothing in this table needs action.

| Version | Change | PR | Why not ours |
|---|---|---|---|
| `v4.5.65` | `fix(aftermath)!: delist` | [#29125](https://github.com/ccxt/ccxt/pull/29125) | Not in `SUPPORTED_EXCHANGES` |
| `v4.5.65` | `refactor(bitmex)!: fetchOHLCVOpenTimestamp > useOpenTimestamp` | [#29142](https://github.com/ccxt/ccxt/pull/29142) | bitmex not supported; our `fetch_ohlcv` targets bybit/binance/okx |
| `v4.5.64` | `fix(ascendex)!: delist` | [#29079](https://github.com/ccxt/ccxt/pull/29079) | Not supported |
| `v4.5.64` | `fix(coinmetro)!: delist` | [#29069](https://github.com/ccxt/ccxt/pull/29069) | Not supported |
| `v4.5.64` | `fix(novadax)!: delist` | [#29078](https://github.com/ccxt/ccxt/pull/29078) | Not supported |
| `v4.5.59` | `fix(precise)!: strict bools` | [#28854](https://github.com/ccxt/ccxt/pull/28854) | We never call `Precise`; rounding is local `Decimal` in `utils/money.py` |
| `v4.5.58` | `fix(precise)!: stringAdd nullify` | [#28834](https://github.com/ccxt/ccxt/pull/28834) | As above |
| `v4.5.58` | `fix(arkham)!: delist` | [#28000](https://github.com/ccxt/ccxt/pull/28000) | Not supported |
| `v4.5.57` | `fix(oxfun)!: delist` | [#28785](https://github.com/ccxt/ccxt/pull/28785) | Not supported |
| `v4.5.55` | `feat(poloniex)!: fetchCurrencies new v2 endpoint` | [#28618](https://github.com/ccxt/ccxt/pull/28618) | Not supported; we never call `fetch_currencies` |

> ⚠️ **The two `precise!` rows are the softest calls in this file.** `Precise` is ccxt's internal
> string math, used by the base parsers that produce values we *do* read (`ticker.last`,
> `order.average`). We never call it directly, so these are classified as not-ours — but a
> `stringAdd`/strict-bool change could in principle alter a parsed price. Re-examine these first if
> anything numeric looks wrong after a bump.

## 📉 Deliberately Excluded

Of **1,840** upstream bullets above the pin, **327** were dropped mechanically and the rest by
judgment; ~30 entries survived. Categories excluded:

- **Dependency bumps / dependabot, docs, tests, CI** (327, dropped by regex — provably inert for a
  Python consumer).
- **Other-language work**: Go, PHP, Java, C#, .NET, TypeScript `strictNullChecks`, transpiler
  output, and the JS `node-fetch` → undici transport swap.
- **Exchanges outside** `SUPPORTED_EXCHANGES = ('bybit', 'binance', 'okx')` — the bulk of the range.
- **Unified methods we never call**: `fetch_trades`, `fetch_order`, `fetch_positions`, `edit_order`,
  `cancel_all_orders`, `fetch_currencies`, `watch_*`, transfers, withdrawals, funding, borrow/repay,
  leverage, liquidations, earn.
- **ccxt Pro / WebSocket**, ccxt-cli, the docs site, and ccxt's own agent skills.
- **249 bullets with no conventional-commit prefix and no surface keyword** — the acknowledged blind
  spot. Retrieve them with
  `distill.py --releases <json> --include-unclassified` if something seems missing.

Two changes in this range (`#29131`, `#29112`) had *no* commit prefix and named none of our methods,
yet are bundle-breaking. They are in the Python section above because the distiller matches ccxt's
Python dependency names explicitly — not because a keyword caught them. Assume the blind spot is
real.
