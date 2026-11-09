#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fade outcomes — negotiable results AGAINST each impulse.

  impulse BUY  (dir=+1) -> fade SELL: enter bid_e, exit ask(t+H)
  impulse SELL (dir=-1) -> fade BUY : enter ask_e, exit bid(t+H)

Usage: python extract_fade_outcomes.py [--combos K2_W120_R1.5 ...]
"""
import os
import sys
import argparse
import glob
import numpy as np
import pandas as pd

from extract_impulse_events import BIN, OUT, HORIZONTES, H_MFE, PIP, bid_em, ask_em, ask_no_instante


def fade_eventos(df, ano, ts_b, px_b, ts_a, px_a):
    t_ev = df["t"].to_numpy()
    d = df["dir"].to_numpy().astype(np.int8)
    bid_e = df["bid_e"].to_numpy()
    ask_e = df["ask_e"].to_numpy()
    ok_a = df["ok_a"].to_numpy().astype(bool)
    n = len(df)

    rows = {"f_out%d" % h: np.full(n, np.nan) for h in HORIZONTES}
    idx_h = {}
    for h in HORIZONTES:
        t_h = t_ev + h * 1000
        jb, okb = bid_em(ts_b, px_b, t_h)
        ja, oka = ask_em(ts_a, px_a, t_h)
        idx_h[h] = (jb, ja)
        outb = (px_b[jb] - ask_e) / PIP      # lado compra (fade de dir=-1)
        outs = (bid_e - px_a[ja]) / PIP      # lado venda  (fade de dir=+1)
        val = np.where(d == 1, outs, outb)
        okm = np.where(d == 1, oka, ok_a & okb)
        val[~okm] = np.nan
        rows["f_out%d" % h] = val

    # indices de entrada p/ MFE/MAE
    e_b = np.clip(np.searchsorted(ts_b, t_ev, side="left"), 0, len(ts_b) - 1)
    ia, _ = ask_no_instante(ts_a, px_a, t_ev)

    mfe = {h: np.full(n, np.nan) for h in H_MFE}
    mae = {h: np.full(n, np.nan) for h in H_MFE}
    for k in range(n):
        dk = int(d[k])
        for h in H_MFE:
            jb, ja = idx_h[h]
            if dk == 1:   # fade SELL: caminho do ASK
                path = px_a[ia[k]:int(ja[k]) + 1]
                if len(path):
                    mfe[h][k] = (bid_e[k] - path.min()) / PIP
                    mae[h][k] = (bid_e[k] - path.max()) / PIP
            else:         # fade BUY: caminho do BID
                path = px_b[int(e_b[k]):int(jb[k]) + 1]
                if len(path):
                    mfe[h][k] = (path.max() - ask_e[k]) / PIP
                    mae[h][k] = (path.min() - ask_e[k]) / PIP
    for h in H_MFE:
        rows["f_mfe%d" % h] = mfe[h]
        rows["f_mae%d" % h] = mae[h]
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--combos", nargs="*", default=None,
                    help="nomes tipo K2_W120_R1.5 (sem ev_/fade_/ .pkl)")
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    ap.add_argument("--pref", default="ev_",
                    help="prefixo dos ficheiros de entrada (ev_, ev2_streak_...)")
    ap.add_argument("--suf", default="fade_",
                    help="prefixo dos ficheiros de saida")
    args = ap.parse_args()

    if args.combos:
        ficheiros = [os.path.join(OUT, "%s%s.pkl" % (args.pref, c))
                     for c in args.combos]
    else:
        ficheiros = sorted(glob.glob(os.path.join(OUT, args.pref + "*.pkl")))

    if args.anos:
        anos_set = set(args.anos)
    else:
        anos_set = set(int(f[4:8]) for f in os.listdir(BIN)
                      if f.startswith("BID_") and f.endswith(".npz"))

    cache = {}
    for fp in ficheiros:
        if not os.path.exists(fp):
            print("falta %s" % fp, flush=True); continue
        base = os.path.basename(fp)[len(args.pref):-4]   # tira prefixo e .pkl
        destino = os.path.join(OUT, "%s%s.pkl" % (args.suf, base))
        df = pd.read_pickle(fp)
        partes = []
        for ano, g in df.groupby("ano"):
            if int(ano) not in anos_set:
                continue
            ano = int(ano)
            if ano not in cache:
                zb = np.load(os.path.join(BIN, "BID_%d.npz" % ano))
                za = np.load(os.path.join(BIN, "ASK_%d.npz" % ano))
                cache[ano] = (zb["ts"], zb["px"], za["ts"], za["px"])
                print("  carregado %d: bid=%.1fM ask=%.1fM"
                      % (ano, len(cache[ano][0]) / 1e6, len(cache[ano][2]) / 1e6),
                      flush=True)
            ts_b, px_b, ts_a, px_a = cache[ano]
            fo = fade_eventos(g.reset_index(drop=True), ano, ts_b, px_b,
                              ts_a, px_a)
            fo["idx"] = g.index.to_numpy()
            partes.append((g.reset_index(drop=True), fo))
        if not partes:
            print("%s: sem eventos nos anos pedidos" % base, flush=True)
            continue
        ev = pd.concat([p[0] for p in partes], ignore_index=True)
        fd = pd.concat([p[1] for p in partes], ignore_index=True)
        res = pd.concat([ev.reset_index(drop=True),
                         fd.drop(columns=["idx"]).reset_index(drop=True)],
                        axis=1)
        res.to_pickle(destino)
        m60 = res["f_out60"].mean()
        print("%s -> %s | n=%d  fade m60=%.3f pips  m300=%.3f"
              % (base, os.path.basename(destino), len(res), m60,
                 res["f_out300"].mean()), flush=True)


if __name__ == "__main__":
    main()
