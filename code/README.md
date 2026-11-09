# code/ — what runs on the shipped data vs what needs extra downloads

Everything below was verified to run. The repo ships M15→D1 MT5 bars,
cTrader M15 bars, a 2-month real-tick sample, and the published result
CSVs — that is enough for the bar-level measurements and a full
tick-pipeline smoke test.

## Runs on shipped data (clone → pip install → run)

| Script | What it reproduces | Data needed |
|---|---|---|
| `measure_cost_by_timeframe.py` | cost-vs-timeframe table (M5 row prints "missing" unless you add the release asset) | `data/bars/M15,M30,H1,H4,D1` |
| `measure_session_window.py` | hourly volatility profile + 12–16 UTC reversal pocket | `data/bars/M30` |
| `measure_bar_exhaustion.py` | big-bar exhaustion stats | `data/bars/M30` |
| `measure_drop_continuation.py` | multi-candle drop continuation | `data/bars/H1` |
| `measure_volatility_persistence.py` | ATR→range, morning→NY-window predictability | `data/bars/D1` + `M15` |
| `eurusd_research/regime_opinion.py` | the causal regime classifier (library) | any bars dict |
| `tests/test_regime_opinion.py` | causality tests (no data needed) | — |
| `tests/test_bars.py` | smoke test on shipped D1 bars | `data/bars/D1` |

Runtime note: the M15 CSV (~37 MB) takes ~30–60 s to parse; the heaviest
script (`measure_volatility_persistence.py`) takes ~1–2 min total.

## Needs the tick sample (`data/ticks_sample/`, shipped — 2 months, 2025-06/07)

Set `EURUSD_TICKS_BIN=data/ticks_sample` (or pass the absolute path).

| Script | Smoke-test command |
|---|---|
| `scalping/extract_impulse_events.py` | `--anos 2025 --combos 2,60,1.5` → ~4k events in seconds |
| `scalping/simulate_impulse.py` | same combo + `--stop 3 --take 6` → full P&L book |

Verified end-to-end: extraction → simulation → daily P&L all run on the
sample (result consistent with the published negative finding).

## Needs the full tick archive (~1.5 GB, NOT shipped)

Produced by [XScryer/tick-replay](https://github.com/XScryer/tick-replay)
(free cTrader demo account, resumable). Point `EURUSD_TICKS_BIN` at the
output dir (`BID_<year>.npz`/`ASK_<year>.npz`, 2013→2026). These scripts
regenerate every number in `docs/tick-level-scalping.md`:

- `scalping/extract_*.py` — event detectors (impulse, flow, edge, zigzag legs, candle paths)
- `scalping/simulate_*.py` — tick-level SL/TP simulators (impulse, market-making, leg exit)
- `scalping/build_*.py`, `scalping/audit_lookahead_*.py` — event builders + causal audits
- `audit/simulate_pivot_tick.py`, `audit/audit_tick_generic.py` — tick-level trade sims

## Needs the cTrader M1 bars (release asset `data-extra-v1`)

`EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv.gz` → decompress into
`data/ctrader/`. Unlocks the bar-level half of the retail/audit pipeline
(they resample M1→M5/M15 internally):

- `retail/measure_ryan_brown.py`, `retail/measure_box_fade.py`,
  `retail/measure_kristina_fvg.py`
- `audit/measure_pivot_rsi.py`, `audit/audit_events.py`,
  `audit/audit_verify_bugs.py`, `audit/audit_grid_placebos.py`
- `retail/measure_pivot_confluence.py` runs on shipped M15 cTrader bars already.

The tick-level halves (`audit/simulate_pivot_tick.py`,
`audit/audit_tick_generic.py`) additionally need the tick archive and the
event pickles the bar scripts emit.

## Needs MT5 M5 bars (release asset `data-extra-v1`)

`EURUSD_M5_export.csv.gz` + `EURUSD_M5_spread.csv.gz` → decompress into
`data/bars/M5/`. Only used by `measure_cost_by_timeframe.py`'s M5 row.

## Output locations

Scripts write pickles/CSVs under `data/impulso/`, `data/candle/`,
`data/pernadas/` (created automatically; gitignored via `*.pkl`).
