# Tick-level scalping — the exhaustive falsification

> ~13 years of real cTrader ticks (2013-07 → 2026-11, bid+ask, ~433M ticks),
> every event family × every horizon 5s–60min × every causal conditioning
> variable. Account: 0.01 lot, ~$70. Cost ~0.5 pip/trade round-trip.

**Verdict: EURUSD at scalping scale is efficient. All three possible retail
mechanisms — predicting direction, harvesting oscillation (fading), and
making markets — are falsified after costs.**

## Setup of the search

Event detectors run on raw ticks (bid feed for detection, real ask/bid for
fills). Each event logs ~42 features + forward outcomes at 5s/30s/60s/120s/
300s/600s/1800s/3600s horizons. ~2M events for the impulse family alone,
~5.3M for range-edge. Simulations evaluate SL/TP/time-stop tick-by-tick,
one position at a time, both broker fee schedules.

Frequency targets were met (up to 57 events/day at the soft edge of the
grid) — the problem was never trade count, it was edge.

## Family 1 — impulse displacement (K pips in ≤W seconds)

Grid: K∈{2,3,4,5,8} × W∈{10,30,60,120}s × re-arm R∈{1.5,3} — 40 combos,
8 years, ~2M events.

- **Momentum (with the impulse): all 40 combos negative** (~−0.2 to −0.7
  pip at 60–300s, stable across all periods). Continuation does not exist
  on average — impulses slightly revert.
- Where momentum loses: hours 21–23 UTC (rollover + split spread — broken
  microstructure, mandatory filter); spread >2 pips → −5.4 pip outcome;
  pure climax bursts (pct_dir>0.75) are the *worst* pocket (−2.66 — a tick
  storm is exhaustion, not continuation); bursts <5s apart = −1.82.
- **Fade (against the impulse)**: aggregate also negative (−0.26 pip/60s)
  but closer to zero, with exploitable structure — and the fade edge
  *grows with the years* (f_out60 by year: 2019 −0.11 → 2025 +0.02).
- Best fade sim (fade + 1-pip extension entry, SL3 TP2 TS60): PF 1.05 in
  2025–26 but **PF 0.88 over 8 years** — confined to the recent regime,
  fails 2019–24.

## Family 2 — tick flow (streaks + imbalance)

Streak = ≥K consecutive same-direction ticks in ≤W seconds;
imbalance = |dominant-direction fraction| ≥K in a W-tick window.
24 combos, ~1.5M events.

- Momentum: all combos negative.
- Fade direct: best PF 1.00–1.01 in 2025–26 — breakeven gross at best.
- The extension-entry trick that helped impulse-fade **does not transfer**.

## Family 3 — range-edge touches

Price within K pips of the rolling W-tick extreme. 12 combos, ~5.3M events
(most frequent: ~575 events/day).

- Momentum: all negative. Fade direct: PF 0.91–0.99 — no edge.

## Family 4 — composite "agreement" — and the lookahead that faked it

Cross-family agreement looked spectacular: events where impulse-fade
coincided ±60s with flow/edge events showed f_out60 = +0.5 to +0.9 pips
consistently across sub-periods. Simulated portfolios combining the "solo"
and "agreement" legs reported **+$2,254 over 8 years, PF ~1.9, positive in
all 8 years**.

**It was 100% lookahead.** The agreement count used a *symmetric* ±60s
window — events up to 60s in the FUTURE entered the count. Recomputed with
the causal window `[t−60s, t)`: every agreement pocket collapses to |outcome|
≤ 0.15 pip = noise. See
[case-study-lookahead.md](case-study-lookahead.md) for the full mechanism.

One sub-structure survived the audit and is worth recording: on the
*edge-touch* leg the relationship inverts — more agreement with other edge
touches (persistent touching of the same zone) *improves* the fade (+0.4+),
while an isolated touch means breakout. But even that leg fails in
tick-level sim (PF 1.55 gross → negative net on both brokers).

## Family 5 — candle patterns

The candle hypothesis: M1 candles with body ≥5–8 pips closing at ≥70% of
range → fade the close. Real giveback exists (~0.2×body in the last 30% of
the candle) but the candle-decis measurement used bid on both sides — the
real short exits bid and covers ask. Tick-level sim: **−0.4 pip/trade,
PF 0.65–0.73**.

## Family 6 — market-making

Two limit orders inside the spread, optimistic fills (queue position and
latency ignored — generous to the strategy):

- ~1.5–2.0M round-trips/year, win rate ~10%
- **−0.25 to −0.32 pip/trip GROSS**, 100% of days negative in 2024, across
  all three spread fractions tested (0.1/0.3/0.45)
- Cause: adverse selection — your order only fills when price moves against
  you; ~0.8 pip of friction per cycle vs ~0.2–0.5 pip of oscillation

Even with fills more generous than reality permits, it loses. Dead.

## Family 7 — zigzag leg structure (10-tick candles)

Detector: zigzag with reversal R on 10-tick candles. 1.49M pivot triples,
13 years.

**The structure is real and robust**: pullback depth ÷ impulse leg →
probability of higher-high next:

| Retrace r | n | HH% | pivot-to-pivot diff |
|---|---|---|---|
| <0.25 | 16k | **85%** | +1.84 |
| 0.25–0.5 | 196k | 77% | +1.55 |
| 0.5–0.75 | 267k | 67% | +1.15 |
| 0.75–1 | 280k | 59% | +0.77 |
| 1–1.5 | 348k | 45% | +0.04 |
| >1.5 | 386k | **18%** | −2.26 |

Identical across all 3 periods — not a regime artifact.

**But it does not monetize**: entry at pullback-bottom confirmation returns
~R=2 pips; exit at top confirmation ~2 pips; +~1 pip spread/commission ≈
5 pips friction vs ~3.5 pips capturable. Full causal sim (real-time zigzag,
SL at pivot, 449k trades, real bid/ask, 13 years): **−0.51 pip/trade,
PF 0.59, 100% losing days**. All filters (s1≥6, s1≥10, r<0.5): −0.5 to −0.6.

**Recorded trap**: the naive version measuring "exit at pivot timestamp"
showed +1.05 pips/trade — lookahead, because the pivot leg's timestamp is
the candle of the *extreme*, not of the *confirmation* (which happens R pips
later). Any pivot/zigzag backtest must model confirmation, never the extreme.

## The pattern of failure

Every measured pocket shares the same two properties:

1. **Edge is sub-cost**: +0.0 to +0.1 pip gross vs ~0.55–0.65 pip cost.
2. **Regime-confined**: positive only in 2025–26, fails 2019–24 — the same
   regime-dependence that affects the one live strategy.

A portfolio of these legs would be ~breakeven gross − costs = negative.

## What was NOT tested

- **Cross-pair lead-lag** (EURUSD vs EURGBP/GBPUSD ticks) — the only
  remaining causal mechanism, needs tick downloads of the other pairs.
  Download is resumable via tick-replay.
