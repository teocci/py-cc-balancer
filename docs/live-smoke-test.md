# Live smoke-test runbook (capped)

A backtest never touches auth, real order placement, real rejections, or partial fills. This runbook
validates that residual risk **once**, with the smallest possible amount of real money, then stands
down. Run it before trusting live execution — it is the last gate a [paper account](paper-account.md)
cannot cover (a paper account rehearses the same command flow against live prices but never touches a
real venue, so it validates the plumbing but not real credentials, real acceptance, or real fills).

Fill booking is handled by the order-status reconciler ([F-6](fixes/F-6.md), shipped in v0.5.1):
placement is recorded write-ahead and real fills are booked only from exchange order status by the
`reconcile` command (auto-run at the start of each `rebalance`). This smoke test is where you confirm
that machinery matches reality on a real venue for the first time.

> **Real funds, real orders.** Everything below places genuine orders on a live account. Keep the cap
> tiny, keep the `STOP` kill-switch within reach, and stop at the first surprise.

## Preconditions

- A funded **spot** account on the exchange, with a **trade-only** API key (no withdrawal scope).
- One liquid pair (e.g. `BTC/USDT`) and knowledge of its exchange **min-notional** (~$5–10 on most
  venues). You will trade at, or just above, that floor.
- Read [`backtest.md`](backtest.md) first — the smoke test confirms what the backtest cannot.
- **Rehearse with a [paper account](paper-account.md) first** (`auth login --paper`): it drives the
  identical `plan → rebalance --execute → orders → reconcile` flow against live prices with no real
  money, so you meet this runbook already knowing the command sequence works.

## 1. Arm the safety rails first

```bash
# Kill-switch: create the STOP file so nothing can place an order until you remove it.
touch ~/.ccbalancer/STOP            # presence blocks order placement; `cancel` is never blocked

# Cap the blast radius: a per-run notional ceiling just above one min-notional order.
ccbalancer config init              # if not yet initialized
#   then set, in ~/.ccbalancer/config.toml under [safety]:
#     max_session_notional_usd = 15      # ~one min-notional order; 0 would mean unlimited
```

`max_session_notional_usd` is the magnitude backstop (the confirm-token proves *intent*, not size);
the `STOP` file is the hard abort. Keep both until the very last step.

## 2. Authenticate and verify (no orders yet)

```bash
ccbalancer auth login               # hidden prompt for key/secret (+ passphrase on OKX)
ccbalancer auth status              # live credential check — must succeed before continuing
ccbalancer status                   # confirms balances/tickers load for the account
```

## 3. Configure one tiny pair

```bash
ccbalancer pair add BTC/USDT --target 50/50 --band 1 --min-notional 6
#   --target is the volatile/stable ratio; a tight band + a floor min-notional keeps the order tiny.
ccbalancer plan --json              # dry-run: shows the decision AND issues the confirm-token
#   note the `confirm_token` in the output — it digests the intended trade set + direction.
```

If `plan` shows no actionable trade, nudge the target or band slightly so exactly one small order is
proposed. Re-run `plan` to get the matching token.

## 4. Execute exactly one order

```bash
# Disarm the kill-switch only now, immediately before the single execute.
rm ~/.ccbalancer/STOP

ccbalancer rebalance --execute --confirm <token-from-plan>
#   --execute + a valid --confirm token are both required; a stale token (intent changed) is rejected.
```

## 5. Verify the fill against reality — this is the point

```bash
ccbalancer orders                   # our orders are flagged; is it resting (open) or filled?
ccbalancer reconcile                # book any real fill from exchange status into the local ledger
```

- Check the exchange UI/API directly: did the order **rest** (`open`, `filled: 0`) or actually fill?
- Compare against the local book: `~/.ccbalancer/accounts/<id>/ledger.jsonl` and `state.json`.

> **Verify the reconciler matched reality.** A maker limit order usually **rests**. Fills are booked
> only from exchange order status ([F-6](fixes/F-6.md)): a resting order should appear in `orders`
> as open with **nothing** in `ledger.jsonl` until it actually fills, then `reconcile` (or the auto-
> reconcile at the next `rebalance`) books exactly the filled delta. Confirm the local book equals the
> exchange after reconciliation — no fabricated fill on submission, no partial double-counted. Any
> mismatch is a stop-and-fix.

## 6. Stand down

```bash
ccbalancer cancel --execute         # cancel any resting order we placed (never blocked by STOP)
touch ~/.ccbalancer/STOP            # re-arm the kill-switch
```

Leave `STOP` in place and `max_session_notional_usd` low until you deliberately begin real operation.
One clean, reconciled fill (local book == exchange) is a pass; anything else — a rejection you didn't
expect, a partial fill, or an F-6 divergence — is a stop-and-fix.

## What this validates (and what it doesn't)

- **Validates:** credentials/auth, a real order reaching the venue, real acceptance/rejection, and
  whether the reconciler-booked local book matches reality after one real fill.
- **Does not validate:** strategy profitability (that's the [backtest](backtest.md)), behavior across
  market regimes, or partial-fill handling at scale. (The execution *plumbing* itself — confirm-token,
  write-ahead, cancel-and-replace, reconcile — is exercised money-free by a [paper account](paper-account.md).)
