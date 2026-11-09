#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Impulse displacement detector on EURUSD real cTrader ticks.

Detects "waves": displacement >= K pips in <= W seconds (BID),
re-armed by an R-pip retrace (or 1h timeout). For each impulse records
~42 features + negotiable forward outcomes at horizons H.

Outcome convention (pips, signed by impulse direction; commission NOT
included):
  BUY : out_h = bid(t+H) - ask(t)
  SELL: out_h = bid(t)   - ask(t+H)

Usage:
  python extract_impulse_events.py --anos 2019
  python extract_impulse_events.py --K 3 4 --W 30 --R 2
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
OUT = str(impulso_dir())
PIP = 0.0001
HORIZONTES = [5, 15, 30, 60, 120, 300]          # segundos
H_MFE = [60, 300]                               # horizontes p/ MFE/MAE
TOL_GAP_MS = 20_000                             # horizon sem tick <=20s = NaN
TOL_SPR_MS = 5_000                              # ask de entrada <=5s do evento
TIMEOUT_REARM_MS = 3_600_000                    # re-arm forcado apos 1h


# ---------------------------------------------------------------------------
# deteccao de impulsos num ano (BID)
# ---------------------------------------------------------------------------
def detectar_impulsos(ts, px, K, W, R):
    """Devolve (idx_eventos, dirs, j_lag) — dirs +1=buy impulse, -1=sell."""
    Wms = W * 1000
    j = np.searchsorted(ts, ts - Wms, side="right") - 1
    valid = (j >= 0) & ((ts - ts[np.clip(j, 0, len(ts) - 1)]) <= Wms * 1.5)
    jj = np.clip(j, 0, len(ts) - 1)
    disp = (px - px[jj]) / PIP
    disp[~valid] = 0.0
    cand = np.nonzero(valid & (np.abs(disp) >= K))[0]
    if len(cand) == 0:
        return (np.array([], dtype=np.int64), np.array([], dtype=np.int8),
                np.array([], dtype=np.int64))

    Rp = R * PIP
    ev, dirs, ev_jlag = [], [], []
    ci = 0
    nc = len(cand)
    t_last = ts[-1]
    while ci < nc:
        c = int(cand[ci])
        d = 1 if disp[c] >= K else -1
        ev.append(c); dirs.append(d); ev_jlag.append(int(j[c]))
        # re-arm: primeiro tick apos c onde o preco recua R pips (contra d)
        #           ou timeout de 1h
        t_cap = ts[c] + TIMEOUT_REARM_MS
        j_end = int(np.searchsorted(ts, min(t_cap, t_last), side="right"))
        seg = px[c + 1:j_end]
        if len(seg):
            if d == 1:
                hits = np.nonzero(seg <= px[c] - Rp)[0]
            else:
                hits = np.nonzero(seg >= px[c] + Rp)[0]
            if len(hits):
                rearm = c + 1 + int(hits[0])
            else:
                rearm = j_end
        else:
            rearm = j_end
        ci = int(np.searchsorted(cand, rearm, side="left"))
    return (np.array(ev, dtype=np.int64), np.array(dirs, dtype=np.int8),
            np.array(ev_jlag, dtype=np.int64))


# ---------------------------------------------------------------------------
# extracao por evento (vetorizada onde possivel)
# ---------------------------------------------------------------------------
def ask_no_instante(ts_a, px_a, t_ms):
    """ask mais proximo de t_ms (vetorizado). Devolve (idx, valido<=5s)."""
    i0 = np.searchsorted(ts_a, t_ms, side="left")
    i0 = np.clip(i0, 1, len(ts_a) - 1)
    d_fwd = np.abs(ts_a[i0] - t_ms)
    d_bwd = np.abs(ts_a[i0 - 1] - t_ms)
    idx = np.where(d_bwd < d_fwd, i0 - 1, i0)
    return idx, np.abs(ts_a[idx] - t_ms) <= TOL_SPR_MS


def bid_em(ts_b, px_b, t_ms):
    """ultimo bid <= t_ms; valido se <=20s de distancia."""
    j = np.searchsorted(ts_b, t_ms, side="right") - 1
    ok = (j >= 0) & ((t_ms - ts_b[np.clip(j, 0, len(ts_b) - 1)]) <= TOL_GAP_MS)
    jj = np.clip(j, 0, len(ts_b) - 1)
    return jj, ok


