# results/ — published measurement outputs

Small CSVs behind the numbers quoted in `docs/`. All are trade logs or
per-bar labels — no strategy recipe is implied by a trade log alone.

## Regime gate validation (`docs/regime-detection.md`)

Trade logs from the tick-level replay engine (real cTrader bid/ask ticks,
0.01-lot-equivalent books). Columns: `dir;ent_t;ext_t;entry;vol;usd;pips;
motivo;noites;sig_t` — direction, entry/exit times, price, volume, USD
PnL, pips, exit reason, nights held, signal time.

| File | What it is |
|---|---|
| `replay_ticks_quilate_<period>.csv` | baseline books, 3 periods (2015-19 / 2020-24 / 2025-26) |
| `replay_ticks_quilate_regK_<period>.csv` | same books **with** the regime gate (K=12, pers=6) |
| `replay_ticks_quilate_70_{fusion,pepperstone}_*.csv` | $70-account realistic-fee baseline |
| `replay_ticks_quilate_regK_70_{fusion,pepperstone}_*.csv` | same, gated |

The strategy that produced these books is the project's live EURUSD
strategy; per the repo's scope, its signal recipe is intentionally not
published — the logs exist so the *gate effect* (baseline vs `regK`) can be
audited trade by trade.

## Regime classifier outputs

| File | What it is |
|---|---|
| `crivo_regime.csv` | regime-gate parameter screen (per K/pers/threshold × period: blocked/allowed trade counts and P&L) |
| `regime_diario.csv` | daily feature table for the regime predictability study (1999→, ~3 MB) |
| `regime_intraday.csv` | intraday (M15-derived) feature table for the same study (~3 MB) |

These are the *feature/label tables* behind `docs/regime-detection.md`'s
predictability claims — inputs to the study, not the classifier output.
`eurusd_research.regime_opinion.opiniao_regime` reproduces the M15-bar
classifier itself; its gate effect is what the `replay_ticks_*` books above
audit.

## Not published

- `data/impulso/`, `data/candle/`, `data/pernadas/` — multi-GB event
  pickles produced by the `code/scalping/` extractors from the tick
  archive. Regenerate with the documented commands once you have ticks.
- MT5 tester `.ini`/`.set` runs and the squeeze-strategy books — the
  squeeze case study (`docs/squeeze-case.md`) reports aggregate numbers;
  the raw books stay internal.
