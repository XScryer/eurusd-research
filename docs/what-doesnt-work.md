# What does not work — the dead list

Everything below was measured with real costs and real ticks, then died.
Published so nobody re-tests them — and so the *pattern of failure* is visible.
Numbers are per-trade unless stated; "pips" = EURUSD pips at 0.01 lot
(1 pip = $0.10).

## A. Chart-pattern folklore

| Idea | Verdict | Key numbers |
|---|---|---|
| **Fibonacci levels as barriers** (38.2/50/61.8/78.6) | Dead | Corrections distribute smoothly 20–100% of the leg — no clustering at Fib levels; median correction 60–75% of leg; 61.8% is crossed like any other level |
| **"Magic" corrections = 23.6%/38.2%** | Dead | Only 0.6% of corrections land near 23.6, 4.7% near 38.2; most frequent is 61.8 (7.2%) — and even that is noise |
| **Heavily-traded levels as S/R** | Dead | React 18–19% vs 19–24% for arbitrary levels — *less*, not more; no improvement with longer memory (2mo–2yr) or bigger reactions (10–40 pips) |
| **Level strength grows with touches** | Dead | 22.1% respect on first touch → 18.1% after 6+ touches |
| **Impulse-leg extremes as S/R** | Dead | vs displaced fake levels, same test: −0.1 to +0.4pp across 4 configs — nothing |
| **Smart-money concepts** (liquidity sweep, BOS, FVG, order blocks) | Dead | Sweep: 51.4% close below in 3h vs 48.7% base rate; BOS: 47.4% close higher — *below* base rate; FVG filled 63.5%/6h but touched *less* than arbitrary levels at same distance (−1 to −5pp in all bands) |
| **Consolidation breakout** (Consolidation Zones indicator, mechanical port) | Dead | EURUSD M30 2013–2026: 32.4% of bars in zones, 9,782 zones; breakout with real costs: **−0.139 R** over 4,285 trades (t=−9.6), negative in both halves; 2R target −0.113 R |
| **Raghee Horner wave setup** (3×EMA34 band + re-entry) | Dead | EURUSD 2010–2026: 67,586 trades, **−0.021 R** (t=−5.7), identical in both halves; ETHUSD −0.133 R; win rate 49.4% at 1R = coin flip before cost; 192 variations: best in-sample +0.106 R → −0.001 R out-of-sample |
| **VWAP as magnet / reversal at VWAP touch** | Dead | 24.4% touch rate vs 26.2% for an arbitrary line; reversal trade −0.97 pip over 21,029 trades |
| **Previous day/week high-low as S/R** | Dead | Reject *less* than arbitrary levels (58% vs 63%) |
| **Daily momentum as M30 filter** | Dead (and was lookahead) | Same-day close signal: +7.93 pips t=+11.6 — beautiful and fake (uses the day's own close). Lagged one day: −0.29 pip, t=−0.42, inside null |
| **Chasing expansion** (bar range >2× median) | Dead | Next bar continues same direction 48.0% of time, −0.22 pip |

## B. Session and clock patterns

| Idea | Verdict | Key numbers |
|---|---|---|
| **London open defines the day** (07:00 UTC bar direction → next 4h) | Dead | Holds direction 53.0% (2015–20) / 49.8% (2021–26) — coin flip, unstable |
| **First bar of session → day direction** | Dead | 07:00 UTC: 53.0% at +4h; 13:30 UTC: 49.8% |
| **"London drift" trade** | Dead | 49.1% one period, 52.7% the next — flips sign between regimes |
| **Pockets by UTC hour / weekday** | Dead | All ≤ +0.07 pip — noise (23 pockets tested) |
| **Session windows** (London 07–08:30, NY 13:30–15:00, WM/R fix 15:30–16:30, month-end) | Dead | ≤ +0.13 pip — noise |
| **Abrupt-drop continuation as a trade** (short after ≥50-pip drop in 4 bars) | Dead as trade | The *measurement* is real (see market-facts §4) but as an operation: −0.47 pip (2015–20) vs +0.20 (2021–26) — sign flips between periods |

## C. Volume and microstructure filters

| Idea | Verdict | Key numbers |
|---|---|---|
| **Tick-volume divergence** (new high on falling volume) | Dead | 2h30 return −0.67 pip vs −0.42 with high volume; below 54.0% vs 51.9% — within noise |
| **Tick volume as big-bar filter** | Dead | ≥14-pip bar, high vs low volume: 72.7% vs 74.8% contraction — noise |
| **ADX / trend-strength as filter** | Dead | Separates nothing (also confirmed on US500 sweep) |

## D. The scalping chapter — everything at tick level

An exhaustive causal search over ~13 years of real ticks falsified every
mechanism available to retail scalping. Full detail:
[tick-level-scalping.md](tick-level-scalping.md).

- Impulse-following (momentum): **all 40 parameter combos negative** before cost.
- Impulse-fading: best pocket confined to 2025–26, fails 2019–24.
- Tick-flow (streaks, imbalance), range-edge touches: same wall.
- Composite "agreement" signals: **lookahead artifact** — causal version ≈ 0.
- Market-making inside the spread: catastrophic (−0.25 to −0.32 pip/trip
  gross, 100% losing days).
- Zigzag leg continuation: real structure, dead trade (5 pips of friction
  vs 3.5 capturable).

## E. Wyckoff lab robot — what died inside the one working family

The live strategy family (session-windowed reversal) had its filter space
mined exhaustively. All dead on real ticks:

- Wick minimum 0.45/0.50/0.55/0.60 — all reduce profit vs 0.40
- ATR-based targets — replay said win-win; **real ticks reject**
  (+$70.82 vs +$122.88 baseline)
- Partial exits in 2/3/4-lot ladders — helps 2020–24, hurts 2025–26
- Adaptive targets (EWMA of wins) — marginal
- Intra-trade detectors (exit on pullback after +20p, time-stops) — worse both periods
- Volatility/direction/cost filters, "blind day" filters — all measured, all rejected
- **Final filter battery** (range≥8p, wick combos, triple filter): none beats
  baseline — PF rises but profit falls; the edge is broad and filters remove
  trades that were paying
- **26 TradingView-style indicators as force gauge**: dead — the strategy's
  signal is always *against* the gauge on M15/M30/H1; no strength band or
  timeframe beats baseline

## F. Retail strategies from YouTube

Five popular retail strategies were mechanically tested. All dead — one was
a lookahead artifact worth +$380 that became −$195 when fixed. Full audit:
[retail-strategies.md](retail-strategies.md) and
[case-study-lookahead.md](case-study-lookahead.md).

## The meta-lesson

Across ~13 years and every family tested: **EURUSD at 2–5 pip / seconds–minutes
horizons is efficient**. What was *not* falsified: cross-pair lead-lag
(needs EURGBP/GBPUSD ticks) and the pattern+session edge described in
[market-facts.md](market-facts.md) §7 — which is small, regime-dependent, and
the subject of ongoing work.
