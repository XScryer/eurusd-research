#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Range-edge detector — touches of the rolling extreme, EURUSD.

  K = max distance in pips to count as "at the edge"
  W = rolling window in TICKS
  R = re-arm retrace in pips

"up" event (dir=+1): within <=K pips of window max (resistance).
"dn" event (dir=-1): within <=K pips of window min (support).
Output: ev3_borda_*.pkl — same schema as extract_impulse_events.
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd

from extract_impulse_events import (BIN, OUT, PIP, TIMEOUT_REARM_MS, extrair_medidos)

MIN_GAP = 10


def det_borda(ts, px, K, W, R, hi, lo):
    K = float(K)
    n = len(px)
    if n < W + 10:
        return (np.array([], np.int64), np.array([], np.int8),
                np.array([], np.int64))
    d_hi = (hi - px) / PIP          # distancia a maxima (>=0)
    d_lo = (px - lo) / PIP          # distancia a minima (>=0)

    near_hi = d_hi <= K
    near_lo = d_lo <= K
    # primeiro tick de cada episodio de toque (borda crescente do mask)
    ch_hi = np.nonzero(near_hi & ~np.concatenate([[False], near_hi[:-1]]))[0]
    ch_lo = np.nonzero(near_lo & ~np.concatenate([[False], near_lo[:-1]]))[0]
    # remover indices < W (janela incompleta)
    ch_hi = ch_hi[ch_hi >= W]
    ch_lo = ch_lo[ch_lo >= W]

    # fundir por tempo e re-arm greedy por direccao
    Rp = R * PIP
    t_last = ts[-1]
    aceites = []
    dirs_out = []
    jlag_out = []
    # processar em ordem temporal; re-arm = preco afasta R pips do extremo
    # (para up: px <= hi_touch - R*PIP; p/ dn: px >= lo_touch + R*PIP)
    # hi_touch = px no momento? uso o extremo da janela: hi[ch]
    cand = np.sort(np.concatenate([ch_hi, ch_lo]))
    is_hi = np.isin(cand, ch_hi)
    ci = 0
    nc = len(cand)
    while ci < nc:
        c = int(cand[ci])
        d = 1 if is_hi[ci] else -1
        # extremo de referencia = max/min da janela nesse tick
        if d == 1:
            ref = hi[c]
        else:
            ref = lo[c]
        aceites.append(c); dirs_out.append(d)
        jlag_out.append(max(0, c - W // 4))
        t_cap = ts[c] + TIMEOUT_REARM_MS
        j_end = int(np.searchsorted(ts, min(t_cap, t_last), side="right"))
        seg = px[c + 1:j_end]
        if len(seg):
            if d == 1:
                hits = np.nonzero(seg <= ref - Rp)[0]
            else:
                hits = np.nonzero(seg >= ref + Rp)[0]
            rearm = c + 1 + int(hits[0]) if len(hits) else j_end
        else:
            rearm = j_end
        alvo = max(rearm, c + MIN_GAP)
        ci = int(np.searchsorted(cand, alvo, side="left"))
    if not aceites:
        return (np.array([], np.int64), np.array([], np.int8),
                np.array([], np.int64))
    return (np.array(aceites, np.int64), np.array(dirs_out, np.int8),
            np.array(jlag_out, np.int64))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    ap.add_argument("--K", nargs="*", type=float, required=True,
                    help="distancia a borda em pips")
    ap.add_argument("--W", nargs="*", type=int, required=True,
                    help="janela rolante em ticks")
    ap.add_argument("--R", nargs="*", type=float, default=[1.5])
    args = ap.parse_args()

    if args.anos:
        anos = args.anos
    else:
        anos = sorted(int(f[4:8]) for f in os.listdir(BIN)
                      if f.startswith("BID_") and f.endswith(".npz"))
    combos = [(k, w, r) for k in args.K for w in args.W for r in args.R]
    print(f"det=borda anos={anos} combos={len(combos)} -> {OUT}", flush=True)

    partes = {c: [] for c in combos}
    for ano in anos:
        pb = os.path.join(BIN, "BID_%d.npz" % ano)
        pa = os.path.join(BIN, "ASK_%d.npz" % ano)
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"  {ano}: falta npz, skip"); continue
        zb = np.load(pb); za = np.load(pa)
        ts_b, px_b = zb["ts"], zb["px"]
        ts_a, px_a = za["ts"], za["px"]
        print(f"  {ano}: bid={len(ts_b)/1e6:.1f}M ask={len(ts_a)/1e6:.1f}M",
              flush=True)
        zb.close(); za.close()
        # hi/lo rolante por W unico (cache por ano)
        Ws = sorted(set(w for (_, w, _) in combos))
        rol = {}
        for w in Ws:
            s = pd.Series(px_b)
            rol[w] = (s.rolling(w, min_periods=w).max().to_numpy(),
                      s.rolling(w, min_periods=w).min().to_numpy())
            print(f"    rolling W={w} calculado", flush=True)
        for (K, W, R) in combos:
            hi, lo = rol[W]
            ev, dirs, jlag = det_borda(ts_b, px_b, K, W, R, hi, lo)
            df = (extrair_medidos(ano, ts_b, px_b, ts_a, px_a, ev, dirs,
                                  jlag, K, W, R) if len(ev) else None)
            if df is not None and len(df):
                partes[(K, W, R)].append(df)
            print(f"    K={K} W={W} R={R}: {0 if df is None else len(df)} eventos",
                  flush=True)
        del ts_b, px_b, ts_a, px_a

    for (K, W, R), lst in partes.items():
        if not lst:
            continue
        df = pd.concat(lst, ignore_index=True)
        nome = "ev3_borda_K%s_W%s_R%s.pkl" % (K, W, R)
        cam = os.path.join(OUT, nome)
        df.to_pickle(cam)
        n = len(df)
        dias = max(1, int(round((df['t'].max() - df['t'].min()) / 86400000)))
        print(f"{nome}: {n} eventos (~{n/dias:.1f}/dia) -> {cam}", flush=True)


if __name__ == "__main__":
    main()
