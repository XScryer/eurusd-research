# -*- coding: utf-8 -*-
"""Box Theory EURUSD M5 — fading halves of the pre-market box.

Box = max/min of M5 bars 06:00-07:47 UTC. Mid = (max+min)/2.
Entry window 10:07-14:30 UTC. SHORT only upper half, LONG lower.
Trigger = rejection candle (close<open, upper wick >= body).
Entry next bar open. SL = box extreme +3 pips. TP: to mid or fixed.
1 trade/day.
"""
import numpy
import sys as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PIP = 0.0001
f1 = str(ctrader_bars_dir() / "EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv")
m1 = pd.read_csv(f1, parse_dates=["time"]).set_index("time").sort_index()
m5 = m1.resample("5min").agg(o=("open","first"), h=("high","max"),
                             l=("low","min"), c=("close","last")).dropna()
o5 = m5.o.to_numpy(); h5 = m5.h.to_numpy(); l5 = m5.l.to_numpy()
c5 = m5.c.to_numpy(); n5 = len(m5); times = m5.index
print(f"M5={n5} {times[0]} -> {times[-1]}", flush=True)

BOX_LO, BOX_HI = (6, 0), (7, 47)     # UTC
WIN_LO, WIN_HI = (10, 7), (14, 30)   # UTC

# box por dia
days = times.normalize().unique()
box = {}
for d in days:
    mask = (times.normalize() == d) & \
           ((times.hour > BOX_LO[0]) | ((times.hour == BOX_LO[0]) & (times.minute >= BOX_LO[1]))) & \
           ((times.hour < BOX_HI[0]) | ((times.hour == BOX_HI[0]) & (times.minute <= BOX_HI[1])))
    idx = np.nonzero(mask)[0]
    if len(idx) >= 10:
        box[d] = (h5[idx].max(), l5[idx].min())

trades = []
used_days = set()
i = 0
while i < n5 - 1:
    t = times[i]; d = t.normalize()
    if d in used_days or d not in box:
        i += 1; continue
    # janela de entradas
    in_win = (t.hour > WIN_LO[0] or (t.hour == WIN_LO[0] and t.minute >= WIN_LO[1])) and \
             (t.hour < WIN_HI[0] or (t.hour == WIN_HI[0] and t.minute <= WIN_HI[1]))
    if not in_win:
        i += 1; continue
    bh, bl = box[d]; mid = (bh + bl) / 2
    # rejeicao short: na metade superior, perto do topo (topo-30% da box)
    # rejeicao long: metade inferior, perto do fundo
    upper_zone = c5[i] > mid and c5[i] > bl + 0.6 * (bh - bl)
    lower_zone = c5[i] < mid and c5[i] < bh - 0.6 * (bh - bl)
    body = abs(c5[i] - o5[i]); up_wick = h5[i] - max(o5[i], c5[i])
    dn_wick = min(o5[i], c5[i]) - l5[i]
    sig = 0
    if upper_zone and c5[i] < o5[i] and up_wick >= body and up_wick > 2 * dn_wick:
        sig = -1
    elif lower_zone and c5[i] > o5[i] and dn_wick >= body and dn_wick > 2 * up_wick:
        sig = 1
    if sig == 0:
        i += 1; continue
    ent = o5[i + 1] if i + 1 < n5 else c5[i]
    if sig == -1:
        sl = bh + 3 * PIP
        tp_mid = mid; tp10 = ent - 10 * PIP; tp15 = ent - 15 * PIP; tp20 = ent - 20 * PIP
    else:
        sl = bl - 3 * PIP
        tp_mid = mid; tp10 = ent + 10 * PIP; tp15 = ent + 15 * PIP; tp20 = ent + 20 * PIP
    # sim: SL primeiro em empate, max 2 dias; regista exit por variante
    j = i + 1
    exits = {}
    sl_px = None
    tps = {"mid": tp_mid, "t10": tp10, "t15": tp15, "t20": tp20}
    hit = {}
    while j < min(i + 576, n5) and len(hit) < len(tps) + 1:
        if sig == -1:
            if h5[j] >= sl and sl_px is None: sl_px = sl; hit["__sl__"] = j
            for k, tp in tps.items():
                if k not in hit and l5[j] <= tp: hit[k] = j
        else:
            if l5[j] <= sl and sl_px is None: sl_px = sl; hit["__sl__"] = j
            for k, tp in tps.items():
                if k not in hit and h5[j] >= tp: hit[k] = j
        j += 1
    # para cada variante: se SL antes do TP -> perda; se TP -> ganho; senao fim
    row = {"t": t, "dir": sig, "ent": ent, "sl": sl}
    for k, tp in tps.items():
        jt = hit.get(k, 10**9); js = hit.get("__sl__", 10**9)
        if jt < js:
            row[k] = (tp - ent) / PIP * sig
        elif js < 10**9:
            row[k] = (sl - ent) / PIP * sig if sig == -1 else (ent - sl) / PIP * -1
            row[k] = -(abs(sl - ent)) / PIP
        else:
            row[k] = (c5[min(j, n5 - 1)] - ent) / PIP * sig
    trades.append(row)
    used_days.add(d)
    i = j + 1

df = pd.DataFrame(trades)
print(f"\ntrades: {len(df)} em {len(used_days)} dias ({(times[-1]-times[0]).days} dias)")
if len(df):
    for k in ["mid", "t10", "t15", "t20"]:
        a = df[k].to_numpy()
        gp = a[a > 0].sum(); gl = -a[a <= 0].sum()
        print(f"TP={k:4s}: n={len(a)} win={(a>0).mean()*100:.0f}% "
              f"avg={a.mean():+.2f} pips PF={gp/max(gl,1e-9):.2f} "
              f"liq~{a.mean()-0.6:+.2f}")
    df.to_pickle(str(impulso_dir() / "evbox.pkl"))
    print("dump evbox.pkl")
