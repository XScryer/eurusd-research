# -*- coding: utf-8 -*-
"""Tradeable events from the zigzag leg structure (R=2 pips).

Setup: impulse leg i -> pullback i+1 -> confirmation i+2.
Entry = first real tick reaching pullback_pivot + dir*R*pips within
WIN_S seconds of the pivot. sim_impulso schema + imp_size,s1,T1,B0.
"""
import os
import sys
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
PERN = str(legs_dir() / "pern_R2.0_all.pkl")
OUT = str(impulso_dir())
PIP = 0.0001
R_PIPS = 2.0
WIN_S = 600

r_min = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
r_max = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
anos_req = [int(a) for a in sys.argv[3:]] or None

df = pd.read_pickle(PERN).sort_values(["ano", "t0"]).reset_index(drop=True)
d = df["dir"].to_numpy(); sz = df.size_pips.to_numpy()
px0 = df.px0.to_numpy(); px1 = df.px1.to_numpy()
ano = df.ano.to_numpy(); t0 = df.t0.to_numpy(); t1 = df.t1.to_numpy()
anos_arr = ano

os.makedirs(OUT, exist_ok=True)
fp = os.path.join(OUT, f"evpern_r{r_min}-{r_max}.pkl")
all_rows = []
for yr in sorted(set(anos_arr.tolist())):
    if anos_req and yr not in anos_req:
        continue
    # triplas do ano
    evs = []
    idx_ano = np.nonzero(anos_arr == yr)[0]
    for i in idx_ano:
        if i + 2 >= len(df) or anos_arr[i + 1] != yr or anos_arr[i + 2] != yr:
            continue
        if d[i] == 1 and d[i + 1] == -1 and d[i + 2] == 1:
            tr_dir = 1
        elif d[i] == -1 and d[i + 1] == 1 and d[i + 2] == -1:
            tr_dir = -1
        else:
            continue
        s1, s2 = sz[i], sz[i + 1]
        if s1 <= 0:
            continue
        r = s2 / s1
        if not (r_min <= r < r_max):
            continue
        piv = px1[i + 1]                     # extremo do recuo (fundo p/ compra)
        trig = piv + tr_dir * R_PIPS * PIP   # confirmacao = +2 pips a favor
        evs.append((i, tr_dir, r, s1, px1[i], px0[i], int(t1[i + 1]), trig,
                    piv, px1[i + 2], int(t1[i + 2])))
    if not evs:
        continue

    zb = np.load(os.path.join(BIN, f"BID_{yr}.npz"))
    za = np.load(os.path.join(BIN, f"ASK_{yr}.npz"))
    ts_b, px_b, ts_a, px_a = zb["ts"], zb["px"], za["ts"], za["px"]

    rows = []
    n_skip = 0
    for i, tr_dir, r, s1, T1, B0, tpiv, trig, piv, T2, tT2 in evs:
        t_ini = tpiv
        t_fim = tpiv + WIN_S * 1000
        j0 = int(np.searchsorted(ts_b, t_ini, side="left"))
        j1 = int(np.searchsorted(ts_b, t_fim, side="left"))
        if j1 <= j0 or j0 >= len(ts_b):
            n_skip += 1; continue
        seg = px_b[j0:j1]
        if tr_dir == 1:
            hit = np.nonzero(seg >= trig)[0]
        else:
            hit = np.nonzero(seg <= trig)[0]
        if len(hit) == 0:
            n_skip += 1; continue
        j = j0 + int(hit[0])
        te = int(ts_b[j]); be = float(px_b[j])
        ja = int(np.searchsorted(ts_a, te, side="left"))
        cand = [x for x in (ja - 1, ja, ja + 1) if 0 <= x < len(ts_a)]
        if not cand:
            n_skip += 1; continue
        jb = min(cand, key=lambda x: abs(int(ts_a[x]) - te))
        ae = float(px_a[jb]); spr = ae - be
        if spr <= 0 or spr > 0.002:
            n_skip += 1; continue
        th = pd.Timestamp(te, unit="ms", tz="UTC")
        rows.append(dict(ano=yr, K=0, W=0, R=0, t=te, dir=tr_dir,
                         bid_e=be, ask_e=ae, spread_e=spr,
                         ok_a=True, ok_b=True,
                         out5=np.nan, out15=np.nan, out30=np.nan,
                         out60=np.nan, out120=np.nan, out300=np.nan,
                         imp_size=r, ticks_win=0, tick_rate=0,
                         pct_dir=1.0, span_s=0, rng300=np.nan,
                         dist_hi=np.nan, dist_lo=np.nan, gap_b=0.0,
                         mes=th.month, dia=th.day, hora=th.hour,
                         dow=th.day_of_week, dt_prev=np.nan,
                         dir_prev=0, s1=s1, T1=T1, B0=B0,
                         piv=piv, T2=T2, tT2=tT2))
    zb.close(); za.close()
    if rows:
        all_rows.extend(rows)
        print(f"{yr}: {len(rows)} eventos ({n_skip} skip)", flush=True)

if all_rows:
    out = pd.DataFrame(all_rows)
    if os.path.exists(fp):
        out = pd.concat([pd.read_pickle(fp), out], ignore_index=True)
    out.to_pickle(fp)
    print("GRAVADO", fp, len(out), "eventos")
