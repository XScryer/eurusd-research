#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure: intraday volatility profile and the 12-16 UTC reversal pocket.

Part A (docs/market-facts.md section 2): median bar range and spread by UTC
hour on M30 bars; cost as % of range.

Part B: the same fade-the-extreme rule restricted to bars opening inside
12:00-16:00 UTC, since 2023 — gross/net pips, trades/day, cases.

Run from the repo root:  python code/measure_session_window.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurusd_research.bars import load_tf, hour_utc  # noqa: E402

PIP = 0.0001
SINCE_2023_MS = 1672531200000  # 2023-01-01 UTC


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else float("nan")


def reversal(bars, mask):
    o, h, l, c, sp = bars["o"], bars["h"], bars["l"], bars["c"], bars["spread"]
    rng = h - l
    pos = np.where(rng > 0, (c - l) / rng, 0.5)
    sig = ((pos >= 0.75) | (pos <= 0.25)) & mask
    sig[:-1] &= mask[1:] & np.isfinite(sp[1:])
    idx = np.nonzero(sig[:-1])[0]
    idx = idx[idx + 1 < len(c)]
    direction = np.where(pos[idx] >= 0.75, -1.0, 1.0)
    gross = direction * (c[idx + 1] - o[idx + 1]) / PIP
    cost = sp[idx + 1] / PIP
    return gross, gross - cost


def main():
    bars = load_tf("M30")
    t = bars["t"]
    hr = hour_utc(t)
    rng_p = (bars["h"] - bars["l"]) / PIP
    sp_p = bars["spread"] / PIP
    print("== A. median range / spread by UTC hour (M30, all history) ==")
    print(f"{'hour':>5} {'range':>7} {'spread':>7} {'cost%':>6}")
    for h in range(24):
        m = (hr >= h) & (hr < h + 1)
        if m.sum() < 50:
            continue
        r, s = med(rng_p[m]), med(sp_p[m])
        print(f"{h:5d} {r:7.1f} {s:7.2f} {100 * s / r:5.1f}%")

    print("\n== B. fade-the-extreme inside 12-16 UTC, since 2023 ==")
    since = t >= SINCE_2023_MS
    win = (hr >= 12) & (hr < 16)
    g, n = reversal(bars, since & win)
    ok = np.isfinite(n)
    g, n = g[ok], n[ok]
    days = len(np.unique(t[since & win] // 86_400_000))
    print(f"cases={len(n)}  days={days}  trades/day={len(n)/max(days,1):.2f}")
    print(f"gross={np.mean(g):+.3f} pip/trade")
    print(f"net (measured spread)={np.mean(n):+.3f}   "
          f"net (flat 0.20 pip)={np.mean(g)-0.20:+.3f} pip/trade")
    print(f"win rate(net>0, flat cost)={100*np.mean(g-0.20>0):.1f}%")


if __name__ == "__main__":
    main()
