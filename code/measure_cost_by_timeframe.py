#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure: does the mean-reversion cost barrier fall with timeframe?

Rule (docs/market-facts.md section 1): a bar closing in the top/bottom
quartile of its own range is faded — enter against it at the next bar's
open, exit at that bar's close.

Two cost models are reported:
  - "net_spr": subtract the bar's measured spread (first tick of bar)
  - "net_0.2": subtract a flat 0.20 pip round trip — typical all-in cost
    at 0.01 lot on a raw-spread account (spread ~0.1-0.3 pip + commission)

Default period: 2021+ (recent low-spread era). Use --since 0 for the full
history — but note 1999-2005 spreads were 2-5 pips and dominate the mean.

Run from the repo root:  python code/measure_cost_by_timeframe.py
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurusd_research.bars import load_tf  # noqa: E402

PIP = 0.0001
TFS = ["M5", "M15", "M30", "H1", "H4", "D1"]
SINCE_2021_MS = 1609459200000


def reversal(bars, pip=PIP):
    """Fade-the-extreme rule -> gross, spread-cost and flat-cost arrays."""
    o, h, l, c, sp = bars["o"], bars["h"], bars["l"], bars["c"], bars["spread"]
    rng = h - l
    pos = np.where(rng > 0, (c - l) / np.where(rng > 0, rng, 1), 0.5)
    sig = (pos >= 0.75) | (pos <= 0.25)
    sig[:-1] &= np.isfinite(sp[1:])
    idx = np.nonzero(sig[:-1])[0]
    idx = idx[idx + 1 < len(c)]
    direction = np.where(pos[idx] >= 0.75, -1.0, 1.0)  # fade the extreme
    gross = direction * (c[idx + 1] - o[idx + 1]) / pip
    cost = sp[idx + 1] / pip
    m = np.isfinite(gross) & np.isfinite(cost)
    return gross[m], cost[m], rng[idx + 1][m] / pip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=SINCE_2021_MS,
                    help="start ms epoch (default 2021-01-01; 0 = all)")
    ap.add_argument("--cost", type=float, default=0.20,
                    help="flat round-trip cost in pips (default 0.20)")
    a = ap.parse_args()
    print(f"{'TF':4} {'trades':>8} {'gross':>7} {'net_spr':>8} "
          f"{'net_%.2f' % a.cost:>8} {'med_spr/rng':>11}")
    for tf in TFS:
        try:
            bars = load_tf(tf, since_ms=a.since or None)
        except FileNotFoundError:
            print(f"{tf:4}  (missing — export bars+spread to data/bars/{tf}/)")
            continue
        if len(bars["t"]) < 100:
            continue
        g, cost, rng1 = reversal(bars)
        if not len(g):
            continue
        net_spr = g - cost
        net_flat = g - a.cost
        ratio = 100.0 * np.median(cost) / np.median(rng1)
        print(f"{tf:4} {len(g):8d} {g.mean():+7.3f} {net_spr.mean():+8.3f} "
              f"{net_flat.mean():+8.3f} {ratio:10.1f}%")


if __name__ == "__main__":
    main()
