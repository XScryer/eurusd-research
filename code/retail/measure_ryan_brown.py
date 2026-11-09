# -*- coding: utf-8 -*-
"""M1 screening of the Ryan Brown strategy (impulse+correction).
VECTORIZED. Impulse: W-min window, |displacement|>=D pips, >=70%
candles in direction, final streak >=C candles. Optional ADX(14) M1.
Measures forward momentum/fade returns at +5/+10/+15/+30 min.
"""
import numpy
import sys as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

CSV = str(ctrader_bars_dir() / "EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv")
PIP = 0.0001

df = pd.read_csv(CSV, parse_dates=["time"]).set_index("time").sort_index()
o = df.open.to_numpy(); h = df.high.to_numpy(); l = df.low.to_numpy()
c = df.close.to_numpy(); n = len(df)
print(f"barras: {n}  {df.index[0]} -> {df.index[-1]}", flush=True)

up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
tr = np.maximum(h - l, np.maximum(abs(h - np.roll(c, 1)), abs(l - np.roll(c, 1))))
tr[0] = h[0] - l[0]

def wilder(x, n):
    a = np.empty(len(x)); a[:n] = np.nan
    a[n - 1] = x[:n].sum()
    for i in range(n, len(x)):
        a[i] = a[i - 1] - a[i - 1] / n + x[i]
    return a

atr = wilder(tr, 14)
pdi = 100 * wilder(plus_dm, 14) / atr
mdi = 100 * wilder(minus_dm, 14) / atr
dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
adx = pd.Series(dx).rolling(14).mean().to_numpy()

body_up = (c > o).astype(float); body_dn = (c < o).astype(float)

# racha consecutiva de velas body_up/body_dn terminando em t
run_up = np.zeros(n); run_dn = np.zeros(n)
for i in range(1, n):
    run_up[i] = run_up[i - 1] + 1 if body_up[i] else 0
    run_dn[i] = run_dn[i - 1] + 1 if body_dn[i] else 0

frac_up = pd.Series(body_up).rolling(10).mean().to_numpy()
frac_dn = pd.Series(body_dn).rolling(10).mean().to_numpy()

HOR = [5, 10, 15, 30]

def scan(W, C, D, adx_min):
    disp = (c - np.roll(c, W)) / PIP          # deslocamento W barras atras
    direc = np.zeros(n, dtype=int)
    ok_up = (disp >= D) & (frac_up >= 0.7) & (run_up >= C)
    ok_dn = (disp <= -D) & (frac_dn >= 0.7) & (run_dn >= C)
    direc[ok_up] = 1; direc[ok_dn] = -1
    if adx_min:
        adx_ok = (adx >= adx_min) & (((direc == 1) & (pdi > mdi)) | ((direc == -1) & (mdi > pdi)))
        direc[~adx_ok] = 0
    idx = np.nonzero(direc)[0]
    idx = idx[(idx >= W + 2) & (idx < n - 31)]
    if len(idx) == 0:
        return 0, None
    d = direc[idx]
    base = c[idx]
    out = {}
    for dhor in HOR:
        fut = c[idx + dhor]
        r = (fut - base) / PIP * d
        out[dhor] = r
    return len(idx), out

for W, C in [(7, 3), (10, 3), (10, 4)]:
    for D in [4, 6, 8]:
        for adx_min in [0, 20, 25]:
            cnt, res = scan(W, C, D, adx_min)
            if cnt < 200 or res is None: continue
            tag = f"W{W} C{C} D{D} ADX{adx_min or '-'}"
            line = f"{tag:22s} n={cnt:6d}"
            for dhor in HOR:
                mom = res[dhor].mean(); fad = -mom
                line += f" | +{dhor}m mom{mom:+.2f}/fad{fad:+.2f}"
            print(line, flush=True)
