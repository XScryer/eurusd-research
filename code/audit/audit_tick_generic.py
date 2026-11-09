# -*- coding: utf-8 -*-
"""AUDIT — generic tick-level sim.
Usage: python audit_tick_generic.py <events.pkl> <output.pkl> [tag]
Replicates simulate_pivot_tick.py exactly.
"""
import os
import sys, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
PIP = 0.0001
USD_POR_PIP = 0.10
COMISSAO = {"fusion": 0.05, "pepperstone": 0.06}
MAX_S = 16.7 * 3600

ev_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else ev_path.replace(".pkl", "_tick.pkl")
tag = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(ev_path)

ev = pd.read_pickle(ev_path).sort_values("t_ent").reset_index(drop=True)
ev["tms"] = ev.t_ent.astype("datetime64[ms]").astype("int64")
print(f"[{tag}] eventos: {len(ev)}", flush=True)

trades = []
cache = {}
pos_ate = -1
n_skip = 0
for _, e in ev.iterrows():
    ano = int(e.t_ent.year)
    if ano not in cache:
        zb = np.load(os.path.join(BIN, f"BID_{ano}.npz"))
        za = np.load(os.path.join(BIN, f"ASK_{ano}.npz"))
        cache[ano] = (zb["ts"], zb["px"], za["ts"], za["px"])
        while len(cache) > 2:
            del cache[next(iter(cache))]
    ts_b, px_b, ts_a, px_a = cache[ano]

    t_in = int(e.tms); d = int(e.dir); sl = float(e.sl)
    if t_in <= pos_ate:
        n_skip += 1; continue
    if d == 1:
        ja = int(np.searchsorted(ts_a, t_in, side="left"))
        cand = [x for x in (ja-1, ja, ja+1) if 0 <= x < len(ts_a)]
        if not cand: n_skip += 1; continue
        jb = min(cand, key=lambda x: abs(int(ts_a[x]) - t_in))
        entry = float(px_a[jb]); t_act = int(ts_a[jb])
        tp = entry + 1.7 * (entry - sl)
        s_ts, s_px = ts_b, px_b
    else:
        jb2 = int(np.searchsorted(ts_b, t_in, side="left"))
        cand = [x for x in (jb2-1, jb2, jb2+1) if 0 <= x < len(ts_b)]
        if not cand: n_skip += 1; continue
        jb = min(cand, key=lambda x: abs(int(ts_b[x]) - t_in))
        entry = float(px_b[jb]); t_act = int(ts_b[jb])
        tp = entry - 1.7 * (sl - entry)
        s_ts, s_px = ts_a, px_a

    t_fim = min(t_act + int(MAX_S * 1000), int(s_ts[-1]))
    j0 = int(np.searchsorted(s_ts, t_act, side="left"))
    j1 = int(np.searchsorted(s_ts, t_fim, side="right"))
    path = s_px[j0:j1]
    if len(path) == 0:
        n_skip += 1; continue
    if d == 1:
        hit_sl = np.nonzero(path <= sl)[0]
        hit_tp = np.nonzero(path >= tp)[0]
    else:
        hit_sl = np.nonzero(path >= sl)[0]
        hit_tp = np.nonzero(path <= tp)[0]
    isl = int(hit_sl[0]) if len(hit_sl) else 10**18
    itp = int(hit_tp[0]) if len(hit_tp) else 10**18
    if itp < isl:
        motivo, px_out, hit = "tp", float(tp), itp
    elif isl < 10**18:
        motivo = "sl"
        px_out = float(min(sl, path[isl])) if d == 1 else float(max(sl, path[isl]))
        hit = isl
    else:
        motivo, px_out, hit = "fim", float(path[-1]), len(path) - 1
    t_out = int(s_ts[j0 + hit])
    pips = (px_out - entry) / PIP if d == 1 else (entry - px_out) / PIP
    trades.append({"ano": ano, "t": t_act, "dir": d, "entry": entry,
                   "exit": px_out, "pips": pips, "usd_g": pips * USD_POR_PIP,
                   "motivo": motivo, "t_out": t_out, "risk": float(e.risk)})
    pos_ate = t_out

if not trades:
    print("0 trades"); raise SystemExit
df = pd.DataFrame(trades)
n = len(df)
dias = max((df.t_out.max() - df.t.min()) / 86400000, 1)
tp_ = (df.motivo == "tp").sum(); sl_ = (df.motivo == "sl").sum()
gp = df.usd_g[df.usd_g > 0].sum(); gl = -df.usd_g[df.usd_g <= 0].sum()
print(f"\n=== [{tag}] TICK-LEVEL ===")
print(f"trades={n} (~{n/dias:.2f}/dia) | tp={tp_} sl={sl_} fim={n-tp_-sl_} | "
      f"win={(df.pips>0).mean()*100:.1f}% | PF_gross={gp/max(gl,1e-9):.2f}")
print(f"pips/trade={df.pips.mean():+.3f} | dur_med={(df.t_out-df.t).median()/60000:.0f}min")
for nome, com in COMISSAO.items():
    liq = df.usd_g.sum() - com * n
    print(f"  liquido {nome}: ${liq:+.2f} (${liq/n:+.3f}/trade) = ${(liq/dias):+.3f}/dia")
print("  por ano (usd_gross):")
print(df.groupby("ano").usd_g.sum().round(2).to_string())
df.to_pickle(out_path)
print("dump:", out_path, "| saltados:", n_skip)
