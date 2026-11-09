# -*- coding: utf-8 -*-
"""Kristina Forex "20 pips/day": M15 bias (EMA20/50) + M5 zone
(FVG) + TP 20.

M5 resampled from cTrader M1. Bullish FVG: low[i+1] > high[i-1] ->
zone [high[i-1], low[i+1]]. Long: M15 close above EMA20/50 + pullback
touches zone + bullish reaction bar. SL = zone bottom -2 pips.
TP = +20 pips. Short: mirror. Bar-level sim, SL first on tie.
"""
import numpy
import sys as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PIP = 0.0001
# M15 cTrader
f15 = [str(ctrader_bars_dir() / "EURUSD_M15_ctrader_2020-01-01_2024-12-31.csv"),
       str(ctrader_bars_dir() / "EURUSD_M15_ctrader_2025-01-01_2026-10-22.csv")]
m15 = pd.concat([pd.read_csv(f, parse_dates=["time"]) for f in f15]).set_index("time").sort_index()
# M1 cTrader -> M5
f1 = str(ctrader_bars_dir() / "EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv")
m1 = pd.read_csv(f1, parse_dates=["time"]).set_index("time").sort_index()
m5 = m1.resample("5min").agg(o=("open","first"), h=("high","max"),
                             l=("low","min"), c=("close","last")).dropna()
print(f"M15={len(m15)} M5={len(m5)}", flush=True)

# EMAs no M15
e20 = m15.close.ewm(span=20, adjust=False).mean().to_numpy()
e50 = m15.close.ewm(span=50, adjust=False).mean().to_numpy()
c15 = m15.close.to_numpy()

# FVGs no M5
o5 = m5.o.to_numpy(); h5 = m5.h.to_numpy(); l5 = m5.l.to_numpy(); c5 = m5.c.to_numpy()
n5 = len(m5)
# zonas activas: listas de (idx_fim_validade, topo, fundo)
# bullish FVG em i (usa i-1,i,i+1): zona [h[i-1], l[i+1]]
bull_zones = []  # (ate_idx, topo, fundo)
bear_zones = []
for i in range(1, n5 - 1):
    if l5[i + 1] > h5[i - 1]:
        bull_zones.append((i + 60, h5[i - 1], l5[i + 1]))   # valida ~5h
    if h5[i + 1] < l5[i - 1]:
        bear_zones.append((i + 60, l5[i - 1], h5[i + 1]))   # topo,fundo trocados

# mapa timestamp->idx M15 para vies
m15_idx = {t: i for i, t in enumerate(m15.index)}
m5_times = m5.index

def ema_at(t):
    # EMA do M15 vigente no instante t (ultima barra M15 <= t)
    j = m15.index.searchsorted(t, side="right") - 1
    if j < 50: return None
    return c15[j], e20[j], e50[j]

# sim
trades = []
i = 60
while i < n5 - 60:
    t = m5_times[i]
    vi = ema_at(t)
    if vi is None:
        i += 1; continue
    c15v, e20v, e50v = vi
    uptrend = c15v > e20v and c15v > e50v
    dntrend = c15v < e20v and c15v < e50v
    if not (uptrend or dntrend):
        i += 1; continue
    # procura zona activa que o preco esta a tocar AGORA
    done = False
    for ate, ztop, zbot in (bull_zones if uptrend else bear_zones):
        if i > ate: continue
        if uptrend:
            # pullback toca zona: low actual dentro/abaixo do topo, acima do fundo-5
            if l5[i] <= ztop + 2 * PIP and l5[i] >= zbot - 8 * PIP and c5[i] > o5[i]:
                ent = c5[i + 1] if i + 1 < n5 else c5[i]
                sl = zbot - 2 * PIP; tp = ent + 20 * PIP
                d = 1
            else:
                continue
        else:
            if h5[i] >= zbot - 2 * PIP and h5[i] <= ztop + 8 * PIP and c5[i] < o5[i]:
                ent = c5[i + 1] if i + 1 < n5 else c5[i]
                sl = ztop + 2 * PIP; tp = ent - 20 * PIP
                d = -1
            else:
                continue
        # sim forward
        j = i + 1; motivo = "fim"; px = c5[min(j + 96, n5 - 1)]
        while j < min(i + 96, n5):
            if d == 1:
                if l5[j] <= sl: motivo = "sl"; px = min(sl, l5[j]); break
                if h5[j] >= tp: motivo = "tp"; px = tp; break
            else:
                if h5[j] >= sl: motivo = "sl"; px = max(sl, h5[j]); break
                if l5[j] <= tp: motivo = "tp"; px = tp; break
            j += 1
        pips = (px - ent) / PIP * d
        trades.append({"t": t, "dir": d, "pips": pips, "motivo": motivo})
        i = j + 5   # cooldown
        done = True
        break
    if not done:
        i += 1

df_t = pd.DataFrame(trades)
if len(df_t):
    n = len(df_t); dias = (m5.index[-1] - m5.index[0]).days
    gp = df_t.pips[df_t.pips > 0].sum(); gl = -df_t.pips[df_t.pips <= 0].sum()
    print(f"\n=== Kristina M5-FVG ===")
    print(f"trades={n} (~{n/(dias/7):.1f}/sem) | win={(df_t.pips>0).mean()*100:.0f}% | "
          f"PF_g={gp/max(gl,1e-9):.2f} | avg={df_t.pips.mean():+.2f} pips")
    liq = df_t.pips.mean() - 0.6
    print(f"liquido~{liq:+.2f} pips/trade = ${(liq*0.10*len(df_t)):+.2f} total, "
          f"${(liq*0.10*len(df_t)/ (dias/30)):+.2f}/mes @0.01")
    print(df_t.groupby(df_t.t.dt.year).pips.mean().round(2).to_string())
else:
    print("0 trades")
