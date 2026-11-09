# What survives — measured facts about EURUSD

These are the results that held up under real costs and real ticks. They are
**facts about the market**, not tradeable strategies — except where noted.

## 1. Cost is the binding constraint at short timeframes

The same reversal rule (bar closes in the top/bottom quarter of its range,
enter against it at the next bar's open, exit at that bar's close) nets out
as — 2021+, 0.20 pip round-trip cost, verified by
`code/measure_cost_by_timeframe.py`:

| Timeframe | Trades | Gross | Net (0.20 pip RT) | Median spread/range |
|---|---:|---:|---:|---:|
| M15 | 80,900 | +0.13 pip | **−0.07 pip** | 1.9% |
| **M30** | 39,715 | +0.26 pip | **+0.06 pip** | 1.3% |
| H1 | 19,617 | +0.29 pip | +0.09 pip | 0.9% |
| H4 | 4,919 | +0.23 pip | +0.03 pip | 0.4% |

The gross edge is roughly constant (~0.13–0.29 pip); what changes is how
much of the bar's range the spread eats. **M30 is the floor where cost
stops swallowing the pattern** (M5 was also measured negative on the full
dataset; its export is not in this repo — see `data/README.md`). At 0.01
lot, position sizing also rules out M1/M5: a 1% stop on a $70–150 account
is 7–15 pips, wider than most M1/M5 noise. Subtracting the *measured* bar
spread instead of the flat 0.20 pip makes every row negative — the edge is
smaller than a realistic all-in cost on most days.

## 2. The 12:00–16:00 UTC window concentrates range and keeps cost low

Median M30 bar range by UTC hour (all history, verified by
`code/measure_session_window.py`): ~7 pips during Asian hours (00–02 UTC),
rising through the European morning to a peak of **18.9 pips at 17:00
UTC**; 13–15 pips through the 12–16 window. Cost as a share of range —
median spread ÷ median range — runs ~9–12% inside the liquid hours versus
17–29% overnight.

Reversing the extreme on M30 inside 12–16 UTC since 2023 (flat 0.20-pip
cost): **+0.35 gross / +0.15 net**, 3.81 trades/day, 3,764 cases — versus
−0.04 net if the *measured* per-bar spread is charged instead. London open
→ New York is where the EURUSD actually moves; whether the pocket survives
a realistic all-in cost is exactly the kind of question this repo exists to
answer honestly (here: marginally, on this cost model).

## 3. A big isolated bar is exhaustion, not continuation

M30 bars ≥14 pips inside the liquid window (07–20 UTC, 2015+, previous bar
smaller — "isolated"), verified by `code/measure_bar_exhaustion.py` (16,572
cases): the next bar is smaller **71.8%** of the time (14–20 pip bars),
**81.0%** (20–30), **91.4%** (>30). The close 3 bars later gives back a
mean **84% / 70% / 57%** of the big bar's range respectively. Direction is
a coin flip (48–49% same direction).

**Known, but not tradeable**: every entry/target/stop variant around this
pattern loses (−0.05 to −1.76 pip per trade). The giveback is real; the
spread eats it.

## 4. A drop spread over several candles continues — the only directional pattern found

Largest close-to-close decline over up to 4 H1 bars inside the liquid
window (07–14 UTC, 2015+), verified by `code/measure_drop_continuation.py`.
Median move over the next 6 hours, and how often the drop retraces >50%
by that close:

| Drop ≥ | Cases | Next-6h move | Retraced >50% |
|---|---:|---:|---:|
| 50 pips | 334 | −1.3 | 18.6% |
| 60 | 178 | −5.4 | 15.2% |
| 70 | 89 | −10.0 | 9.0% |
| 80 | 52 | −15.5 | 3.8% |
| 90 | 34 | −28.6 | 0.0% |

Baseline for any liquid H1 bar: −1.3 pip next-6h, 41.9% retrace. Larger
drops continue further and retrace less — a real monotone dose-response.
**Caveat**: measured as a raw outcome, not as a trade with stop and cost —
as a strategy it has not survived simulation (see
[what-doesnt-work.md](what-doesnt-work.md) §B).

## 5. Volatility is predictable; direction and shape are not

27 years of daily data, verified by `code/measure_volatility_persistence.py`:

- `atr14` → next day's range: Spearman **r = +0.633**, stable across three
  sub-periods (+0.46/+0.60/+0.52). High-vol days have ~2.7× the range of
  low-vol days (54 vs 146 pips median).
- Yesterday's range adds almost nothing on top of the 20-day mean
  (partial r = +0.10). Use the recent average as your sizing ruler, not
  yesterday.
- Intraday (2015+, 3,062 days): the 00:00–12:00 UTC morning range predicts
  the 12:00–16:00 UTC window with **r = +0.430**; yesterday's full-day
  range predicts it even better (**r = +0.585**). Morning-range quintiles:
  afternoon window of 28→49 pips (Q1→Q5).
- Direction: every feature tested → |r| < 0.04. Day shape (trend vs chop):
  nothing predicts it. See [regime-detection.md](regime-detection.md).

## 6. The regime "opinion" classifier — validated on real ticks

A causal classifier that labels each closed M15 bar as *confirmed run*,
*confirmed range*, or *no opinion* (spec in
[regime-detection.md](regime-detection.md)) was used as an entry filter on a
fade-style strategy. On real cTrader ticks across ~11.8 years and 3
parameterizations: **9/9 period cells improved**, total −$12 → +$76 on a $150
account. It is a **damage-reduction filter, not a profit engine** — dead
markets stay negative. At a realistic $70 account with real broker fees the
same setup earns roughly **+$0.5–1.0/year (~+1%/yr)**.

## 7. The one live edge is regime-dependent

The project's only currently-profitable EURUSD strategy (a session-windowed
reversal pattern — details withheld) shows the same signature everywhere in
this repo: **positive in the 2025–26 regime, negative in 2020–24 on real
ticks** (PF 0.73–0.75 vs 1.50–1.90). The regime gate above improves all three
variants in all three periods but does not turn dead regimes profitable.

**The honest summary of 13 years of EURUSD research: sub-5-pip,
seconds-to-minutes horizons are efficient — zero exploitable edge after costs
across every event family tested. Pattern-plus-session edges exist but are
small, regime-dependent, and fragile.**