def ask_em(ts_a, px_a, t_ms):
    j = np.searchsorted(ts_a, t_ms, side="right") - 1
    ok = (j >= 0) & ((t_ms - ts_a[np.clip(j, 0, len(ts_a) - 1)]) <= TOL_GAP_MS)
    jj = np.clip(j, 0, len(ts_a) - 1)
    return jj, ok


def extrair_eventos(ano, ts_b, px_b, ts_a, px_a, K, W, R):
    ev, dirs, jlag = detectar_impulsos(ts_b, px_b, K, W, R)
    if len(ev) == 0:
        return None
    return extrair_medidos(ano, ts_b, px_b, ts_a, px_a, ev, dirs, jlag,
                           K, W, R)


def extrair_medidos(ano, ts_b, px_b, ts_a, px_a, ev, dirs, jlag,
                    K, W, R):
    """Features + outcomes forward para eventos (ev=indices BID, dirs, jlag).
    Reutilizavel por outros detectores (mede_fluxo.py etc.)."""
    n = len(ev)
    t_ev = ts_b[ev]
    bid_e = px_b[ev]

    # ask de entrada (instante do evento)
    ia, ok_a = ask_no_instante(ts_a, px_a, t_ev)
    ask_e = px_a[ia]
    spread_e = (ask_e - bid_e) / PIP

    rows = {"ano": np.full(n, ano, np.int32), "K": np.full(n, K, np.float32),
            "W": np.full(n, W, np.int32), "R": np.full(n, R, np.float32),
            "t": t_ev.astype(np.int64), "dir": dirs.astype(np.int8),
            "bid_e": bid_e, "ask_e": ask_e, "spread_e": spread_e,
            "ok_a": ok_a}

    # ---- outcomes forward vetorizados ----
    for H in HORIZONTES:
        t_h = t_ev + H * 1000
        jb, okb = bid_em(ts_b, px_b, t_h)
        ja, oka = ask_em(ts_a, px_a, t_h)
        outb = (px_b[jb] - ask_e) / PIP
        outs = (bid_e - px_a[ja]) / PIP
        val = np.where(dirs == 1, outb, outs)
        # BUY precisa ask_entrada(ok_a) + bid_saida(okb); SELL so' ask_saida(oka)
        val[~np.where(dirs == 1, ok_a & okb, oka)] = np.nan
        rows[f"out{H}"] = val
        rows[f"okb{H}"] = okb; rows[f"oka{H}"] = oka
        # guarda indices p/ MFE/MAE depois
        if H == H_MFE[1]:
            rows["_jb_end"] = jb
            rows["_ja_end"] = ja
        if H == H_MFE[0]:
            rows["_jb_60"] = jb
            rows["_ja_60"] = ja

    # ---- MFE/MAE nos horizontes curtos (loop; slices) ----
    mfe = {h: np.full(n, np.nan) for h in H_MFE}
    mae = {h: np.full(n, np.nan) for h in H_MFE}
    for k in range(n):
        e = int(ev[k]); d = int(dirs[k])
        for h in H_MFE:
            if h == 60:
                jb, ja = int(rows["_jb_60"][k]), int(rows["_ja_60"][k])
            else:
                jb, ja = int(rows["_jb_end"][k]), int(rows["_ja_end"][k])
            if d == 1:
                path = px_b[e:jb + 1]
                if len(path):
                    mfe[h][k] = (path.max() - ask_e[k]) / PIP
                    mae[h][k] = (path.min() - ask_e[k]) / PIP
            else:
                path = px_a[ia[k]:ja + 1]
                if len(path):
                    mfe[h][k] = (bid_e[k] - path.min()) / PIP
                    mae[h][k] = (bid_e[k] - path.max()) / PIP
    for h in H_MFE:
        rows[f"mfe{h}"] = mfe[h]; rows[f"mae{h}"] = mae[h]

    # ---- features por evento (loop; slices curtos) ----
    n_ = n
    imp_size = np.zeros(n_); ticks_win = np.zeros(n_, np.int32)
    tick_rate = np.zeros(n_); pct_dir = np.zeros(n_)
    span_s = np.zeros(n_); rng300 = np.zeros(n_); dist_hi = np.zeros(n_)
    dist_lo = np.zeros(n_); gap_b = np.zeros(n_)
    t_s_ago = np.searchsorted(ts_b, t_ev - 300_000, side="left")
    for k in range(n_):
        e = int(ev[k]); jl = int(jlag[k]); d = int(dirs[k])
        seg = px_b[jl:e + 1]
        imp_size[k] = abs(px_b[e] - px_b[jl]) / PIP
        ticks_win[k] = e - jl + 1
        span_s[k] = (ts_b[e] - ts_b[jl]) / 1000.0
        if span_s[k] > 0:
            tick_rate[k] = ticks_win[k] / span_s[k]
        if len(seg) > 1:
            dif = np.diff(seg)
            if d == 1:
                pct_dir[k] = float(np.mean(dif > 0))
            else:
                pct_dir[k] = float(np.mean(dif < 0))
        s0 = int(t_s_ago[k])
        if s0 < e:
            w = px_b[s0:e + 1]
            lo = w.min(); hi = w.max()
            rng300[k] = (hi - lo) / PIP
            dist_hi[k] = (hi - px_b[e]) / PIP
            dist_lo[k] = (px_b[e] - lo) / PIP
        if e > 0:
            gap_b[k] = (ts_b[e] - ts_b[e - 1]) / 1000.0
    rows.update({"imp_size": imp_size, "ticks_win": ticks_win,
                 "tick_rate": tick_rate, "pct_dir": pct_dir, "span_s": span_s,
                 "rng300": rng300, "dist_hi": dist_hi, "dist_lo": dist_lo,
                 "gap_b": gap_b})

    # ---- features temporais ----
    tt = pd.to_datetime(t_ev, unit="ms", utc=True)
    rows["ano2"] = tt.year.to_numpy(); rows["mes"] = tt.month.to_numpy()
    rows["dia"] = tt.day.to_numpy(); rows["hora"] = tt.hour.to_numpy()
    rows["dow"] = tt.day_of_week.to_numpy()  # seg=0
    # clustering
    dt_ev = np.diff(t_ev) / 1000.0
    rows["dt_prev"] = np.concatenate([[np.nan], dt_ev])
    rows["dir_prev"] = np.concatenate([[0], dirs[:-1].astype(np.int8)])

    for k in ("_jb_end", "_ja_end", "_jb_60", "_ja_60"):
        del rows[k]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    ap.add_argument("--K", nargs="*", type=float, default=[2, 3, 4, 5, 8])
    ap.add_argument("--W", nargs="*", type=int, default=[10, 30, 60, 120])
    ap.add_argument("--R", nargs="*", type=float, default=[1.5, 3.0])
    ap.add_argument("--combos", nargs="*", default=None,
                    help="lista 'K,W,R' separada por espaco")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    if args.combos:
        combos = []
        for c in args.combos:
            k, w, r = c.split(",")
            combos.append((float(k), int(w), float(r)))
    else:
        combos = [(k, w, r) for k in args.K for w in args.W for r in args.R]

    if args.anos:
        anos = args.anos
    else:
        anos = sorted(int(f[4:8]) for f in os.listdir(BIN)
                      if f.startswith("BID_") and f.endswith(".npz"))
    print(f"anos={anos} combos={len(combos)} -> {OUT}", flush=True)

    partes = {c: [] for c in combos}
    for ano in anos:
        pb = os.path.join(BIN, f"BID_{ano}.npz")
        pa = os.path.join(BIN, f"ASK_{ano}.npz")
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"  {ano}: falta npz, skip"); continue
        zb = np.load(pb); za = np.load(pa)
        ts_b, px_b = zb["ts"], zb["px"]
        ts_a, px_a = za["ts"], za["px"]
        print(f"  {ano}: bid={len(ts_b)/1e6:.1f}M ask={len(ts_a)/1e6:.1f}M ticks", flush=True)
        zb.close(); za.close()
        for (K, W, R) in combos:
            df = extrair_eventos(ano, ts_b, px_b, ts_a, px_a, K, W, R)
            if df is not None and len(df):
                partes[(K, W, R)].append(df)
            print(f"    K={K} W={W} R={R}: {0 if df is None else len(df)} eventos", flush=True)
        del ts_b, px_b, ts_a, px_a

    for (K, W, R), lst in partes.items():
        if not lst:
            continue
        df = pd.concat(lst, ignore_index=True)
        nome = f"ev_K{K}_W{W}_R{R}.pkl"
        cam = os.path.join(OUT, nome)
        df.to_pickle(cam)
        n = len(df)
        dias = max(1, int(round((df['t'].max() - df['t'].min()) / 86400000)))
        print(f"{nome}: {n} eventos (~{n/dias:.1f}/dia) -> {cam}", flush=True)


if __name__ == "__main__":
    main()
