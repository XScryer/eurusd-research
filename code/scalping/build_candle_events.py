# -*- coding: utf-8 -*-
"""Candle-fade events from pre-measured M1/M5 candles.

Signal (causal): at decile-8 entry (~48s M1 / ~240s M5), body formed
up to decile 7 has |.|>=TH pips -> trade AGAINST it.
Entry: first real BID tick inside decile 8; ask_e = nearest ASK.
SL/TP/tstop simulated tick by tick by simulate_impulse.py.

Usage: python build_candle_events.py [M1|M5] [TH_pips]
"""
import os
import sys
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
CND = str(candles_dir())
OUT = str(impulso_dir())
PIP = 0.0001

TF = sys.argv[1] if len(sys.argv) > 1 else "M1"
TH = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
DUR = 60_000 if TF == "M1" else 300_000
DEC7 = int(DUR * 0.7)   # inicio do decil 7
DEC8 = int(DUR * 0.8)   # inicio do decil 8 = janela de entrada

rows = []
for ano in range(2019, 2027):
    cf = os.path.join(CND, f"{TF}_{ano}.pkl")
    bf = os.path.join(BIN, f"BID_{ano}.npz")
    af = os.path.join(BIN, f"ASK_{ano}.npz")
    if not (os.path.exists(cf) and os.path.exists(bf) and os.path.exists(af)):
        continue
    c = pd.read_pickle(cf)
    c["body7"] = (c["p7"] - c["open"]) / PIP
    sel = c[c["body7"].abs() >= TH]
    if len(sel) == 0:
        continue
    zb = np.load(bf); za = np.load(af)
    ts_b, px_b = zb["ts"], zb["px"]
    ts_a, px_a = za["ts"], za["px"]
    for t0, body7, o, h, l, cl in zip(sel["t"], sel["body7"], sel["open"],
                                    sel["high"], sel["low"], sel["close"]):
        t0 = int(t0)
        e_lo, e_hi = t0 + DEC8, t0 + DEC8 + int(DUR * 0.1)  # janela do decil 8
        i0 = int(np.searchsorted(ts_b, e_lo, side="left"))
        i1 = int(np.searchsorted(ts_b, e_hi, side="left"))
        if i0 >= len(ts_b) or i1 <= i0:
            continue
        # primeiro tick do decil 8 = entrada
        te = int(ts_b[i0]); be = float(px_b[i0])
        # ask mais proximo (searchsorted)
        ja = int(np.searchsorted(ts_a, te, side="left"))
        cand = [ja - 1, ja, ja + 1]
        cand = [j for j in cand if 0 <= j < len(ts_a)]
        jbest = min(cand, key=lambda j: abs(int(ts_a[j]) - te))
        ae = float(px_a[jbest])
        spr = ae - be
        if spr <= 0 or spr > 0.0015:
            continue
        d = -1 if body7 > 0 else 1
        ts_h = pd.Timestamp(te, unit="ms", tz="UTC")
        rows.append(dict(ano=ano, K=0, W=0, R=0, t=te, dir=d,
                         bid_e=be, ask_e=ae, spread_e=spr,
                         ok_a=True, ok_b=True,
                         out5=np.nan, out15=np.nan, out30=np.nan,
                         out60=np.nan, out120=np.nan, out300=np.nan,
                         imp_size=abs(body7), ticks_win=0, tick_rate=0,
                         pct_dir=1.0, span_s=0, rng300=np.nan,
                         dist_hi=np.nan, dist_lo=np.nan, gap_b=0.0,
                         mes=ts_h.month, dia=ts_h.day, hora=ts_h.hour,
                         dow=ts_h.dayofweek, dt_prev=np.nan,
                         dir_prev=0))
    print(f"{TF} {ano}: {len(sel)} candles>=TH, acumulado {len(rows)}", flush=True)
    del c, zb, za

df = pd.DataFrame(rows)
fp = os.path.join(OUT, f"evcandle_{TF}_K0_W0_R0.pkl")
df.to_pickle(fp)
print("GRAVADO", fp, len(df), "eventos")
