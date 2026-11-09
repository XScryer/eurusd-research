# For each target event (impulse K2_W120_R1.5), count how many OTHER events
# in the same direction exist within +-60s, split by group:
#   n_imp    = other impulses (ev_*, target file itself excluded)
#   n_imb    = imbalance (ev2_imb_)
#   n_strk   = streak    (ev2_streak_)
#   n_borda  = edge      (ev3_borda_)
# Any "solo" definition is then a cut on these columns.
# NOTE: symmetric +-60s window = LOOKAHEAD (docs/backtest-traps.md #1).
import glob
import os
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PASTA = str(impulso_dir())
ALVO = os.path.join(PASTA, "ev_K2_W120_R1.5.pkl")
SAIDA = os.path.join(PASTA, "contagens_conc_K2_W120_R1.5.pkl")
JANELA_MS = 60_000

grupo_de = {
    "n_imp": lambda b: b.startswith("ev_") and b != "ev_K2_W120_R1.5.pkl",
    "n_imb": lambda b: b.startswith("ev2_imb_"),
    "n_strk": lambda b: b.startswith("ev2_streak_"),
    "n_borda": lambda b: b.startswith("ev3_borda_"),
}

todos = {g: {1: [], -1: []} for g in grupo_de}
for p in sorted(glob.glob(os.path.join(PASTA, "ev*.pkl"))):
    base = os.path.basename(p)
    if base.startswith(("fade_", "ev4_", "ev5_", "ev6_", "contagens_")):
        continue
    g = next((g for g, f in grupo_de.items() if f(base)), None)
    if g is None:
        continue
    df = pd.read_pickle(p)
    t = df["t"].to_numpy()
    d = df["dir"].to_numpy().astype(np.int8)
    for dd in (1, -1):
        todos[g][dd].append(t[d == dd])
    del df
    print(base, "->", g, flush=True)

arr = {}
for g in grupo_de:
    for dd in (1, -1):
        arr[(g, dd)] = np.sort(np.concatenate(todos[g][dd])) if todos[g][dd] else np.array([], dtype=np.int64)
        print(g, dd, len(arr[(g, dd)]))

df = pd.read_pickle(ALVO)
t = df["t"].to_numpy()
d = df["dir"].to_numpy().astype(np.int8)
n = len(df)
for g in grupo_de:
    cnt = np.zeros(n, dtype=np.int32)
    for dd in (1, -1):
        mask = d == dd
        a = arr[(g, dd)]
        if len(a) == 0 or not mask.any():
            continue
        tev = t[mask]
        lo = np.searchsorted(a, tev - JANELA_MS, side="left")
        hi = np.searchsorted(a, tev + JANELA_MS, side="right")
        cnt[np.where(mask)[0]] = (hi - lo).astype(np.int32)
    df[g] = cnt
    print(g, "eventos com >=1:", int((cnt > 0).sum()))

df.to_pickle(SAIDA)
print("gravado", SAIDA, len(df))
