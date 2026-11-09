# Past-only agreement counts [t-60s, t) for several targets — the causal
# version. Question: does the solo->fade / agreement->momentum mechanism
# survive without lookahead? (It does not — see docs/tick-level-scalping.md.)
import glob
import os
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PASTA = str(impulso_dir())
JANELA_MS = 60_000
ALVOS = [
    "ev_K2_W120_R1.5.pkl",
    "ev2_imb_K0.25_W30_R1.5.pkl",
    "ev2_imb_K0.3_W30_R1.5.pkl",
    "ev2_streak_K6.0_W30_R1.5.pkl",
    "ev3_borda_K2.0_W3000_R1.5.pkl",
]

def grupo_de(base):
    if base.startswith("ev2_imb_"): return "n_imb"
    if base.startswith("ev2_streak_"): return "n_strk"
    if base.startswith("ev3_borda_"): return "n_borda"
    if base.startswith("ev_"): return "n_imp"
    return None

EXCLUI = ("fade_","ev4_","ev5_","ev6_","ev7_","ev8_","ev9_","ev10_","ev11_",
          "ev12_","ev13_","ev14_","ev15_","ev16_","ev17_","evp_","contagens_",
          "trades_")

todos = {g: {1: [], -1: []} for g in ("n_imp","n_imb","n_strk","n_borda")}
for p in sorted(glob.glob(os.path.join(PASTA, "ev*.pkl"))):
    base = os.path.basename(p)
    if base.startswith(EXCLUI): continue
    g = grupo_de(base)
    if g is None: continue
    df = pd.read_pickle(p)
    t = df["t"].to_numpy(); d = df["dir"].to_numpy().astype(np.int8)
    for dd in (1,-1):
        todos[g][dd].append(t[d==dd])
    del df
print("familias carregadas", flush=True)

for alvo in ALVOS:
    df = pd.read_pickle(os.path.join(PASTA, alvo))
    t = df["t"].to_numpy(); d = df["dir"].to_numpy().astype(np.int8)
    n = len(df)
    past = np.zeros(n, np.int32)
    for g in ("n_imp","n_imb","n_strk","n_borda"):
        for dd in (1,-1):
            mask = np.where(d==dd)[0]
            if len(mask)==0: continue
            partes=[x for x in todos[g][dd]]
            if not partes: continue
            a=np.sort(np.concatenate(partes))
            tev=t[mask]
            lp=np.searchsorted(a, tev-JANELA_MS, side="left")
            rp=np.searchsorted(a, tev, side="left")
            past[mask]+=(rp-lp)
    df["n_past"]=past
    saida=os.path.join(PASTA,"passado_"+alvo)
    df.to_pickle(saida)
    print(alvo,"->",os.path.basename(saida),"past>=21:",(past>=21).mean(),flush=True)
    del df
