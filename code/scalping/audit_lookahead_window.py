# Lookahead test: for target events, count agreements ONLY in the past
# [t-60s, t) vs the symmetric window [-60s,+60s].
# If the signal depends on the future, past-only kills the edge.
import glob
import sys
import os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PASTA = str(impulso_dir())
JANELA_MS = 60_000
ALVO = "ev3_borda_K3.0_W1000_R1.5.pkl"

def grupo_de(base):
    if base.startswith("ev2_imb_"): return "n_imb"
    if base.startswith("ev2_streak_"): return "n_strk"
    if base.startswith("ev3_borda_"): return "n_borda"
    if base.startswith("ev_"): return "n_imp"
    return None

# carrega todos os eventos por grupo/direccao
todos = {g: {1: [], -1: []} for g in ("n_imp","n_imb","n_strk","n_borda")}
for p in sorted(glob.glob(os.path.join(PASTA, "ev*.pkl"))):
    base = os.path.basename(p)
    if base.startswith(("fade_","ev4_","ev5_","ev6_","ev7_","ev8_","ev9_",
                        "ev10_","ev11_","ev12_","ev13_","ev14_","ev15_",
                        "ev16_","ev17_","evp_","contagens_","trades_")):
        continue
    g = grupo_de(base)
    if g is None: continue
    df = pd.read_pickle(p)
    t = df["t"].to_numpy(); d = df["dir"].to_numpy().astype(np.int8)
    for dd in (1,-1):
        todos[g][dd].append(t[d==dd])
    del df
print("carregados", flush=True)

df = pd.read_pickle(os.path.join(PASTA, ALVO))
t = df["t"].to_numpy(); d = df["dir"].to_numpy().astype(np.int8)
n = len(df)

past = np.zeros(n, np.int32); fut = np.zeros(n, np.int32); tot60 = np.zeros(n, np.int32)
for g in ("n_imp","n_imb","n_strk","n_borda"):
    for dd in (1,-1):
        mask = np.where(d==dd)[0]
        if len(mask)==0: continue
        partes=[x for x in todos[g][dd]]
        if not partes: continue
        a=np.sort(np.concatenate(partes))
        tev=t[mask]
        # passado [t-60s, t): searchsorted left em t-60, right em t (exclui t exacto? inclui)
        lp=np.searchsorted(a, tev-JANELA_MS, side="left")
        rp=np.searchsorted(a, tev, side="left")          # eventos < t
        # futuro (t, t+60s]:
        lf=np.searchsorted(a, tev, side="right")
        rf=np.searchsorted(a, tev+JANELA_MS, side="right")
        past[mask]+=(rp-lp); fut[mask]+=(rf-lf)
        tot60[mask]+=(rf-lp)  # janela simetrica aprox
df["n_past"]=past; df["n_fut"]=fut; df["n_tot60"]=tot60
df.to_pickle(os.path.join(PASTA,"contagens_passado_"+ALVO))
print("gravado. past media=%.1f fut media=%.1f"%(past.mean(),fut.mean()))
print("frac eventos com past>=21:",(past>=21).mean())
print("frac eventos com tot60>=21:",(tot60>=21).mean())
