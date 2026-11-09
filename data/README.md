# Data

Bar data used by the measurement scripts. Everything here is derived from
publicly available broker price data; no account information is included.

## Layout

```
data/
  bars/<TF>/EURUSD_<TF>_export.csv   OHLCV bars, server time (MT5 export)
  bars/<TF>/EURUSD_<TF>_spread.csv   per-bar spread in price units
  ctrader/EURUSD_M15_ctrader_*.csv   M15 bars built from cTrader ticks, UTC
  results/                           measurement outputs cited by the docs
  ticks_bin/                         (NOT in git — see below)
  impulso/  candle/  pernadas/       (NOT in git — event pickles, see below)
```

## `bars/` — MetaTrader 5 export format

- Columns: `time,open,high,low,close,tick_volume` (export) and
  `time,spread` (spread file; spread = bid−ask at the first tick of the bar,
  in **price units**).
- `time` is **broker server time** — for Pepperstone MT5 that is
  GMT+2 winter / GMT+3 summer (EU DST rules). `eurusd_research.bars`
  converts to UTC automatically.
- Included: M15, M30, H1, H4, D1 (~1999→2026, weekday bars only — Saturday
  bars in the old history are weekend leftovers and are dropped).
- **Not in git**: M1 (~774 MB) and M5 (~164 MB) exceed comfortable repo
  sizes. To reproduce `measure_cost_by_timeframe.py`'s M5 row, export M5
  from your own MT5 (`tools/` in the `mt5-backtest-runner` repo shows the
  CSV format) or resample from tick data — place the files under
  `data/bars/M5/` with the same naming.

## `ctrader/` — bars from real ticks

M15 bars aggregated from cTrader tick data (bid), timestamps already UTC,
covering 2020-01→2026-10 in two files. Used by the scalping pipeline and
the retail-strategy screens. The full tick archive (~1.5 GB of
`BID_<year>.npz`/`ASK_<year>.npz`) is produced by
[XScryer/tick-replay](https://github.com/XScryer/tick-replay) — point
`EURUSD_TICKS_BIN` at the output directory to run the tick-level code.

## `results/` — published measurement outputs

See `results/README.md`. These are the trade logs and regime labels behind
the numbers in `docs/regime-detection.md` — small CSVs, safe to audit.

## Environment overrides

| Variable | Default | Purpose |
|---|---|---|
| `EURUSD_DATA_DIR` | `<repo>/data` | relocate the whole data tree |
| `EURUSD_TICKS_BIN` | `<repo>/data/ticks_bin` | tick `.npz` directory |
