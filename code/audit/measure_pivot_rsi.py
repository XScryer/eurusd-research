# -*- coding: utf-8 -*-
"""YouTube strategy M5: pivots + EMA12 cross + RSI + TP 1.7x risk.

THIS IS THE BUGGY VERSION — kept as the case-study artifact. The H4
trend filter uses the in-progress H4 bar FINAL close (~115 min future)
and pivots are off by one day — see docs/case-study-lookahead.md and
audit_verify_bugs.py / audit_events.py for the corrected causal version.

Long: near support (S1/P/S2), candle crosses EMA12 up, H4 bullish
(close H4 > EMA20 H4), pivot distance in [15,100] pips.
SL = nearest pivot below -2 pips. TP = entry + 1.7*(entry-SL).
Short: mirror. RSI(14) M5: long RSI<55, short RSI>45.
"""
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PIP = 0.0001
f1 = str(ctrader_bars_dir() / "EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv")
m1 = pd.read_csv(f1, parse_dates=["time"]).set_index("time").sort_index()
m5 = m1.resample("5min").agg(o=("open","first"), h=("high","max"),
                             l=("low","min"), c=("close","last")).dropna()
# H4 do mesmo M1
h4 = m1.resample("4h").agg(c=("close","last")).dropna()
h4e = h4.c.ewm(span=20, adjust=False).mean()

o5 = m5.o.to_numpy(); h5 = m5.h.to_numpy(); l5 = m5.l.to_numpy()
c5 = m5.c.to_numpy(); n5 = len(m5)
ema12 = pd.Series(c5).ewm(span=12, adjust=False).mean().to_numpy()
# RSI14
dc = np.diff(c5, prepend=c5[0])
g = np.where(dc > 0, dc, 0.); ls = np.where(dc < 0, -dc, 0.)
def wild(x, w):
    a = np.empty(len(x)); a[:w] = np.nan; a[w-1] = x[:w].sum()
    for i in range(w, len(x)): a[i] = a[i-1] - a[i-1]/w + x[i]
    return a
ag, al = wild(g, 14), wild(ls, 14)
rsi = 100 - 100 / (1 + ag / np.where(al == 0, 1e-9, al))

# pivots diarios (de M5)
dd = m5.resample("1D").agg(h=("h","max"), l=("l","min"), c=("c","last")).dropna()
ph, pl, pc = dd.h.shift(1), dd.l.shift(1), dd.c.shift(1)
pv = (ph + pl + pc) / 3
r1 = 2 * pv - pl; s1 = 2 * pv - ph; r2 = pv + (ph - pl); s2 = pv - (ph - pl)
days = dd.index.normalize()
# arrays por barra M5
pivv = np.full(n5, np.nan); r1v = np.full(n5, np.nan); s1v = np.full(n5, np.nan)
s2v = np.full(n5, np.nan); r2v = np.full(n5, np.nan)
dmap = {d: i for i, d in enumerate(days)}
for i, t in enumerate(m5.index):
    j = dmap.get(t.normalize())
    if j is None or j == 0: continue
    k = j - 1
    pivv[i] = pv.iloc[k]; r1v[i] = r1.iloc[k]; s1v[i] = s1.iloc[k]
    r2v[i] = r2.iloc[k]; s2v[i] = s2.iloc[k]

h4_times = h4.index
h4_up = np.zeros(n5, bool); h4_dn = np.zeros(n5, bool)
for i, t in enumerate(m5.index):
    j = h4_times.searchsorted(t, side="right") - 1
    if j < 25: continue
    if h4.c.iloc[j] > h4e.iloc[j]: h4_up[i] = True
    else: h4_dn[i] = True

trades = []
i = 300
while i < n5 - 60:
    fired = False
    for d in (1, -1):
        if d == 1 and not (h4_up[i] and c5[i-1] <= ema12[i-1] and c5[i] > ema12[i]): continue
        if d == -1 and not (h4_dn[i] and c5[i-1] >= ema12[i-1] and c5[i] < ema12[i]): continue
        # RSI filtro
        if d == 1 and not (30 < rsi[i] < 55): continue
        if d == -1 and not (45 < rsi[i] < 70): continue
        # zona: long perto de suporte, short perto de resistencia
        if d == 1:
            cands = [("S1", s1v[i]), ("P", pivv[i]), ("S2", s2v[i])]
            near = [nm for nm, z in cands if not np.isnan(z) and abs(c5[i] - z) <= 12 * PIP]
            if not near: continue
            # SL = pivô mais proximo abaixo -2
            below = [z for nm, z in cands if not np.isnan(z) and z < c5[i] - 2 * PIP]
            if not below: continue
            sl = max(below) - 2 * PIP
        else:
            cands = [("R1", r1v[i]), ("P", pivv[i]), ("R2", r2v[i])]
            near = [nm for nm, z in cands if not np.isnan(z) and abs(c5[i] - z) <= 12 * PIP]
            if not near: continue
            above = [z for nm, z in cands if not np.isnan(z) and z > c5[i] + 2 * PIP]
            if not above: continue
            sl = min(above) + 2 * PIP
        risk = abs(c5[i] - sl)
        if risk < 3 * PIP or risk > 40 * PIP: continue
        # filtro distancia entre pivôs adjacentes
        if not np.isnan(pivv[i]) and not np.isnan(r1v[i]) and not np.isnan(s1v[i]):
            dists = [abs(r1v[i]-pivv[i])/PIP, abs(pivv[i]-s1v[i])/PIP]
            if min(dists) < 15 or max(dists) > 100: continue
        ent = c5[i]  # entrada no close do cruzamento
        tp = ent + d * 1.7 * risk
        j = i + 1; motivo = "fim"
        px = c5[min(j + 200, n5 - 1)]
        while j < min(i + 200, n5):
            if d == 1:
                if l5[j] <= sl: motivo = "sl"; px = min(sl, l5[j]); break
                if h5[j] >= tp: motivo = "tp"; px = tp; break
            else:
                if h5[j] >= sl: motivo = "sl"; px = max(sl, h5[j]); break
                if l5[j] <= tp: motivo = "tp"; px = tp; break
            j += 1
        pips = (px - ent) / PIP * d
        trades.append({"t": m5.index[i], "t_ent": m5.index[min(i + 1, n5 - 1)],
                       "dir": d, "pips": pips, "motivo": motivo,
                       "sl": sl, "ent_bar": ent, "risk": risk / PIP})
        i = j + 3
        fired = True
        break
    if not fired:
        i += 1

df_t = pd.DataFrame(trades)
if len(df_t):
    dias = (m5.index[-1] - m5.index[0]).days
    gp = df_t.pips[df_t.pips > 0].sum(); gl = -df_t.pips[df_t.pips <= 0].sum()
    print(f"\n=== Pivot+EMA12+RSI M5 ===")
    print(f"trades={len(df_t)} (~{len(df_t)/(dias/7):.1f}/sem) | "
          f"win={(df_t.pips>0).mean()*100:.0f}% | PF_g={gp/max(gl,1e-9):.2f} | "
          f"avg={df_t.pips.mean():+.2f} | risk_medio={df_t.risk.mean():.1f} pips")
    print(f"liquido~{df_t.pips.mean()-0.6:+.2f} pips/tr = ${( (df_t.pips.mean()-0.6)*0.10*len(df_t)):+.2f} total")
    print(df_t.groupby(df_t.t.dt.year).pips.agg(['count','mean']).round(2).to_string())
    df_t.to_pickle(str(impulso_dir() / "evpivo_ema12.pkl"))
    print("dump: evpivo_ema12.pkl")
else:
    print("0 trades")
