#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Long horizons 600/900/1800/3600s for EVERY impulse event, both
directions (impulse and fade). Output: data/impulso/lon_<combo>.pkl
"""
import os
import sys
import argparse
import glob
import numpy as np
import pandas as pd

from extract_impulse_events import BIN, OUT, PIP, bid_em, ask_em

HORIZONTES = [600, 900, 1800, 3600]


def outcomes_longos(df, ano, ts_b, px_b, ts_a, px_a):
    t_ev = df["t"].to_numpy()
    d = df["dir"].to_numpy().astype(np.int8)
    bid_e = df["bid_e"].to_numpy()
    ask_e = df["ask_e"].to_numpy()
    ok_a = df["ok_a"].to_numpy().astype(bool)
    n = len(df)
    rows = {}
    for h in HORIZONTES:
        t_h = t_ev + h * 1000
        jb, okb = bid_em(ts_b, px_b, t_h)
        ja, oka = ask_em(ts_a, px_a, t_h)
        outb = (px_b[jb] - ask_e) / PIP     # compra
        outs = (bid_e - px_a[ja]) / PIP     # venda
        # direccao do impulso (dir=+1 -> compra)
        v_imp = np.where(d == 1, outb, outs)
        ok_imp = np.where(d == 1, ok_a & okb, oka)
        # direccao fade (contraria)
        v_fad = np.where(d == 1, outs, outb)
        ok_fad = np.where(d == 1, oka, ok_a & okb)
        v_imp[~ok_imp] = np.nan
        v_fad[~ok_fad] = np.nan
        rows["imp%d" % h] = v_imp
        rows["fad%d" % h] = v_fad
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--combos", nargs="*", default=None)
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    args = ap.parse_args()

    if args.combos:
        ficheiros = [os.path.join(OUT, "ev_%s.pkl" % c) for c in args.combos]
    else:
        ficheiros = sorted(glob.glob(os.path.join(OUT, "ev_*.pkl")))
    anos_set = set(args.anos) if args.anos else set(
        int(f[4:8]) for f in os.listdir(BIN)
        if f.startswith("BID_") and f.endswith(".npz"))

    cache = {}
    for fp in ficheiros:
        if not os.path.exists(fp):
            print("falta %s" % fp, flush=True); continue
        base = os.path.basename(fp)[3:-4]
        destino = os.path.join(OUT, "lon_%s.pkl" % base)
        df = pd.read_pickle(fp)
        partes = []
        for ano, g in df.groupby("ano"):
            ano = int(ano)
            if ano not in anos_set:
                continue
            if ano not in cache:
                zb = np.load(os.path.join(BIN, "BID_%d.npz" % ano))
                za = np.load(os.path.join(BIN, "ASK_%d.npz" % ano))
                cache[ano] = (zb["ts"], zb["px"], za["ts"], za["px"])
                print("  carregado %d" % ano, flush=True)
            ts_b, px_b, ts_a, px_a = cache[ano]
            lo = outcomes_longos(g.reset_index(drop=True), ano,
                                 ts_b, px_b, ts_a, px_a)
            partes.append(lo)
        if not partes:
            continue
        res = pd.concat(partes, ignore_index=True)
        # alinha com o df original por posicao (mesma ordem de groupby/concat)
        ev = pd.concat([g.reset_index(drop=True)
                        for _, g in df.groupby("ano") if int(_) in anos_set],
                       ignore_index=True)
        res = pd.concat([ev.reset_index(drop=True),
                         res.reset_index(drop=True)], axis=1)
        res.to_pickle(destino)
        print("%s -> n=%d | imp600=%.2f fad600=%.2f imp1800=%.2f fad1800=%.2f"
              % (base, len(res), res["imp600"].mean(), res["fad600"].mean(),
                 res["imp1800"].mean(), res["fad1800"].mean()), flush=True)


if __name__ == "__main__":
    main()
