# -*- coding: utf-8 -*-
"""Tick-level sim of zigzag leg structure (10-tick candles, R=2).

Entry: first tick reaching pullback_pivot + dir*2 pips.
--zz R: real-time zigzag exit (causal). Default exit is LOOKAHEAD
(reference only — do not use). Costs: real spread + RT commission.
"""
import os, argparse
import numpy as np
import pandas as pd
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
EV = str(impulso_dir() / "evpern_r0.0-1.5.pkl")
PIP = 0.0001
USD_POR_PIP = 0.10
COMISSAO = {"fusion": 0.05, "pepperstone": 0.06}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zz", type=float, default=-1)
    ap.add_argument("--sl_buf", type=float, default=1.0)
    ap.add_argument("--hold_max", type=int, default=900)
    ap.add_argument("--r_min", type=float, default=-1)
    ap.add_argument("--r_max", type=float, default=9)
    ap.add_argument("--s1_min", type=float, default=-1)
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    ap.add_argument("--dump", default=None)
    a = ap.parse_args()

    ev = pd.read_pickle(EV)
    ev = ev[(ev.imp_size >= a.r_min) & (ev.imp_size < a.r_max)
            & (ev.s1 >= a.s1_min)]
    if a.anos:
        ev = ev[ev.ano.isin(a.anos)]
    ev = ev.sort_values("t").reset_index(drop=True)
    print(f"eventos: {len(ev)}", flush=True)

    trades = []
    cache = {}
    pos_ate = -1
    n_skip = 0
    for _, e in ev.iterrows():
        ano = int(e.ano)
        if ano not in cache:
            zb = np.load(os.path.join(BIN, f"BID_{ano}.npz"))
            za = np.load(os.path.join(BIN, f"ASK_{ano}.npz"))
            cache[ano] = (zb["ts"], zb["px"], za["ts"], za["px"])
            while len(cache) > 2:
                del cache[next(iter(cache))]
        ts_b, px_b, ts_a, px_a = cache[ano]

        t_in = int(e.t); d = int(e.dir)
        if t_in <= pos_ate:
            n_skip += 1; continue
        piv = float(e.piv)
        entry = float(e.ask_e) if d == 1 else float(e.bid_e)
        sl = piv - a.sl_buf * PIP if d == 1 else piv + a.sl_buf * PIP

        # ---------- saida ZZ (causal) ----------
        t_lim = min(t_in + a.hold_max * 1000, int(ts_b[-1]))
        jz0 = int(np.searchsorted(ts_b, t_in, side="left"))
        jz1 = int(np.searchsorted(ts_b, t_lim, side="right"))
        seg = px_b[jz0:jz1]
        nseg = (len(seg) // 10) * 10
        t_zz = None
        if nseg >= 10:
            ch = seg[:nseg].reshape(-1, 10).max(axis=1)
            cl = seg[:nseg].reshape(-1, 10).min(axis=1)
            R = a.zz * PIP
            if d == 1:
                run = np.maximum.accumulate(ch)
                conf = np.nonzero(cl <= run - R)[0]
            else:
                run = np.minimum.accumulate(cl)
                conf = np.nonzero(ch >= run + R)[0]
            if len(conf):
                ci = int(conf[0])
                tk = min((ci + 1) * 10 - 1, len(seg) - 1)
                t_zz = int(ts_b[jz0 + tk])
        t_scan = t_zz if t_zz is not None else t_lim

        # SL no lado de execucao ate' t_scan
        t_sl = None; px_sl = None
        if d == 1:
            j0 = int(np.searchsorted(ts_b, t_in, side="left"))
            j1 = int(np.searchsorted(ts_b, t_scan, side="right"))
            hits = np.nonzero(px_b[j0:j1] <= sl)[0]
            if len(hits):
                jj = j0 + int(hits[0])
                t_sl = int(ts_b[jj]); px_sl = float(min(sl, px_b[jj]))
        else:
            j0 = int(np.searchsorted(ts_a, t_in, side="left"))
            j1 = int(np.searchsorted(ts_a, t_scan, side="right"))
            hits = np.nonzero(px_a[j0:j1] >= sl)[0]
            if len(hits):
                jj = j0 + int(hits[0])
                t_sl = int(ts_a[jj]); px_sl = float(max(sl, px_a[jj]))

        cand = []
        if t_sl is not None:
            cand.append((t_sl, px_sl, "sl"))
        if t_zz is not None:
            if d == 1:
                jj = int(np.searchsorted(ts_b, t_zz, side="left"))
                jj = min(jj, len(ts_b) - 1)
                cand.append((int(ts_b[jj]), float(px_b[jj]), "zz"))
            else:
                ja = int(np.searchsorted(ts_a, t_zz, side="left"))
                cand_a = [x for x in (ja - 1, ja, ja + 1) if 0 <= x < len(ts_a)]
                if cand_a:
                    jb = min(cand_a, key=lambda x: abs(int(ts_a[x]) - t_zz))
                    cand.append((int(ts_a[jb]), float(px_a[jb]), "zz"))
        if not cand:
            if d == 1:
                jj = min(int(np.searchsorted(ts_b, t_lim, side="right")) - 1, len(ts_b) - 1)
                t_out = int(ts_b[jj]); px_out = float(px_b[jj])
            else:
                jj = min(int(np.searchsorted(ts_a, t_lim, side="right")) - 1, len(ts_a) - 1)
                t_out = int(ts_a[jj]); px_out = float(px_a[jj])
            motivo = "fim"
        else:
            t_out, px_out, motivo = min(cand)
        pips = (px_out - entry) / PIP if d == 1 else (entry - px_out) / PIP
        trades.append({"ano": ano, "t": t_in, "dir": d, "entry": entry,
                       "exit": px_out, "pips": pips, "usd_g": pips * USD_POR_PIP,
                       "motivo": motivo, "t_out": t_out,
                       "r": float(e.imp_size), "s1": float(e.s1),
                       "dur_s": (t_out - t_in) / 1000})
        pos_ate = t_out

    if not trades:
        print("0 trades"); return
    df = pd.DataFrame(trades)
    n = len(df)
    dias = max((df.t_out.max() - df.t.min()) / 86400000, 1)
    tp_ = (df.motivo == "zz").sum(); sl_ = (df.motivo == "sl").sum()
    gp = df.usd_g[df.usd_g > 0].sum(); gl = -df.usd_g[df.usd_g <= 0].sum()
    print(f"\n=== pernada ZZ R={a.zz} ===")
    print(f"trades={n} (~{n/dias:.1f}/dia) | zz={tp_} sl={sl_} fim={n-tp_-sl_} | "
          f"win={(df.pips>0).mean()*100:.1f}% | PF_gross={gp/max(gl,1e-9):.2f}")
    print(f"pips/trade={df.pips.mean():+.3f} | dur_med={df.dur_s.median():.0f}s")
    for nome, com in COMISSAO.items():
        liq = df.usd_g.sum() - com * n
        print(f"  liquido {nome}: ${liq:+.2f} (${liq/n:+.3f}/trade) = ${(liq/dias):+.2f}/dia")
    print("  por ano (usd_gross):")
    print(df.groupby("ano").usd_g.sum().round(2).to_string())
    dia = (df.t_out // 86400000).astype(np.int64)
    g = pd.DataFrame({"dia": dia, "usd_g": df.usd_g, "n": 1}).groupby("dia").agg(
        n=("n", "sum"), gross=("usd_g", "sum"))
    for nome, com in COMISSAO.items():
        ld = g.gross - com * g.n
        print(f"  DIARIO {nome}: dias={len(ld)} perd={int((ld<0).sum())} "
              f"({(ld<0).mean()*100:.0f}%) med=${ld.median():+.2f} "
              f"pior=${ld.min():+.2f} | total=${ld.sum():+.2f}")
    print(f"saltados(posicao aberta): {n_skip}")
    if a.dump:
        df.to_pickle(a.dump); print("dump:", a.dump)


if __name__ == "__main__":
    main()
