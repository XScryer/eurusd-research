#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure: a big isolated M30 bar is exhaustion, not continuation.

For M30 bars with range >= MIN_PIPS inside the liquid window
(07:00-19:59 UTC), since 2015 (docs/market-facts.md section 3):

- does the NEXT bar contract? (range[i+1] < range[i])
- how much of the big bar's range is given back within 3 bars?
- does price continue in the bar's direction?

Run from the repo root:  python code/measure_bar_exhaustion.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurusd_research.bars import load_tf, hour_utc  # noqa: E402

PIP = 0.0001
MIN_PIPS = 14.0
SINCE_2015_MS = 1420070400000  # 2015-01-01 UTC


def main():
    b = load_tf("M30", since_ms=SINCE_2015_MS)
    t, o, h, l, c = b["t"], b["o"], b["h"], b["l"], b["c"]
    hr = hour_utc(t)
    liquid = (hr >= 7) & (hr < 20)
    rng = (h - l) / PIP
    big = liquid & (rng >= MIN_PIPS)
    # "isolated": previous bar is smaller than the big bar
    iso = np.zeros(len(t), bool)
    iso[1:] = rng[1:] > rng[:-1]
    big &= iso
    idx = np.nonzero(big[:-3])[0]
    idx = idx[(idx + 3) < len(t)]

    print(f"M30 bars >= {MIN_PIPS:.0f} pips in 07-20 UTC since 2015: {len(idx)}")
    print(f"{'range':>10} {'n':>6} {'next<bar':>9} {'retrace':>9} {'same_dir':>9}")
    for lo, hi in [(14, 20), (20, 30), (30, 10_000)]:
        sel = idx[(rng[idx] >= lo) & (rng[idx] < hi)]
        if not len(sel):
            continue
        r0 = rng[sel]
        nxt = rng[sel + 1]
        contract = np.mean(nxt < r0)
        d = np.sign(c[sel] - o[sel])
        retrace = np.full(len(sel), np.nan)  # close-based retrace of range
        cont = np.zeros(len(sel), bool)
        for k, i in enumerate(sel):
            # extreme reached in the bar's direction over i..i+3
            if d[k] > 0:
                ext = np.max(h[i:i + 4])
                retrace[k] = (ext - c[i + 3]) / PIP / r0[k]
            else:
                ext = np.min(l[i:i + 4])
                retrace[k] = (c[i + 3] - ext) / PIP / r0[k]
            cont[k] = (c[i + 3] - c[i]) * d[k] > 0
        print(f"{lo:>4}-{hi if hi<9999 else 'inf':>5} {len(sel):6d} "
              f"{100*contract:8.1f}% {100*np.nanmean(retrace):9.1f}% "
              f"{100*np.mean(cont):8.1f}%")
    print("cols: next<bar = next bar smaller; retrace = mean fraction of the")
    print("big bar's range given back by the close 3 bars later; same_dir =")
    print("close 3 bars later still in the bar's direction")


if __name__ == "__main__":
    main()
