# Regime detection — what is predictable and what is not

> 13 years of EURUSD tick data, daily + intraday features, combinations, and
> validation on a live strategy's trade log. Code:
> `code/eurusd_research/regime_opinion.py`.

## Verdict in one line

**The SIZE regime (volatility) is predictable. The SHAPE regime
(trend vs chop) and DIRECTION are not — with price data alone.**

## What is predictable

### Daily volatility → tomorrow's range (strongest sensor)

| Feature | r (Spearman) | Q1→Q5 of target | Stability |
|---|---|---|---|
| atr14 → day range | **+0.633** | 54→146 pips (low/high vol days) | +0.46/+0.60/+0.52 across 3 periods |
| atr14 → up/down excursions | +0.21/+0.26 | ~30→~70 pips | stable |
| atr percentile (250d) | +0.25 | 79→117 pips | improves over time |

### Morning range → NY afternoon window (intraday sensor)

Target window: 12:00–16:00 UTC. Features known by noon:

| Feature | → window range | Verified |
|---|---|---|
| morn_rng (00–12h UTC range) | **+0.430** | `measure_volatility_persistence.py` |
| yest_rng (yesterday's full-day range) | **+0.585** | same |
| day-of-week | +0.214 | +0.26/+0.24/+0.18 |

Q1→Q5 of morn_rng: afternoon window of 28→49 pips (3,062 days, 2015+).
**By noon UTC you know whether the afternoon will be big or small** —
useful for sizing and for deciding whether to trade at all.

### Weak but real: unusually moved morning → choppier afternoon

`morn_vol_rel → window efficiency ratio`: r = −0.067 (t = −5.7). Only
non-null SHAPE signal found, and it is weak.

## What is NOT predictable

- **Direction**: all features (momentum, streak, position in range,
  morning/Asia/London direction, gap) → day/window direction: |r| < 0.04.
- **Day shape** (trend-day vs chop-day): no daily feature predicts it
  (|r| ≤ 0.03). 153 tested 2×2 interactions: max |effect| ~0.16 ER,
  unstable across halves.
- **Cross-asset lead-lag**: US500 and gold correlate contemporaneously
  (+0.22/+0.35 on M30) but do **not** lead EURUSD — M5 partial +0.026 ≈
  0.05 pip/bar, below cost.

## The "opinion" classifier (now-casting, not forecasting)

For each **closed** M15 bar, the classifier labels the market state using
only past bars. Canonical implementation: `code/eurusd_research/regime_opinion.py`.

**Recipe** (K=12 bars ≈ 3h window):

1. `net` = close[i] − close[i−K] — net move in pips
2. `path` = Σ|close[j] − close[j−1]| — total distance traveled
3. `er` = |net| / path — efficiency ratio (0 = sawtooth, 1 = straight line)
4. `rng` = max(high) − min(low) over the window

Raw label per bar:
- **RUN** if |net| ≥ 10 pips AND er ≥ 0.45 (direct path)
- **RANGE** if er ≤ 0.25 AND rng ≤ 25 pips (tight sawtooth)
- **No opinion** otherwise

Final opinion: only counts if the **last 6 consecutive bars agree** — a run
declares itself over 1.5h of identical behavior, not one candle.

**Causality guarantee**: `opin[i]` uses only bars with index ≤ i (all
closed). Verified bit-identical against the reference implementation; future
perturbation tests show zero lookahead.

```python
from eurusd_research.regime_opinion import opiniao_regime, ROTULOS
opin = opiniao_regime(bars)   # bars: {"t0","o","h","l","c"} numpy dict
# opin[i]: 2=RUN_UP  3=RUN_DOWN  1=RANGE  -1=NO_OPINION
```

Honest latency: a run is only identifiable **after** it has moved —
inherent lag of ~1–3h (6 bars × 15min). That is the price of not using the
future.

## Why it works as a filter

The project's live strategy is a **fade/reversal**: its rejection-wick entry
keeps running when the market is in a confirmed run. Measured on 354
real-tick trades: trades taken during confirmed runs average **−1.6 to −2.6
pips**; trades outside runs average **+3.6 to +9.1 pips** — a −5 to −11
pip/trade gap, consistent across 6 classifier variants, in BOTH market
periods, and controlling for volatility.

Blocking entries during confirmed runs removes ~2/3 of losing trades.

## Gate results — tick-level replay, causal, backward-only

Three strategy variants × three periods (~11.8 years, $150 account,
fixed-fraction sizing):

| Period | Baseline | + regime gate | Δ |
|---|---|---|---|
| 2015–19 (out-of-sample) | −$60.44 | −$52.30 | +$8.14 |
| 2020–24 | −$59.99 | −$8.69 | +$51.30 |
| 2025–26 | +$108.25 | +$136.90 | +$28.65 |

**9/9 cells improved**, including the never-seen period. Totals:
baseline −$12.18 → gated **+$75.91**. Neighboring parameterizations also
beat baseline → robust plateau, not a lucky peak.

### Reality check at a $70 account

With a $70 account, 0.01 fixed lot (the profit ladder never engages), real
broker fees, full 2015→2026 period:

| Broker | No filter | + gate |
|---|---|---|
| Pepperstone Razor ($6/lot RT) | −$25.55 (min balance $5.55) | +$9.65→**+$2.31** at true $6/lot fee |
| Fusion Zero (€4.50/lot RT ≈ $4.95) | −$32.00 (min $0.84 — nearly bust) | **+$6.26** |

The gate adds +$35–38 over baseline on both brokers — the effect direction
confirms at realistic size. **But absolute profit is marginal: ~+$0.5–1.0/yr
(~+1%/yr).** The per-trade edge is too small to compound on a $70 account.

## Limitations — read before trusting

- **Measures the now, doesn't predict.** Inherent 1–3h detection lag.
- **Damage filter, not profit engine.** In structureless markets it cuts
  losses but creates no edge — those years stay negative.
- **Parameters validated on EURUSD M15.** For other pairs/timeframes,
  rescale `net_min`/`rng_max` to the instrument's typical range and re-run
  the parameter screen.
- **In-sample selection on 2020–26**; the 2015–19 confirmation is real but
  the exact magnitude may be inflated.

## How to apply this to your own strategy

1. Produce your strategy's trade log (any replay engine).
2. For each trade, read `opin[signal_bar]` — the state at signal time.
3. Cross-tabulate: mean P&L of trades in {RUN_UP, RUN_DOWN} vs the rest.
   If run-state trades consistently lose → the gate helps; if not, don't
   force it.
4. If it helps: replicate the blocked trades in a full replay — the gate
   changes position chaining, so **replay is the verdict, not the table**.
5. Parameters: start with the validated set (K=12, pers=6, net=10p, er=0.45);
   scale K and net_min proportionally for larger timeframes.

## What remains untested

- Scheduled news calendar (FOMC/NFP/CPI) as a regime feature.
- Cross-pair lead-lag (EURGBP/GBPUSD ticks).
- Longer volatility regimes (60–120d) and vol term-structure.
- Conversion-rate regime sensor (+20p→TP rolling) with more trade history.
