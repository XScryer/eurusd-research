# -*- coding: utf-8 -*-
"""Naive market-making on real EURUSD ticks — falsification test.

BUY limit at bid+f*spread fills when ask <= L; SELL limit at
ask-f*spread fills when bid >= A (optimistic: no queue/latency).
Full skew, 1 unit max; EOD mark-to-market. $0.025 commission/fill.

If the naive version loses -> MM is dead. If it wins -> a realistic
queue model is needed (most die there anyway).
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
PIP = 0.0001
COMISSAO_FILL = 0.025
USD_POR_PIP = 0.10


def sim_ano(ano, f, comis=COMISSAO_FILL):
    zb = np.load(os.path.join(BIN, f"BID_{ano}.npz"))
    za = np.load(os.path.join(BIN, f"ASK_{ano}.npz"))
    ts_b, px_b = zb["ts"], zb["px"]
    ts_a, px_a = za["ts"], za["px"]
    n_b, n_a = len(ts_b), len(ts_a)

    ib = ia = 0
    pb = pa = None
    pos = 0
    ent = ent_t = 0.0
    lb = la = 0.0
    trades = []
    dia_pnl = {}

    def fecha(t, px, motivo):
        nonlocal pos, ent, ent_t
        pips = (px - ent) / PIP if pos == 1 else (ent - px) / PIP
        usd = pips * USD_POR_PIP - 2 * comis
        trades.append((ent_t, t, pips, usd, motivo))
        d = pd.Timestamp(t, unit="ms", tz="UTC").date()
        dia_pnl[d] = dia_pnl.get(d, 0.0) + usd
        pos = 0; ent = 0.0

    while ib < n_b or ia < n_a:
        tb = int(ts_b[ib]) if ib < n_b else 1 << 62
        ta = int(ts_a[ia]) if ia < n_a else 1 << 62
        if tb <= ta:
            t = tb; pb = float(px_b[ib]); ib += 1
        else:
            t = ta; pa = float(px_a[ia]); ia += 1
        if pb is None or pa is None:
            continue
        spr = pa - pb
        if spr <= 0:
            continue

        # ---- fills (niveis postados no evento anterior) ----
        if pos == 0:
            if pa <= lb:                      # ask desceu ao nosso bid -> compra
                pos = 1; ent = lb; ent_t = t
            elif pb >= la:                    # bid subiu ao nosso ask -> venda
                pos = -1; ent = la; ent_t = t
        elif pos == 1:
            if pb >= la:                      # bid subiu ao nosso ask -> venda fecha
                fecha(t, la, "tp")
        else:
            if pa <= lb:                      # ask desceu ao nosso bid -> compra fecha
                fecha(t, lb, "tp")

        # ---- reposta ----
        if pos == 0:
            lb = pb + f * spr
            la = pa - f * spr
            if la <= lb:                      # spread < 2f: volta ao mercado
                lb, la = pb, pa
        elif pos == 1:
            la = pa - f * spr
            lb = -1e18
        else:
            lb = pb + f * spr
            la = 1e18

    if pos != 0:
        mid = (pb + pa) / 2
        pips = (mid - ent) / PIP if pos == 1 else (ent - mid) / PIP
        t = int(ts_b[-1])
        usd = pips * USD_POR_PIP - comis
        d = pd.Timestamp(t, unit="ms", tz="UTC").date()
        dia_pnl[d] = dia_pnl.get(d, 0.0) + usd
        trades.append((ent_t, t, pips, usd, "fim"))

    zb.close(); za.close()
    return trades, dia_pnl


def relatorio(trades, dia_pnl):
    if not trades:
        print("sem trades"); return
    df = pd.DataFrame(trades, columns=["t_in", "t_out", "pips", "usd", "motivo"])
    pips = df.pips.sum(); usd = df.usd.sum()
    wins = (df.pips > 0).mean()
    pf = df[df.pips > 0].pips.sum() / max(1e-9, -df[df.pips < 0].pips.sum())
    n = len(df)
    dias = pd.Series(dia_pnl)
    perd = (dias < 0).mean() if len(dias) else 0
    print(f"round-trips={n} | pips/trip={df.pips.mean():+.3f} | "
          f"soma pips={pips:+.0f} | PF_gross={pf:.2f} | win={wins:.1%}")
    print(f"  liquido total=${usd:+.2f} (${usd/max(1,n):+.4f}/trip)")
    if len(dias):
        print(f"  DIARIO: dias={len(dias)} perdedores={int((dias<0).sum())} "
              f"({perd:.0%}) | mediana=${dias.median():+.3f} "
              f"pior=${dias.min():+.2f} melhor=${dias.max():+.2f}")
    print("  por motivo:", df.motivo.value_counts().to_dict())
    df["ano"] = pd.to_datetime(df.t_in, unit="ms", utc=True).dt.year
    print(df.groupby("ano").usd.agg(["size", "sum", "mean"]).round(2).to_string())
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="*", type=int, required=True)
    ap.add_argument("--f", type=float, default=0.3,
                    help="fraccao do spread para dentro (0.3=compra a bid+30%spread)")
    args = ap.parse_args()
    todos, dp = [], {}
    for ano in args.anos:
        tr, dd = sim_ano(ano, args.f)
        todos += tr
        dp.update(dd)
        print(f"{ano}: {len(tr)} trips", flush=True)
    print(f"\n=== MM f={args.f} ===")
    relatorio(todos, dp)


if __name__ == "__main__":
    main()
