#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tick-flow detector — EURUSD tick microstructure events.

  streak : K=min same-direction tick run, W=max window s, R=re-arm
  imb    : K=|imbalance| in [-1,1], W=window in TICKS, R=re-arm

imb[i] = fraction of diffs in the dominant direction over last W diffs.
Re-arm: R-pip retrace from event price (or 1h timeout).
Output: ev2_*.pkl (same schema as extract_impulse_events).

Usage: python extract_flow_events.py --anos 2019 --det streak --K 8 --W 30
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd

from extract_impulse_events import (BIN, OUT, PIP, TIMEOUT_REARM_MS, ask_no_instante,
                          extrair_medidos)

MIN_GAP = 20          # ticks minimos entre eventos do mesmo detector


def rearm_seguinte(ts, px, cand, dirs, disp_abs, R, t_last):
    """Greedy re-arm: a partir de cada candidato, salta para depois do primeiro
    recuo de R pips (ou timeout 1h). Devolve mascara de eventos aceite."""
    Rp = R * PIP
    aceites = []
    ci = 0
    nc = len(cand)
    while ci < nc:
        c = int(cand[ci])
        d = int(dirs[ci])
        aceites.append(c)
        t_cap = ts[c] + TIMEOUT_REARM_MS
        j_end = int(np.searchsorted(ts, min(t_cap, t_last), side="right"))
        seg = px[c + 1:j_end]
        if len(seg):
            if d == 1:
                hits = np.nonzero(seg <= px[c] - Rp)[0]
            else:
                hits = np.nonzero(seg >= px[c] + Rp)[0]
            rearm = c + 1 + int(hits[0]) if len(hits) else j_end
        else:
            rearm = j_end
        # proximo candidato >= rearm E >= c+MIN_GAP
        alvo = max(rearm, c + MIN_GAP)
        ci = int(np.searchsorted(cand, alvo, side="left"))
    return np.array(aceites, dtype=np.int64)


def det_streak(ts, px, K, W, R):
    """Sequencia de >=K diffs com o mesmo sinal completada em <=W segundos."""
    K = int(K)
    dif = np.diff(px)
    s = np.sign(dif)
    s[s == 0] = np.nan
    # fronteiras de segmento (onde o sinal muda; NaN corta segmento)
    mud = np.nonzero(s[1:] != s[:-1])[0] + 1
    starts = np.concatenate([[0], mud])
    ends = np.concatenate([mud, [len(s)]])
    Ls = ends - starts
    sg0 = s[starts]
    Wms = W * 1000
    ok = (Ls >= K) & ~np.isnan(sg0)
    starts, ends, Ls, sg0 = starts[ok], ends[ok], Ls[ok], sg0[ok]
    if len(starts) == 0:
        return (np.array([], np.int64), np.array([], np.int8),
                np.array([], np.int64))
    e = starts + K                      # tick px do K-esimo diff
    e = np.clip(e, 0, len(px) - 1)
    t_ok = (ts[e] - ts[np.clip(starts + 1, 0, len(ts) - 1)]) <= Wms * 1.5
    cand = e[t_ok]
    dirs = np.where(sg0[t_ok] > 0, 1, -1).astype(np.int8)
    jlag0 = np.clip(cand - K, 0, len(px) - 1)
    if len(cand) == 0:
        return (np.array([], np.int64), np.array([], np.int8),
                np.array([], np.int64))
    ev = rearm_seguinte(ts, px, cand, dirs, None, R, ts[-1])
    pos = np.searchsorted(cand, ev)
    return ev, dirs[pos], jlag0[pos]


def det_imb(ts, px, K, W, R):
    """Desequilibrio |imb|>=K numa janela de W diffs (ticks)."""
    dif = np.diff(px)
    s = np.sign(dif)
    W = int(W)
    cs = np.concatenate([[0.0], np.cumsum(s)])
    n = len(s)
    if n < W:
        return (np.array([], np.int64), np.array([], np.int8),
                np.array([], np.int64))
    idx = np.arange(W - 1, n)
    soma = cs[idx + 1] - cs[idx + 1 - W]
    imb = soma / W
    hits = np.nonzero(np.abs(imb) >= K)[0]
    if len(hits) == 0:
        return (np.array([], np.int64), np.array([], np.int8),
                np.array([], np.int64))
    cand = idx[hits] + 1                       # tick px
    dirs = np.where(imb[hits] > 0, 1, -1).astype(np.int8)
    jlag0 = np.clip(cand - W, 0, len(px) - 1)
    ev = rearm_seguinte(ts, px, cand, dirs, None, R, ts[-1])
    pos = np.searchsorted(cand, ev)
    return ev, dirs[pos], jlag0[pos]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    ap.add_argument("--det", choices=["streak", "imb"], required=True)
    ap.add_argument("--K", nargs="*", type=float, required=True)
    ap.add_argument("--W", nargs="*", type=float, required=True)
    ap.add_argument("--R", nargs="*", type=float, default=[1.5])
    args = ap.parse_args()

    if args.anos:
        anos = args.anos
    else:
        anos = sorted(int(f[4:8]) for f in os.listdir(BIN)
                      if f.startswith("BID_") and f.endswith(".npz"))
    combos = [(k, int(w), r) for k in args.K for w in args.W for r in args.R]
    print(f"det={args.det} anos={anos} combos={len(combos)} -> {OUT}", flush=True)

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
        for (K, W, R) in combos:
            if args.det == "streak":
                ev, dirs, jlag = det_streak(ts_b, px_b, K, W, R)
            else:
                ev, dirs, jlag = det_imb(ts_b, px_b, K, W, R)
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
        nome = "ev2_%s_K%s_W%s_R%s.pkl" % (args.det, K, W, R)
        cam = os.path.join(OUT, nome)
        df.to_pickle(cam)
        n = len(df)
        dias = max(1, int(round((df['t'].max() - df['t'].min()) / 86400000)))
        print(f"{nome}: {n} eventos (~{n/dias:.1f}/dia) -> {cam}", flush=True)


if __name__ == "__main__":
    main()
