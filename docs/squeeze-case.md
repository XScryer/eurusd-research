# Case study: an indicator strategy that failed out-of-sample — and the regime that saved it

A momentum strategy built on three indicators ported literally from a
popular TradingView toolkit (ZLEMA, EMA20, TTM Squeeze momentum), EURUSD
M15, real cTrader ticks 2019→2026. This doc is a compact record of a full
research cycle: build → diagnose → filter → validate → verdict.

## The strategy (mechanical core)

- **Signal**: TTM momentum crosses zero and changes pole; within a 3-bar
  window momentum stays on one side and grows (thresholds ~p55–p75 of its
  own distribution); price closes beyond both ZLEMA and EMA20; ZLEMA within
  0.05% of EMA20.
- **Exit**: momentum returns to zero, or the two averages converge.
- No SL/TP originally, unlimited positions (never actually overlapped).

## Act I — the honest baseline is negative

| Period | Trades | P&L | PF |
|---|---:|---:|---:|
| 2019-10→2024-12 | 228 | **−$43.13** | 0.84 |
| 2025-01→2026-07 | 34 | −$10.57 | 0.60 |

**Giveback autopsy**: average MFE +25.8 pips vs average result −1.4 pips —
each trade travels ~26 pips in favor and gives back ~27 before exiting.
108/228 trades reached +20 pips. The exit was not the fixable bottleneck;
the entry produced no edge.

## Act II — in-sample rescue (all numbers below are in-sample 2019–24)

A long autonomous tuning session produced a stack of filters and exits:

- post-loss "chop pause" + wave-death pause + no-Monday entries
- max extension filter (don't chase already-separated averages)
- ATR14×2.0 stop + TP80 pips
- Result: 136 ops, **+$110.89, PF 2.12** (~+$2.36/month at 0.01 lot)
- With a lot-sizing ladder tuned for return/DD: **+$260.61, PF 2.30**

Every individual filter was weak; together PF 1.5–2.2. Parameter plateaus
(ext 0.08–0.10%, TP 60–80) suggested non-fragility — but everything was
selected on the same data. Classic overfit risk, acknowledged.

## Act III — out-of-sample validation: REJECTED

Same engine, same champion config, 2025-01→2026-07 real ticks:

- Raw book: 34 trades, **−$10.57, PF 0.60**
- Full stack (partials + lot ladder + stops + TP): **−$3.40, PF 0.86**
- Best grid cell: +$5.75 — noise

**The edge did not replicate.** Same pattern as the live strategy's
2020–24 failure: regime-dependent edge. Verdict: do not port to production.

## Act IV — the regime analysis that found the mechanism

Features computed at each signal bar across both periods. Almost every
feature had *opposite* sign between periods — except one plateau:

**"Contained trend": ATR14 < ~14 pips AND Kaufman ER20 ≥ ~0.15–0.20**
(price moving directionally over the last ~5h without being a news spike).

| Filter | A: 2019–24 | B: 2025–26 |
|---|---|---|
| atr<14 & er≥0.15 | +$30.67 / 53 ops | **+$9.90 / 13 ops** |
| atr<14 & er≥0.20 | +$19.21 / 42 | +$10.80 / 9 |
| atr<16 & er≥0.15 | +$43.12 / 60 | +$8.18 / 14 |

With the full exit/sizing stack: **A: +$83.59 PF 2.22** (vs +$260 unfiltered —
costs ~2/3 of in-sample profit but DD drops) · **B: +$19.07 PF 4.19**
(vs −$3.40 unfiltered).

**Market taxonomy that emerged**: the squeeze only pays in contained
trends; in high volatility OR directionless markets it loses in *both*
periods — and that second regime is exactly where the Wyckoff-style
reversal strategy wins (2025–26). The two robots are not overlapping —
they partition the regime space. Monthly P&L correlation between them on
the common 2020–24 window: **0.12** (essentially zero); only 1 same-direction
simultaneous trade out of ~430.

## Honest weaknesses

- Period B has only 13 trades under the filter — PF 4.19 is fragile.
- The cut was discovered scanning period A (in-sample selection); B's
  confirmation is genuinely out-of-sample but minimal.
- Removing the filter costs +$32 of profit that existed in period A.
- Next honest test: integrate the gate into the engine (not just subset
  the book) and extend back to 2013–2019.

## Lessons

1. **A strategy's edge can be real but regime-locked.** In-sample
   +$260/PF 2.30 became OOS −$3.40/PF 0.86 — and regime conditioning is
   what separates "lucky period" from "mechanism".
2. **Giveback autopsy before exit-tweaking**: MFE +26 vs result −1.4 said
   the entry was broken before any stop/target was touched.
3. **Opposite-sign features across periods = regime dependence.** When
   every conditioning variable flips sign between two samples, the honest
   conclusion is "no stable edge", not "pick the better half".
