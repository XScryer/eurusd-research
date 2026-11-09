# -*- coding: utf-8 -*-
"""AUDIT — verifies the two suspected bugs in
measure_pivot_rsi.py without running it.

Bug A (H4 lookahead): h4.c.iloc[j] uses the H4 bar CONTAINING t but
h4.c is the bar FINAL close (up to ~4h future).
Bug B (pivot off-by-one): pv[i] = pivot from day i-1; loop uses
pv.iloc[j-1] => pivot from 2 days ago.
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
h4 = m1.resample("4h").agg(c=("close","last")).dropna()
h4e = h4.c.ewm(span=20, adjust=False).mean()

h4_times = h4.index
n5 = len(m5)

# --- Bug A: para cada barra M5, a barra H4 usada esta completa em t?
# Barra M5 i cobre [t_i, t_i+5min). Sinal conhecido no fecho = t_i+5min.
# Barra H4 [T, T+4h) esta completa em T+4h.
inc = 0; tot = 0; ex = []
for i, t in enumerate(m5.index):
    j = h4_times.searchsorted(t, side="right") - 1
    if j < 0: continue
    t_close = t + pd.Timedelta(minutes=5)
    h4_fim = h4_times[j] + pd.Timedelta(hours=4)
    tot += 1
    if h4_fim > t_close:
        inc += 1
        if len(ex) < 5: ex.append((t, h4_times[j], h4_fim))
print(f"[BugA] barras M5 onde a barra H4 usada AINDA NAO FECHOU no instante do sinal:")
print(f"  {inc}/{tot} = {inc/tot*100:.1f}%")
for e in ex: print("   ex:", e)
# quanto futuro? distribuicao do atraso do fecho H4 vs fecho do sinal M5
atrasos = []
for i, t in enumerate(m5.index[::37]):  # amostra
    j = h4_times.searchsorted(t, side="right") - 1
    if j < 0: continue
    t_close = t + pd.Timedelta(minutes=5)
    atrasos.append((h4_times[j] + pd.Timedelta(hours=4) - t_close).total_seconds()/60)
atrasos = np.array(atrasos)
print(f"  atraso do fecho H4 vs fecho do sinal M5 (min): med={np.median(atrasos):.0f} max={atrasos.max():.0f}")

# --- Bug B: que dia gerou os pivots usados? mostrar 10 exemplos
m5c = m5.c.to_numpy()
dd = m5.resample("1D").agg(h=("h","max"), l=("l","min"), c=("c","last")).dropna()
ph, pl, pc = dd.h.shift(1), dd.l.shift(1), dd.c.shift(1)
pv = (ph + pl + pc) / 3
days = dd.index.normalize()
dmap = {d: i for i, d in enumerate(days)}
print("\n[BugB] pivot usado num dia vs dia que gerou o HLC:")
mostrados = 0
for i, t in enumerate(m5.index):
    j = dmap.get(t.normalize())
    if j is None or j < 2: continue
    k = j - 1
    dia_uso = days[j]; dia_fonte = days[k-1]   # pv[k] usa dd[k-1]
    if mostrados < 12:
        print(f"  barra {t} (dia {dia_uso.date()}): pivots de {dia_fonte.date()} "
              f"(ontem seria {days[j-1].date()})")
        mostrados += 1
    if t.normalize() > days[min(30, len(days)-1)]: break
