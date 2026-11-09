#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure: multi-candle drops continue (docs/market-facts.md section 4).

A "drop" = the largest close-to-close decline over any window of up to
DROP_BARS (4) consecutive H1 bars ending at bar i, inside the liquid
window (07-14 UTC so the 6h horizon fits), since 2015. Events are counted
per bar (overlapping windows allowed — this matches the original count).

For each threshold: number of events and the median move over the next
6 hours (6 H1 bars), plus the baseline for all liquid bars.

NOTE: raw outcome measurement, not a trade simulation — see the doc's
caveat. Run: python code/measure_drop_continuation.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurusd_research.bars import load_tf, hour_utc  # noqa: E402

PIP = 0.0001
DROP_BARS = 4
HORIZON_BARS = 6  # 6h on H1
SINCE_2015_MS = 1420070400000
THRESHOLDS = [50, 60, 70, 80, 90]


def main():
    b = load_tf("H1", since_ms=SINCE_2015_MS)
    t, c = b["t"], b["c"] / PIP
    hr = hour_utc(t)
    n = len(c)
    drop = np.full(n, -np.inf)
    for k in range(1, DROP_BARS + 1):
        dk = np.full(n, -np.inf)
        dk[k:] = c[:-k] - c[k:]
        drop = np.maximum(drop, dk)
    ok_h = np.arange(n) + HORIZON_BARS < n
    fut = np.full(n, np.nan)
    fut[ok_h] = c[np.arange(n)[ok_h] + HORIZON_BARS] - c[ok_h]
    liq = (hr >= 7) & (hr < 14) & ok_h

    print(f"H1 drops >= threshold within {DROP_BARS} bars, 07-14 UTC, 2015+")
    print(f"{'drop>=':>7} {'cases':>6} {'next6h_med':>11} {'retr>50%':>9}")
    for lo in THRESHOLDS:
        sel = liq & (drop >= lo)
        # retrace = fraction of the drop recovered by the +6h close
        retr = np.clip(fut[sel] / np.maximum(drop[sel], 1e-9), 0, 1)
        print(f"{lo:>7} {int(sel.sum()):6d} {np.nanmedian(fut[sel]):+10.1f} "
              f"{100*np.nanmean(retr>0.5):8.1f}%")
    sel = liq
    retr = np.clip(fut[sel] / np.maximum(drop[sel], 1e-9), 0, 1)
    print(f"{'base':>7} {int(sel.sum()):6d} {np.nanmedian(fut[sel]):+10.1f} "
          f"{100*np.nanmean(retr>0.5):8.1f}%")


if __name__ == "__main__":
    main()
