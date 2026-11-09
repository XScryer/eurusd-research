# -*- coding: utf-8 -*-
"""Zigzag legs on 10-tick candles — EURUSD real bid.

Candles = groups of 10 ticks -> OHLC + t. Zigzag: top confirms when
low <= max_high - R; bottom when high >= min_low + R.

WARNING: t1 is the candle of the EXTREME, not of the confirmation
(which happens R pips later). Backtests using pivot timestamps must
model confirmation delay — see docs/backtest-traps.md.

Output: data/pernadas/pern_R<R>_W<year>.pkl
columns: ano,t0,t1,dir,px0,px1,size_pips,n_candles,hi,lo
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
OUT = str(legs_dir())
PIP = 0.0001
NTICK = 10


def candles_10tick(ts, px):
    n = len(px) // NTICK * NTICK
    p = px[:n].reshape(-1, NTICK)
    t = ts[:n].reshape(-1, NTICK)
    return (t[:, 0], p[:, 0], p[:, -1], p.max(1), p.min(1))


def zigzag(high, low, R):
    """Devolve listas de pernas: (i0,i1,dir,px0,px1)."""
    n = len(high)
    legs = []
    d = 0
    ex_i = -1
    ex_px = 0.0
    leg_i0 = 0
    leg_px0 = (high[0] + low[0]) / 2
    init = False
    for i in range(n):
        h = high[i]; l = low[i]
        if not init:
            # primeiro movimento >= R define direccao
            if h - leg_px0 >= R:
                d = 1; ex_i = i; ex_px = h; init = True
            elif leg_px0 - l >= R:
                d = -1; ex_i = i; ex_px = l; init = True
            continue
        if d == 1:
            if h > ex_px:
                ex_px = h; ex_i = i
            if l <= ex_px - R:
                top_px = ex_px; top_i = ex_i
                legs.append((leg_i0, top_i, 1, leg_px0, top_px))
                d = -1
                leg_i0 = top_i; leg_px0 = top_px
                ex_i = i; ex_px = l
        else:
            if l < ex_px:
                ex_px = l; ex_i = i
            if h >= ex_px + R:
                bot_px = ex_px; bot_i = ex_i
                legs.append((leg_i0, bot_i, -1, leg_px0, bot_px))
                d = 1
                leg_i0 = bot_i; leg_px0 = bot_px
                ex_i = i; ex_px = h
    return legs


def pernadas_ano(ano, R):
    zb = np.load(os.path.join(BIN, f"BID_{ano}.npz"))
    ts, px = zb["ts"], zb["px"]
    zb.close()
    t, o, c, h, l = candles_10tick(ts, px)
    del ts, px
    legs = zigzag(h, l, R * PIP)
    rows = []
    for i0, i1, d, p0, p1 in legs:
        rows.append(dict(ano=ano, t0=int(t[i0]), t1=int(t[i1]), dir=d,
                         px0=p0, px1=p1,
                         size_pips=(p1 - p0) / PIP * d,   # sempre >=0
                         n_candles=i1 - i0,
                         hi=h[i0:i1 + 1].max(), lo=l[i0:i1 + 1].min()))
    del t, o, c, h, l
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--R", type=float, required=True, help="reversao p/ confirmar pivô (pips)")
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    anos = args.anos or sorted(int(f[4:8]) for f in os.listdir(BIN)
                               if f.startswith("BID_") and f.endswith(".npz"))
    partes = []
    for ano in anos:
        fp = os.path.join(OUT, f"pern_R{args.R}_W{ano}.pkl")
        if os.path.exists(fp):
            print(f"{ano}: ja existe, skip"); continue
        df = pernadas_ano(ano, args.R)
        df.to_pickle(fp)
        print(f"{ano}: {len(df)} pernas -> {fp}", flush=True)
        partes.append(df)
    if partes:
        all_df = pd.concat(partes, ignore_index=True)
        all_df.to_pickle(os.path.join(OUT, f"pern_R{args.R}_all.pkl"))
        print("ALL:", len(all_df))


if __name__ == "__main__":
    main()
