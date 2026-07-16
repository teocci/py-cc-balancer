# CCXT Upstream Change Impact — Since Our Pin

> **Not a changelog.** This is an *impact assessment*: every entry is a judgment about **our**
> surface, and the large majority of upstream's changes are deliberately absent. For a neutral
> record of what ccxt changed, read <https://github.com/ccxt/ccxt/releases>.
>
> **Purpose**: What changed in ccxt **after** the version we pin — and what each change means for
> *this* project. Read this before bumping the ccxt pin, or when a chunk `01`-`18` seems to
> contradict observed behavior.
> **Pin**: `ccxt==4.5.65` (`pyproject.toml`). Chunks `01`-`18` describe ccxt **at this pin**; this
> file is the delta above it.
> **Covers**: **no releases above the pin** — we are pinned at ccxt's tip. 239 releases scanned,
> 0 above the floor, 0 upstream bullets to assess.
> **Scope**: Only changes touching this project's ccxt surface — the 9 methods, 4 exception classes,
> config keys and structure fields used in `src/ccbalancer/stores/exchange.py`, the three exchanges
> in `SUPPORTED_EXCHANGES`, and the Python wheel we bundle. Everything else is excluded by design;
> the last two sections say exactly what and why.
> **Source**: `GET /repos/ccxt/ccxt/releases`. **Regenerate**: run the `ccxt-changelog-distill` skill.

---

## 🚨 Breaking Changes That Affect Us

**None** — there are no releases above the pin. The pin sits at the latest ccxt release, so the delta
is empty until upstream ships a new version and this digest is regenerated.

## 📌 How this file got here (pin bumped to tip at F-4)

The previous digest tracked the delta from the old pin `4.4.94` up to tip (`v4.4.95` … `v4.5.65`, 72
releases). That gap was **closed** by [F-4](../fixes/F-4.md), which bumped the pin to `4.5.65` to pick
up the OKX preopen-instrument `loadMarkets` fix (`v4.5.57`, PR #28825). At that bump the outgoing
digest's action items were consumed and verified empirically — they did **not** require edits to
chunks `01`-`18`:

- **Default precision (`v4.5.48`) & parseJson types (`v4.5.65`)** — highest-risk entries. Captured
  `market['precision']['amount']`/`['price']` and their Python types for BTC/USDT and ETH/USDT on
  bybit, binance and okx on both `4.4.94` and `4.5.65`: **byte-identical values and identical
  `float` types**. No change reaches `portfolio_manager` rounding or the `Decimal` path in
  `utils/money.py`.
- **`load_markets` guards (`v4.5.65`)** — cold + `reload=True` still refetch OKX markets (4058 both
  ways); the `adjustForTimeDifference` offset still loads during `load_markets`.
- **Error mapping (bybit/binance/okx)** — full `pytest` suite (which mocks the ccxt exception
  hierarchy and asserts our retry boundary in `exchange.py:176-190`) is green on `4.5.65`.
- **Packaging** — `coincurve`, `orjson`, `winloop` and the `aiohttp` accelerators are now hard ccxt
  deps; the bundle rebuild + smoke test under F-4 covers PyInstaller collection.

**Residual verify-on-live item** (needs testnet credentials, not run at bump): OKX broker code
(`v4.5.2`, #26689) rides the `clOrdId` field we tag with `CCB_PREFIX` — place one tagged OKX testnet
order and confirm `execution_manager.is_ours()` still matches it before trading OKX live.

## 🧾 Breaking Changes That Do NOT Affect Us

None above the pin.

## 📉 Deliberately Excluded

Nothing to exclude — 0 upstream bullets above the pin. When the pin next moves below tip, regenerating
this digest repopulates the impact entries, the breaking ledger, and this exclusion accounting from
the release notes.
