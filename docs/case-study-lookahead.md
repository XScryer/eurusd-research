# Case study: auditing a "profitable" strategy — +$380 became −$195

A worked example of why every backtest result in this repository goes
through causal audit before being believed. The strategy: a YouTube
"Pivot + EMA12 + RSI" system on EURUSD M5/M15. Initial mechanical port
reported **+2.72 pips/trade, +$380 net over ~6 years** — too good, so it was
audited line by line.

**Verdict: the profit was 100% lookahead bias. Corrected, the strategy loses
~2 pips/trade and −$195 net. None of ~30 parameter variants is profitable.**

## Bug 1 — the fatal one: lookahead in the H4 trend filter

```python
j = h4_times.searchsorted(t, side="right") - 1   # the H4 bar CONTAINING t
if h4.c.iloc[j] > h4e.iloc[j]: ...               # but h4.c.iloc[j] is the
                                                 # FINAL close of that bar
```

`h4` was resampled over the whole dataset: `h4.c.iloc[j]` is the last M1
close of the window `[T, T+4h)` — i.e., the close of an H4 bar **still
forming**. `h4e.iloc[j]` is the EMA20 computed up to that same future close.

**Proof**: in **97.9%** of M5 bars the H4 bar used had not yet closed at
signal time; the future close used was on average **115 minutes ahead**
(max ~4h).

**Mechanism**: the filter only allows longs when the in-progress H4 bar
*will close* above its EMA20 — an oracle correlated with the trade's own
outcome (median trade duration ~3.4h, the H4 close lands inside it).

**Measured impact** (same bars, only the filter changes):

| Version | n | avg pips | PF | t |
|---|---|---|---|---|
| H4 buggy (original) | 1,251 | **+2.71** | 1.35 | +4.4 |
| H4 fixed (last *closed* H4) | 1,355 | **−2.05** | 0.80 | −3.5 |

The lookahead was worth **~4.8 pips/trade of phantom profit**.

## Bug 2 — daily pivots off-by-one

`pv[i]` is already "day i's pivot" (computed from day i−1's HLC); the loop
used `pv.iloc[j-1]` = pivot from the HLC of **two trading days back**. Worse:
the day list included partial Sunday sessions (~2–3h), so weekday pivots
were being computed from a handful of hours — effectively arbitrary levels.
Not lookahead, but the tested strategy wasn't the described one.

## The corrected strategy loses everywhere

All causal interpretations of the H4 filter lose at bar level
(−1.7 to −2.1 pips/trade, t ≈ −4) and at tick level:

- **2,292 trades, win 37.7%, gross PF 0.96, −0.35 pips/trade**
- Net: **−$195 (Fusion) / −$218 (Pepperstone)** over ~6.3 years
- Negative in 4 of 7 years

**Sensitivity — 30 parameter variants, all negative.** This is not a
parameter-peak problem; there is no edge anywhere in the neighborhood:
zone width 8→20 pips, TP ratio 1.3→2.5, risk bands, pivot-distance filters,
RSI bands — every combination loses ~$0.9+/trade after costs.

## Placebos — how we know it was the bug, not bad luck

| Placebo | avg pips | Reading |
|---|---|---|
| Fixed version, direction **inverted** | −1.33 | also loses → no directional edge |
| Fixed version, **random direction** (same bars/regime) | −1.15 | regime+costs alone give ~−1 pip |
| Fixed version, entry **+1 bar late** | −1.82 | no decay because there was no edge |
| **Buggy**, direction inverted | **−7.53** (PF 0.52, t=−8.8) | the buggy "edge" is real directional information — *injected by the lookahead* |
| Buggy, entry +3 bars late | **+2.86** (t=+4.2) | the lookahead lives in the H4 filter, not the entry — delaying entry doesn't remove it |

The inverted-placebo result is the tell: if the buggy version's profit were
real skill, flipping direction should also profit (or at least not collapse
to −7.5). Instead it collapses — because the filter was literally telling
the future.

## Minor bugs found during the audit (noted for completeness)

- Exit-at-close measurement read 2 bars past the verified window (micro-
  lookahead in the *meter*, not the events or the tick sim).
- The tick sim only scanned ticks within the entry year — a position opened
  at year-end got cut at the last December tick (≤1–2 trades/year, verified
  negligible).
- Entry-tick selection could pick a tick ~1 interval before `t_ent`
  (sub-second, negligible).

## Lessons that generalize

1. **`resample()` + "last bar ≤ t" = classic lookahead** when the bar is
   still forming. Any higher-timeframe feature must check bar *close time*,
   not just bar start.
2. **Too-good results demand audit.** +2.7 pips/trade on EURUSD M5 is not a
   strategy, it's a bug report.
3. **Placebos are cheap and decisive.** Inverted direction + random
   direction + delayed entry separate "edge" from "oracle" in an afternoon.
4. **A profitable backtest is a hypothesis, not a finding.** This strategy
   looked robust (positive every year, top-10 trades only 15% of profit) —
   all fabricated.
