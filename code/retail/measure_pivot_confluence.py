# -*- coding: utf-8 -*-
"""M15 screening: Pivot Points + MA200 + bearish engulfing +
StochRSI (YouTube retail confluence).

SHORT: close near R1/P/R2, close < MA200, StochRSI %K > OB, bearish
engulfing. Entry next bar open. SL = signal high + buf. Fixed ~9-pip
TP + runner to S1. Costs ~0.6 pip RT.
"""
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PIP = 0.0001
files = [str(ctrader_bars_dir() / "EURUSD_M15_ctrader_2020-01-01_2024-12-31.csv"),
         str(ctrader_bars_dir() / "EURUSD_M15_ctrader_2025-01-01_2026-10-22.csv")]
df = pd.concat([pd.read_csv(f, parse_dates=["time"]) for f in files])
df = df.set_index("time").sort_index()
o = df.open.to_numpy(); h = df.high.to_numpy(); l = df.low.to_numpy()
c = df.close.to_numpy(); n = len(df)
print(f"M15 barras: {n}  {df.index[0]} -> {df.index[-1]}", flush=True)

# ---- pivots diarios (dia UTC anterior) ----
dd = df.resample("1D").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
dd = dd.dropna()
ph, pl, pc = dd.h.shift(1), dd.l.shift(1), dd.c.shift(1)
piv = (ph + pl + pc) / 3
r1 = 2 * piv - pl; s1 = 2 * piv - ph
r2 = piv + (ph - pl); s2 = piv - (ph - pl)
piv_d = piv.index.normalize()
mapd = {d: i for i, d in enumerate(piv_d)}
# arrays alinhados a cada barra M15: pivots do dia anterior
bar_day = df.index.normalize()
piv_val = np.full(n, np.nan); r1v = np.full(n, np.nan); s1v = np.full(n, np.nan)
r2v = np.full(n, np.nan); s2v = np.full(n, np.nan)
# pivot do dia D usa HLC de D-1: para barras do dia D, usar valores de D-1
prev_map = {d: i - 1 for d in piv_d for i in [mapd[d]] if i > 0}
for i, d in enumerate(bar_day):
    j = mapd.get(d)
    if j is None or j == 0: continue
    k = j - 1  # dia anterior
    piv_val[i] = piv.iloc[k]; r1v[i] = r1.iloc[k]; s1v[i] = s1.iloc[k]
    r2v[i] = r2.iloc[k]; s2v[i] = s2.iloc[k]

# ---- MAs ----
def sma(x, w):
    return pd.Series(x).rolling(w).mean().to_numpy()
ma20, ma50, ma200 = sma(c, 20), sma(c, 50), sma(c, 200)

# ---- StochRSI ----
dc = np.diff(c, prepend=c[0])
gain = np.where(dc > 0, dc, 0); loss = np.where(dc < 0, -dc, 0)
def wilder(x, w):
    a = np.empty(len(x)); a[:w] = np.nan; a[w-1] = x[:w].sum()
    for i in range(w, len(x)): a[i] = a[i-1] - a[i-1]/w + x[i]
    return a
ag, al = wilder(gain, 14), wilder(loss, 14)
rsi = 100 - 100 / (1 + ag / np.where(al == 0, 1e-9, al))
rsi_s = pd.Series(rsi).rolling(14).mean().to_numpy()
# estocastico do RSI suavizado
rmin = pd.Series(rsi_s).rolling(14).min().to_numpy()
rmax = pd.Series(rsi_s).rolling(14).max().to_numpy()
stk = 100 * (rsi_s - rmin) / np.where(rmax - rmin == 0, 1e-9, rmax - rmin)

# ---- bearish engulfing ----
eng = np.zeros(n, bool)
for i in range(1, n):
    if c[i-1] > o[i-1] and c[i] < o[i] and o[i] >= c[i-1] and c[i] <= o[i-1]:
        eng[i] = True

# ---- sinal ----
res = {}
for zona in ["R1", "P", "R2"]:
    for ob in [70, 80]:
        for trend in ["ma200", "ma200+ma50"]:
            sig = np.zeros(n, bool)
            for i in range(210, n - 40):
                if not eng[i]: continue
                if stk[i] < ob: continue
                zz = {"R1": r1v, "P": piv_val, "R2": r2v}[zona][i]
                if np.isnan(zz): continue
                # perto da zona: close dentro de 15 pips abaixo ou high tocou
                if not (l[i] <= zz + 3 * PIP and h[i] >= zz - 15 * PIP): continue
                if trend == "ma200":
                    if not (c[i] < ma200[i]): continue
                else:
                    if not (c[i] < ma200[i] and ma50[i] < ma200[i]): continue
                sig[i] = True
            # simula trades
            tr = []
            i = 210
            while i < n - 2:
                if not sig[i]: i += 1; continue
                ent = o[i + 1]; sl = h[i] + 2 * PIP
                # anda barras seguintes
                tp9 = ent - 9 * PIP; tpS1 = s1v[i]
                res_ = None; j = i + 1
                while j < min(i + 200, n):
                    # SL primeiro (conservador)
                    if h[j] >= sl:
                        res_ = -(sl - ent) / PIP; break  # short: SL acima = perda
                    if l[j] <= tp9:
                        res_ = 9.0; break
                    j += 1
                if res_ is None:
                    res_ = (c[min(j, n-1)] - ent) / PIP
                tr.append((df.index[i], res_, zona, ob, trend))
                i = j + 1
            res[(zona, ob, trend)] = tr

for k, tr in sorted(res.items(), key=lambda x: -len(x[1])):
    if len(tr) < 30: continue
    arr = np.array([t[1] for t in tr])
    wins = (arr > 0).mean()
    print(f"{k} n={len(tr):4d} ({len(tr)/2500:.1f}/sem) win={wins*100:.0f}% "
          f"avg={arr.mean():+.2f} pips gross | liq~{arr.mean()-0.6:+.2f}", flush=True)
