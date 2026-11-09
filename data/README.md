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
  ticks_sample/                      2 months of real ticks (2025-06/07), smoke tests
  ticks_bin/                         (NOT in git — full archive, see below)
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
  sizes. Both are in the **`data-extra-v1` release** as `.csv.gz` assets
  (~54 MB total): decompress `EURUSD_M5_export.csv.gz` +
  `EURUSD_M5_spread.csv.gz` into `data/bars/M5/` for the M5 row of
  `measure_cost_by_timeframe.py`, or export M5 from your own MT5 (the
  `mt5-backtest-runner` repo shows the CSV format).

## `ticks_sample/` — real ticks for smoke tests

`BID_2025.npz` / `ASK_2025.npz` = ~4M real cTrader ticks covering
2025-06-01 → 2025-08-01 (UTC, `ts` ms + `px`). Enough to run the whole
tick pipeline end-to-end:

```bash
export EURUSD_TICKS_BIN=$PWD/data/ticks_sample
python code/scalping/extract_impulse_events.py --anos 2025 --combos 2,60,1.5
python code/scalping/simulate_impulse.py --K 2 --W 60 --R 1.5 --stop 3 --take 6
```

## `ctrader/` — bars from real ticks

M15 bars aggregated from cTrader tick data (bid), timestamps already UTC,
covering 2020-01→2026-10 in two files. Used by the scalping pipeline and
the retail-strategy screens. The **M1 bars** used by `code/retail/` and
`code/audit/` are in the `data-extra-v1` release
(`EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv.gz` → decompress here).
The full tick archive (~1.5 GB of `BID_<year>.npz`/`ASK_<year>.npz`) is
produced by [XScryer/tick-replay](https://github.com/XScryer/tick-replay)
— point `EURUSD_TICKS_BIN` at the output directory to run the tick-level
code on the full history.

## `results/` — published measurement outputs

See `results/README.md`. These are the trade logs and regime labels behind
the numbers in `docs/regime-detection.md` — small CSVs, safe to audit.

## Environment overrides

| Variable | Default | Purpose |
|---|---|---|
| `EURUSD_DATA_DIR` | `<repo>/data` | relocate the whole data tree |
| `EURUSD_TICKS_BIN` | `<repo>/data/ticks_bin` | tick `.npz` directory |
