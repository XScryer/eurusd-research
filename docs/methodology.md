# Methodology

How every number in this repository was produced — and the rules that decide
what counts as evidence.

## Data

Two datasets, both real market data, both covering different periods:

| Dataset | Coverage | Format | How to get it |
|---|---|---|---|
| **Tick data** (cTrader Open API, Pepperstone feed) | 2013-07-23 → 2026-11, bid+ask | per-year `.npz` files, ~433M ticks | Download with [tick-replay](https://github.com/XScryer/tick-replay) — free demo account, resumable |
| **OHLCV bars + per-bar spread** (MetaTrader 5 export) | 1999 → 2026 | CSV per timeframe (M1→D1) | `data/bars/` in this repo for M15→D1; M1/M5 resample from ticks or request from your broker |

The tick data is the ground truth for anything intraday. Bar data is used for
long-horizon structural measurements (1999 onward) and for quick triage.

**Key detail:** all tick timestamps are UTC. Bars derived from ticks are
computed on the **bid** feed (the MT5 convention). Bars exported from MT5 use
server time — the broker's server clock is UTC+2 (winter) / UTC+3 (summer),
an integer-hour offset that does not affect bar boundaries on hourly+
timeframes, but must be accounted for on M1/M5 session studies.

## Cost model

Every tradeable conclusion is net of realistic costs:

- **Spread**: real bid/ask spread at the moment of the decision (tick-level
  sims) or per-bar average spread (bar-level studies).
- **Commission**: measured from real broker statements —
  Pepperstone Razor: $6.00/lot round-trip ($0.06 per 0.01-lot trade);
  Fusion Markets Zero: €4.50/lot round-trip (~$0.05 per 0.01-lot trade).
- **Swap**: measured overnight financing rates applied at each server
  midnight for positions held past the rollover.

At 0.01 lot, **1 pip = $0.10** and the round-trip cost of a EURUSD trade is
roughly **0.5–0.7 pip**. This number is the single most important constant in
the project: any measured edge below ~0.6 pip per trade cannot pay for itself.

## The causal rule

Every conditioning variable must be computable **using only past data**.
Concretely:

- Windows look backward: `[t−X, t)` — never `[t−X, t+X]` (the symmetric window
  is the single most common lookahead bug; see
  [backtest-traps.md](backtest-traps.md)).
- Higher-timeframe features use the last **closed** bar — never a bar still
  forming (its "close" is the future).
- Zigzag/pivot exits use the **confirmation** timestamp/price, not the
  extreme — a pivot is only known R pips after it happens.
- Any portfolio backtest result is re-verified by a causal audit before it is
  believed.

## Verdict protocol

Nothing is accepted or rejected on a single measurement. The pipeline:

1. **Screening** — cheap bar-level or fixed-horizon measurement. Produces
   hypotheses, never verdicts. Fixed-horizon outcomes ignore the trade path
   and systematically flatter edges.
2. **Tick-level simulation** — SL/TP/time-stop evaluated on every real tick,
   entry at the real ask/bid, spread filter, commission and swap. This is the
   verdict engine for anything intraday.
3. **Out-of-sample check** — a result must hold in at least two different
   market periods (ideally including a period never used to select
   parameters). An edge that only exists in one regime is a regime, not a
   mechanism.
4. **Live validation** — the only final proof. Paper/demo first, always.

**Honest reporting conventions used throughout:** all dollar figures assume
fixed 0.01 lot unless stated; "PF" is profit factor (gross wins / gross
losses); negative results are published with the same detail as positive ones
— the dead ends are the most valuable part of this repository.
