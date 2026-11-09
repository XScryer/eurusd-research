# Agreement counts (+-60s, same direction) for SEVERAL target events.
# Groups: n_imp (ev_*), n_imb (ev2_imb_*), n_strk (ev2_streak_*),
# n_borda (ev3_borda_*). The target file is always excluded from its own
# group. NOTE: symmetric window = lookahead; causal: audit_lookahead_multi.py.
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

ALVOS = [
    "ev3_borda_K1.0_W3000_R1.5.pkl",
    "ev3_borda_K3.0_W1000_R1.5.pkl",
    "ev2_imb_K0.3_W30_R1.5.pkl",
    "ev2_imb_K0.35_W50_R1.5.pkl",
    "ev2_streak_K8.0_W30_R1.5.pkl",
    "ev2_streak_K10.0_W30_R1.5.pkl",
    "ev_K3_W120_R1.5.pkl",
    "ev_K4_W60_R1.5.pkl",
]

def grupo_de(base):
    if base.startswith("ev2_imb_"): return "n_imb"
    if base.startswith("ev2_streak_"): return "n_strk"
    if base.startswith("ev3_borda_"): return "n_borda"
    if base.startswith("ev_"): return "n_imp"
    return None

# 1) carrega todos os eventos por grupo (excepto derivados)
todos = {g: {1: [], -1: []} for g in ("n_imp", "n_imb", "n_strk", "n_borda")}
for p in sorted(glob.glob(os.path.join(PASTA, "ev*.pkl"))):
    base = os.path.basename(p)
    if base.startswith(("fade_", "ev4_", "ev5_", "ev6_", "ev7_", "ev8_",
                        "ev9_", "ev10_", "ev11_", "evp_", "contagens_")):
        continue
    g = grupo_de(base)
    if g is None:
        continue
    df = pd.read_pickle(p)
    t = df["t"].to_numpy()
    d = df["dir"].to_numpy().astype(np.int8)
    for dd in (1, -1):
        todos[g][dd].append((base, t[d == dd]))
    del df
print("carregados", flush=True)

arr = {}
for g in todos:
    for dd in (1, -1):
        # lista de (ficheiro, ts): mantem separacao por ficheiro p/ exclusao do alvo
        arr[(g, dd)] = todos[g][dd]

# 2) para cada alvo, conta concordancias por grupo (excluindo o proprio ficheiro)
for alvo in ALVOS:
    fp = os.path.join(PASTA, alvo)
    if not os.path.exists(fp):
        print("falta", alvo, flush=True); continue
    df = pd.read_pickle(fp)
    g_alvo = grupo_de(alvo)
    t = df["t"].to_numpy()
    d = df["dir"].to_numpy().astype(np.int8)
    n = len(df)
    for g in ("n_imp", "n_imb", "n_strk", "n_borda"):
        cnt = np.zeros(n, dtype=np.int32)
        for dd in (1, -1):
            mask = np.where(d == dd)[0]
            if len(mask) == 0:
                continue
            # concatena ts de todos os ficheiros do grupo, excepto o alvo
            partes = [ts for (b, ts) in arr[(g, dd)] if b != alvo]
            if not partes:
                continue
            a = np.sort(np.concatenate(partes))
            tev = t[mask]
            lo = np.searchsorted(a, tev - JANELA_MS, side="left")
            hi = np.searchsorted(a, tev + JANELA_MS, side="right")
            cnt[mask] = (hi - lo).astype(np.int32)
        df[g] = cnt
    rot = alvo.split("_")[0] + "_" + alvo.split("_")[1] if alvo.startswith("ev3") else alvo[:12]
    saida = os.path.join(PASTA, "contagens_" + alvo)
    df.to_pickle(saida)
    print(alvo, "->", os.path.basename(saida), len(df),
          "| com>=1:", {g: int((df[g] > 0).sum()) for g in ("n_imp","n_imb","n_strk","n_borda")}, flush=True)
    del df
