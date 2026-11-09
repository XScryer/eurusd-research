# Backtest traps — the catalog

Every trap below produced a *believed* result that dissolved under audit.
Ordered roughly by how much phantom profit each one can inject.

## 1. Lookahead via symmetric windows

Counting "how many same-direction events within ±60s" uses the future.
In real time only `[t−60s, t)` exists. The causal recompute collapsed every
"agreement" pocket to ≤0.15 pip — a reported **+$2,254 portfolio was 100%
artifact**. Any conditioning count must look strictly backward.

## 2. Lookahead via resampled higher-timeframe bars

`df.resample("4h")` then "last bar ≤ t" returns the bar **still forming** —
its `close` is the final close hours in the future. Produced +2.71
pips/trade that became −2.05 when fixed (~4.8 pips/trade of phantom edge).
**Rule**: HTF features need the last *closed* bar — check close time, not
just start time.

## 3. Pivot/zigzag timestamp ≠ pivot price time

A zigzag pivot is only confirmed R pips after the extreme. Using the
extreme's timestamp for exit (or the pivot's raw price for entry) is
lookahead: showed **+1.05 pips/trade vs real −0.51**. Model the
confirmation bar/price, never the extreme.

## 4. Fixed-horizon outcome ≠ trade

"Price was +X pips 5 minutes later" ignores the path: the stop may have
been hit first. A fade pocket with +1.6 pip fixed-horizon outcome lost
money in SL/TP sim (−$66 to −$118). Fixed-horizon is for *screening*;
verdicts require tick-level SL/TP simulation.

## 5. Candle-decis measured on bid only

Giveback measured open→decis→close on bid ignores that a real short exits
bid and covers ask — the spread eats the measured edge (−0.4 pip/trade
real vs +0.3 apparent). Any measurement of a *tradeable* outcome must use
the correct side of the book for each leg.

## 6. `Model=real ticks` silently gives simulated ticks (MetaTrader 5)

In MT5 `.ini` files, `Model=real ticks` is an **invalid string** — the
tester falls back to "every tick" *simulated* without warning. Real ticks
require `Model=4`. Confirm in the tester log: `generating ticks based on
real ticks` = real; `every tick generating` = simulated. This invalidated
every pre-audit "real ticks" result in the project until re-run — including
numbers that survived (the live strategy's edge held on re-validation).

## 7. `TimeGMT()` inside the tester returns server time

Measured over 116 consecutive hours: `TimeGMT()`, `TimeCurrent()`,
`TimeTradeServer()` and `TimeLocal()` return the **same** value — the
server clock, not UTC. A "14–19 UTC" session filter was actually
11–16 UTC. Half of a reported edge was this timezone swap.

## 8. Missing end-of-day close

An EA without an explicit EOD close holds positions overnight, through
weekends and gaps, exiting only on SL/TP. Same setup, same window: adding
the EOD close cut profit from +94.92 to +40.68 — **half the "edge" was
unmanaged overnight risk**.

## 9. Concentration arithmetic artifacts

Calculating concentration with gross profit on top and net below produced
"top-3 trades = 127% of profit" nonsense. Always consistent numerator and
denominator.

## 10. Selection on the recent period

Pockets positive in 2024–26 that were ~0 or negative in 2019–23 are regime,
not mechanism. Rule adopted: an edge must show signal in **all** testable
periods (ideally including pre-2019 fragments).

## 11. Feed sensitivity

The same engine diverges ~30% between data feeds (MT5 ticks vs cTrader
ticks). MT5 real ticks = gold standard where `.tkc` files exist; otherwise
the cTrader replay is the oracle — and it was validated trade-by-trade
against MT5 (88/88 and 71/71 trades matched on direction and exit reason).
Bar-level (M1 OHLC) engines systematically **overvalue** larger targets —
never use them for verdicts.

## 12. Rejected orders counted as trades

A rejected order burned the day's trade quota and polluted stats. Count
only filled positions.

## 13. Survivorship in "profitable" retail content

YouTube strategy summaries omit the losing trades, the discretionary
filters, and the account size. Five mechanically-transcribed strategies:
all negative; one was a lookahead artifact. Treat unsourced performance
claims as hypotheses requiring full audit — see
[retail-strategies.md](retail-strategies.md).

## The audit checklist (run before believing any positive result)

- [ ] Every conditioning variable computable with `[t−X, t)` only?
- [ ] HTF bars confirmed *closed* before use?
- [ ] Pivots/exits modeled at confirmation, not extreme?
- [ ] Verdict from tick-level SL/TP sim, not fixed-horizon outcome?
- [ ] Correct bid/ask side for every leg of the trade?
- [ ] Tick model confirmed real (`Model=4` / real tick log line)?
- [ ] Session times verified against actual UTC, not server clock?
- [ ] Positions closed per the strategy's own rules (EOD, max hold)?
- [ ] Result holds in ≥2 disjoint periods, one never used for selection?
- [ ] Placebo runs: inverted direction, random direction, delayed entry —
      does the "edge" survive or collapse like a real one should/shouldn't?
