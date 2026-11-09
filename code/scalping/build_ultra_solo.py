# Build ev6_ultrasolo: impulse events K2_W120_R1.5 with NO other event of
# ANY family/parameter in the same direction within +-JANELA seconds.
# NOTE: symmetric window = lookahead by design (the buggy version);
# see audit_lookahead_*.py for the causal recomputation.
import glob
import sys
import os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PASTA = str(impulso_dir())
ALVO = os.path.join(PASTA, "ev_K2_W120_R1.5.pkl")
SAIDA = os.path.join(PASTA, "ev6_ultrasolo_K2_W120_R1.5.pkl")
JANELA_MS = 60_000

# 1) carrega t e dir de TODOS os ficheiros de eventos (ev_, ev2_, ev3_)
#    exclui fade_ (outcomes), ev4_/ev5_/ev6_ (derivados)
ts_dir = {1: [], -1: []}
for p in sorted(glob.glob(os.path.join(PASTA, "ev*.pkl"))):
    base = os.path.basename(p)
    if base.startswith(("fade_", "ev4_", "ev5_", "ev6_")):
        continue
    df = pd.read_pickle(p)
    t = df["t"].to_numpy()
    d = df["dir"].to_numpy().astype(np.int8)
    for dd in (1, -1):
        ts_dir[dd].append(t[d == dd])
    del df
    print(base, flush=True)

todos = {}
for dd in (1, -1):
    todos[dd] = np.sort(np.concatenate(ts_dir[dd]))
    print(f"dir={dd}: {len(todos[dd])} eventos")

# 2) para cada evento alvo, existe outro evento mesma direccao a +-60s?
df = pd.read_pickle(ALVO)
df["fade_dir"] = -df["dir"]
t = df["t"].to_numpy()
d = df["dir"].to_numpy().astype(np.int8)

conc = np.zeros(len(df), dtype=bool)
for dd in (1, -1):
    mask = d == dd
    if not mask.any():
        continue
    arr = todos[dd]
    tev = t[mask]
    lo = np.searchsorted(arr, tev - JANELA_MS, side="left")
    hi = np.searchsorted(arr, tev + JANELA_MS, side="right")
    # remove auto-match: o proprio evento alvo esta no array (mesmo ficheiro).
    # conta quantos eventos na janela; se >1 e concordancia (>=2 = outro existe)
    # truque: para cada evento, janela [lo,hi) tem hits; auto-match = 1 hit exacto.
    # como o alvo esta incluido, concordancia real = (hi-lo) > 1
    # MAS se houver 2 eventos alvo no mesmo ms, complica. Aceitavel: exigimos >=2 hits.
    hits = hi - lo
    idx = np.where(mask)[0]
    conc[idx[hits > 1]] = True

print(f"alvo={len(df)} com_concordancia={conc.sum()} ({conc.mean()*100:.1f}%) solo={(~conc).sum()}")

# 3) guarda so os solos
solo = df.loc[~conc].copy()
solo.to_pickle(SAIDA)
print("gravado", SAIDA, len(solo))
