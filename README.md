# eurusd-research

**What works and what doesn't in EURUSD strategy research — measured, not
debated.**

This repository publishes ~13 years of systematic EURUSD research: the
market facts that survived real costs and real ticks, the mechanisms that
were falsified, the backtest traps that produced phantom profits, and the
code to reproduce all of it. It is research, **not financial advice** —
nothing here is a recommendation to trade.

## The one-paragraph summary

EURUSD at 2–5 pip / seconds-to-minutes horizons is efficient: an exhaustive
causal search over real tick data found **zero exploitable edge after
costs** across every event family tested (impulse-following, impulse-fading,
tick-flow, range-edge, market-making, zigzag legs). What *was* found:
volatility is predictable (direction is not), a causal regime classifier
improves a fade-style strategy in 9/9 test cells, and the project's one
live edge is real but small and regime-dependent (~+1%/yr at realistic
account size). Five popular YouTube retail strategies were mechanically
tested — all dead; one was a lookahead artifact worth +$380 that became
−$195 when fixed.

## Repository map

| Path | Contents |
|---|---|
| `docs/methodology.md` | the scientific method: causality rules, cost model, evidence tiers |
| `docs/market-facts.md` | measured facts that survived — volatility persistence, session windows, exhaustion, drop continuation |
| `docs/regime-detection.md` | what is/isn't predictable + the validated regime "opinion" classifier |
| `docs/what-doesnt-work.md` | the dead list — every falsified mechanism, with numbers |
| `docs/tick-level-scalping.md` | the scalping chapter — why sub-5-pip horizons are efficient |
| `docs/squeeze-case.md` | a full research cycle: indicator strategy → OOS rejection → regime rescue |
| `docs/retail-strategies.md` | five YouTube strategies mechanically tested — all dead |
| `docs/case-study-lookahead.md` | the +$380-that-was-a-bug audit, step by step |
| `docs/backtest-traps.md` | 13 traps that inject phantom profit + an audit checklist |
| `code/eurusd_research/` | shared library: bar loaders (MT5→UTC), tick loaders, regime classifier |
| `code/measure_*.py` | reproduce every bar-level number in `docs/market-facts.md` |
| `code/scalping/` | tick-level event extractors and simulators (the falsification toolkit) |
| `code/audit/` | the lookahead case-study pipeline (buggy → fixed → placebos) |
| `code/retail/` | mechanical transcriptions of the five retail strategies |
| `data/bars/` | EURUSD M15→D1 OHLCV + spread (MT5 export format, ~1999→2026) |
| `data/ctrader/` | M15 bars built from real cTrader ticks (UTC, 2020→2026) |
| `data/results/` | published trade logs + regime labels behind the regime-gate numbers |
| `tests/` | causality tests for the regime classifier |

## Quickstart

```bash
pip install -r requirements.txt   # numpy, pandas

# reproduce the bar-level findings (uses data/bars/, included in repo)
python code/measure_cost_by_timeframe.py
python code/measure_session_window.py
python code/measure_bar_exhaustion.py
python code/measure_drop_continuation.py
python code/measure_volatility_persistence.py

# verify the regime classifier is causal
python tests/test_regime_opinion.py
```

The tick-level pipeline (`code/scalping/`, `code/audit/`) needs the real
tick archive — ~1.5 GB of `BID_<year>.npz`/`ASK_<year>.npz` produced by
[XScryer/tick-replay](https://github.com/XScryer/tick-replay). Set
`EURUSD_TICKS_BIN` to that directory and the scripts regenerate the event
pickles documented in `docs/tick-level-scalping.md`.

## Scope and honest limitations

- **The live strategy's recipe is not published.** This repo shares its
  *findings* — regime dependence, gate effect, validation numbers — not
  its entry/exit rules. The published trade logs let you audit the gate's
  effect trade-by-trade without revealing the signal.
- Bar-level scripts reproduce *screening* measurements; trading verdicts
  in this project always came from tick-level SL/TP simulation — the same
  standard is documented in `docs/methodology.md`.
- Several headline numbers come from the tick archive, which is large
  enough to live in releases, not git history — see `data/README.md`.
- Negative results are first-class outputs here: the dead list is longer
  than the findings list, on purpose.

## Companion repositories

- [XScryer/tick-replay](https://github.com/XScryer/tick-replay) — real
  cTrader tick downloader + tick-level replay engine (the data pipeline
  behind everything here)
- [XScryer/pine-check](https://github.com/XScryer/pine-check) — Pine v6
  validator
- [XScryer/mt5-backtest-runner](https://github.com/XScryer/mt5-backtest-runner)
  — command-line MT5 Strategy Tester runner
