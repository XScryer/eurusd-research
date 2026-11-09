#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Impulse trade simulator — tick-level SL/TP/time-stop.

- 1 position at a time; entry at ask (BUY) / bid (SELL);
- fixed-pip SL/TP; optional --tstop seconds;
- real spread in prices; commission applied after in USD
  (Fusion ~$0.05/op, Pepperstone ~$0.06/op RT at 0.01 lot).

Usage:
  python simulate_impulse.py --K 3 --W 120 --R 1.5 --stop 3 --take 6 --tstop 300
  python simulate_impulse.py --K 2 --W 120 --R 1.5 --fade --stop 3 --take 3 \
      --spread_max 0.5 --pct_min 0.7 --h_to 20 --dt_min 5
"""
import os
import glob
import argparse
import numpy as np
import pandas as pd

from extract_impulse_events import ask_em
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
DIR = str(impulso_dir())
PIP = 0.0001
COMISSAO = {"fusion": 0.05, "pepperstone": 0.06}   # USD por op RT, lote 0.01
LOTE = 0.01
USD_POR_PIP = 10.0 * LOTE   # $0.10/pip


def carrega_eventos(K, W, R, anos=None, fade=False, prefixo=None):
    pref = prefixo or ("fade_" if fade else "ev_")
    dfs = []
    for p in sorted(glob.glob(os.path.join(DIR, pref + "*.pkl"))):
        df = pd.read_pickle(p)
        if df.K.iloc[0] == K and df.W.iloc[0] == W and df.R.iloc[0] == R:
            if anos is None or df["ano"].isin(anos).any():
                dfs.append(df)
    if not dfs:
        raise SystemExit("sem eventos para esse combo")
    return pd.concat(dfs, ignore_index=True)


def aplica_filtros(ev, args):
    antes = len(ev)
    if args.spread_max is not None:
        ev = ev[ev.spread_e <= args.spread_max]
    if args.pct_min is not None:
        ev = ev[ev.pct_dir >= args.pct_min]
    if args.h_from is not None:
        ev = ev[ev.hora >= args.h_from]
    if args.h_to is not None:
        ev = ev[ev.hora <= args.h_to]
    if args.dt_min is not None:
        ev = ev[ev.dt_prev.fillna(1e9) >= args.dt_min]
    if args.imp_min is not None:
        ev = ev[ev.imp_size >= args.imp_min]
    if args.imp_max is not None:
        ev = ev[ev.imp_size <= args.imp_max]
    if args.rng_max is not None:
        ev = ev[ev.rng300 <= args.rng_max]
    if args.rng_min is not None:
        ev = ev[ev.rng300 >= args.rng_min]
    if args.tick_min is not None:
        ev = ev[ev.tick_rate >= args.tick_min]
    print(f"filtros: {antes} -> {len(ev)} eventos")
    return ev


def simula_ano(ano, ev, ts_b, px_b, ts_a, px_a, stop_p, take_p, tstop_s,
               fade=False, retrace_p=0.0, retrace_win_s=0,
               retrace_mode="event"):
    """Simula trades do ano; 1 posicao de cada vez. Devolve lista de dicts.

    retrace_p>0: em vez de entrar no instante do evento, espera o preco
    devolver retrace_p pips (a partir do extremo do evento) num maximo de
    retrace_win_s segundos; entra nesse tick na direccao do trade.
    """
    stop_d = stop_p * PIP; take_d = take_p * PIP
    tstop_ms = (tstop_s * 1000) if tstop_s else None
    retrace_d = retrace_p * PIP
    retrace_ms = retrace_win_s * 1000
    trades = []
    pos_ate = -1
    n_skip = 0
    ev = ev.sort_values("t")
    t_ev_all = ev["t"].to_numpy()
    dir_all = ev["dir"].to_numpy()
    ask_e_all = ev["ask_e"].to_numpy()
    bid_e_all = ev["bid_e"].to_numpy()
    ok_a_all = ev["ok_a"].to_numpy()

    for k in range(len(ev)):
        t0 = int(t_ev_all[k])
        if t0 <= pos_ate:
            n_skip += 1
            continue
        d = -int(dir_all[k]) if fade else int(dir_all[k])

        # ---- entrada: instante do evento OU pullback de retrace_p ----
        if retrace_p > 0:
            e0 = int(np.searchsorted(ts_b, t0, side="left"))
            e0 = min(e0, len(ts_b) - 1)
            t_lim = min(t0 + retrace_ms, ts_b[-1])
            j1r = int(np.searchsorted(ts_b, t_lim, side="right"))
            seg = px_b[e0:j1r + 1]
            if len(seg) < 2:
                n_skip += 1; continue
            if retrace_mode == "extreme":
                # gatilho: devolucao de retrace_p a partir do EXTREMO corrido
                # (fade de compra->venda: maximo; fade de venda->compra: minimo)
                if d == 1:
                    ref = np.maximum.accumulate(seg)
                    hits = np.nonzero(seg <= ref - retrace_d)[0]
                else:
                    ref = np.minimum.accumulate(seg)
                    hits = np.nonzero(seg >= ref + retrace_d)[0]
            else:
                px_ref = float(px_b[e0])
                if d == 1:
                    hits = np.nonzero(seg <= px_ref - retrace_d)[0]
                else:
                    hits = np.nonzero(seg >= px_ref + retrace_d)[0]
            if not len(hits):
                n_skip += 1; continue
            jr = e0 + int(hits[0])
            t_in = int(ts_b[jr])
            if d == 1:
                ja_in, ok_in = ask_em(ts_a, px_a, np.array([t_in]))
                if not ok_in[0]:
                    n_skip += 1; continue
                entry = float(px_a[ja_in[0]])
            else:
                entry = float(px_b[jr])
        else:
            t_in = t0
            if d == 1:
                if not ok_a_all[k]:
                    n_skip += 1
                    continue
                entry = float(ask_e_all[k])
            else:
                entry = float(bid_e_all[k])

        if d == 1:
            sl = entry - stop_d; tp = entry + take_d
            side_ts, side_px = ts_b, px_b     # BUY sai no BID
        else:
            sl = entry + stop_d; tp = entry - take_d
            side_ts, side_px = ts_a, px_a     # SELL sai no ASK

        # janela de simulacao: da entrada ate t_in+tstop (ou +300s max)
        t_fim = t_in + (tstop_ms if tstop_ms else 300_000)
        j0 = int(np.searchsorted(side_ts, t_in, side="left"))
        j1 = int(np.searchsorted(side_ts, min(t_fim, side_ts[-1]), side="right"))
        path = side_px[j0:j1]
        if len(path) == 0:
            n_skip += 1
            continue
        hit = -1; motivo = "fim"; px_out = float(path[-1])
        if d == 1:
            below = np.nonzero(path <= sl)[0]
            above = np.nonzero(path >= tp)[0]
        else:
            below = np.nonzero(path >= sl)[0]
            above = np.nonzero(path <= tp)[0]
        ib = int(below[0]) if len(below) else 10**18
        ia = int(above[0]) if len(above) else 10**18
        if ib < ia:
            hit = ib; motivo = "sl"; px_out = float(min(sl, path[ib])) if d == 1 else float(max(sl, path[ib]))
        elif ia < 10**18:
            hit = ia; motivo = "tp"; px_out = float(tp)
        if motivo == "fim":
            px_out = float(path[-1])
        t_out = int(side_ts[j0 + hit]) if hit >= 0 else int(side_ts[j1 - 1])
        pips = (px_out - entry) / PIP if d == 1 else (entry - px_out) / PIP
        usd_gross = pips * USD_POR_PIP
        trades.append({"ano": ano, "t": t_in, "dir": d, "entry": entry,
                       "exit": px_out, "pips": pips, "usd_g": usd_gross,
                       "motivo": motivo, "t_out": t_out})
        pos_ate = t_out
    return trades, n_skip


def relatorio(trades, tag):
    if not trades:
        print(f"{tag}: 0 trades"); return
    df = pd.DataFrame(trades)
    n = len(df)
    dias = max((df.t_out.max() - df.t.min()) / 86400000, 1) if "t_out" in df else 1
    tp = (df.motivo == "tp").sum(); sl = (df.motivo == "sl").sum()
    gp = df.usd_g[df.usd_g > 0].sum(); gl = -df.usd_g[df.usd_g <= 0].sum()
    print(f"\n=== {tag} ===")
    print(f"trades={n} (~{n/dias:.1f}/dia) | tp={tp} sl={sl} fim={n-tp-sl} | "
          f"win={(df.pips>0).mean()*100:.1f}% | PF_gross={gp/max(gl,1e-9):.2f}")
    print(f"pips/trade medio={df.pips.mean():+.2f} | soma pips={df.pips.sum():+.0f}")
    for nome, com in COMISSAO.items():
        liq = df.usd_g.sum() - com * n
        print(f"  liquido {nome}: ${liq:+.2f} (${liq/n:+.3f}/trade) "
              f"= ${(liq/dias):+.2f}/dia")
    # por ano
    print("  por ano (usd_gross):")
    print(df.groupby("ano").usd_g.sum().round(2).to_string())

    # ---- daily account (UTC, exit day) — goal: never lose a day ----
    dia = (df.t_out // 86400000).astype(np.int64)
    dd = pd.DataFrame({"dia": dia, "usd_g": df.usd_g, "n": 1})
    g = dd.groupby("dia").agg(n=("n", "sum"), gross=("usd_g", "sum"))
    for nome, com in COMISSAO.items():
        liq_dia = g.gross - com * g.n
        perd = (liq_dia < 0).sum()
        print(f"  DIARIO {nome}: dias={len(liq_dia)} perdedores={perd} "
              f"({perd/len(liq_dia)*100:.0f}%) | mediana=${liq_dia.median():+.2f} "
              f"pior=${liq_dia.min():+.2f} melhor=${liq_dia.max():+.2f} "
              f"| total=${liq_dia.sum():+.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=float, required=True)
    ap.add_argument("--W", type=int, required=True)
    ap.add_argument("--R", type=float, required=True)
    ap.add_argument("--stop", type=float, required=True)
    ap.add_argument("--take", type=float, required=True)
    ap.add_argument("--tstop", type=int, default=300)
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    ap.add_argument("--fade", action="store_true",
                    help="opera CONTRA o impulso (le fade_*.pkl)")
    ap.add_argument("--prefixo", default=None,
                    help="prefixo dos ficheiros de eventos (ex: ev2_streak_)")
    ap.add_argument("--spread_max", type=float, default=None)
    ap.add_argument("--pct_min", type=float, default=None)
    ap.add_argument("--h_from", type=int, default=None)
    ap.add_argument("--h_to", type=int, default=None)
    ap.add_argument("--dt_min", type=float, default=None,
                    help="segundos minimos desde o impulso anterior")
    ap.add_argument("--imp_min", type=float, default=None)
    ap.add_argument("--imp_max", type=float, default=None)
    ap.add_argument("--rng_min", type=float, default=None)
    ap.add_argument("--rng_max", type=float, default=None)
    ap.add_argument("--tick_min", type=float, default=None)
    ap.add_argument("--retrace", type=float, default=0.0,
                    help="pips de devolucao p/ entrar (pullback no impulso)")
    ap.add_argument("--retrace_win", type=int, default=60,
                    help="segundos maximos à espera do pullback")
    ap.add_argument("--retrace_mode", choices=["event", "extreme"],
                    default="event",
                    help="event=devolve X do preco do evento; "
                         "extreme=devolve X do extremo corrido (climax)")
    ap.add_argument("--dump", default=None,
                    help="grava trades num pkl (para mapas de condicao)")
    args = ap.parse_args()

    ev = carrega_eventos(args.K, args.W, args.R, args.anos, fade=args.fade,
                         prefixo=args.prefixo)
    if args.anos:
        ev = ev[ev.ano.isin(args.anos)]
    ev = aplica_filtros(ev, args)
    anos = sorted(ev.ano.unique())
    print(f"eventos combo K={args.K} W={args.W} R={args.R}: {len(ev)} "
          f"em {len(anos)} anos; stop={args.stop} take={args.take} tstop={args.tstop}s")

    todos, skips = [], 0
    for ano in anos:
        zb = np.load(os.path.join(BIN, f"BID_{ano}.npz")); za = np.load(os.path.join(BIN, f"ASK_{ano}.npz"))
        ts_b, px_b, ts_a, px_a = zb["ts"], zb["px"], za["ts"], za["px"]
        zb.close(); za.close()
        eva = ev[ev.ano == ano]
        tr, sk = simula_ano(ano, eva, ts_b, px_b, ts_a, px_a,
                            args.stop, args.take, args.tstop, fade=args.fade,
                            retrace_p=args.retrace,
                            retrace_win_s=args.retrace_win,
                            retrace_mode=args.retrace_mode)
        todos.extend(tr); skips += sk
        del ts_b, px_b, ts_a, px_a
        print(f"  {ano}: {len(tr)} trades ({sk} saltados)", flush=True)
    relatorio(todos, f"K{args.K} W{args.W} R{args.R} {'FADE ' if args.fade else ''}"
                     f"SL{args.stop} TP{args.take} TS{args.tstop}"
                     + (f" RET{args.retrace}/{args.retrace_win}s/{args.retrace_mode}"
                        if args.retrace else ""))
    print(f"eventos saltados (posicao aberta): {skips}")
    if args.dump and todos:
        tdf = pd.DataFrame(todos)
        tdf.to_pickle(args.dump)
        print(f"trades gravados -> {args.dump}")


if __name__ == "__main__":
    main()
