#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure: volatility is predictable, direction is not.

Part A (docs/regime-detection.md): daily ATR14 -> next-day range
Spearman correlation, overall and by sub-period; high- vs low-vol day
range ratio; yesterday's range added on top of the 20d mean.

Part B: intraday morning range (00-12 UTC) -> NY window range
(12-16 UTC) Spearman + quintile table, on M15 bars.

Run from the repo root:  python code/measure_volatility_persistence.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurusd_research.bars import load_tf, hour_utc  # noqa: E402

PIP = 0.0001
DAY_MS = 86_400_000


def spearman(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 30:
        return float("nan")
    return float(pd.Series(x[ok]).rank().corr(pd.Series(y[ok]).rank()))


def part_daily():
    d = load_tf("D1")
    c, h, l = d["c"], d["h"], d["l"]
    rng = (h - l) / PIP
    # Wilder ATR14 on true range
    tr = np.maximum(h[1:] - l[1:],
                    np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1]))) / PIP
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    atr = np.concatenate([[np.nan], atr])
    y_rng = np.roll(rng, -1)  # next day's range
    y_rng[-1] = np.nan
    ok = np.isfinite(atr) & np.isfinite(y_rng)
    yrs = pd.to_datetime(d["t"], unit="ms", utc=True).year.to_numpy()
    print("== A1. atr14 -> next-day range (Spearman) ==")
    print(f"all      r={spearman(atr[ok], y_rng[ok]):+.3f}  n={ok.sum()}")
    for a, b_, tag in [(1999, 2009, "1999-2009"), (2010, 2019, "2010-2019"),
                       (2020, 2027, "2020-2026")]:
        m = ok & (yrs >= a) & (yrs < b_)
        print(f"{tag}  r={spearman(atr[m], y_rng[m]):+.3f}  n={m.sum()}")
    # high vs low vol days
    q = np.nanquantile(atr[ok], [0.2, 0.8])
    lo = ok & (atr <= q[0]); hi = ok & (atr >= q[1])
    print(f"low-vol day range={np.nanmedian(rng[lo]):.0f} pips   "
          f"high-vol={np.nanmedian(rng[hi]):.0f} pips   "
          f"ratio={np.nanmedian(rng[hi])/np.nanmedian(rng[lo]):.2f}x")
    # atr14 alone vs atr14 + yesterday's range
    yest = np.roll(rng, 1); yest[0] = np.nan
    m20 = pd.Series(rng).rolling(20).mean().to_numpy()
    base = spearman(atr[ok], y_rng[ok])
    comb = spearman(np.column_stack([atr[ok], yest[ok]]).mean(1) * 0 +
                    atr[ok] + 0 * yest[ok], y_rng[ok])  # atr only baseline
    # partial: residual of y_rng on m20, correlate atr+yest residual
    def resid(v, x):
        A = np.vstack([np.ones_like(x), x]).T
        beta, *_ = np.linalg.lstsq(A[np.isfinite(x) & np.isfinite(v)],
                                   v[np.isfinite(x) & np.isfinite(v)], rcond=None)
        r = v - (beta[0] + beta[1] * x)
        return r
    r_y = resid(y_rng, m20); r_f = resid(atr + yest, m20)
    mok = np.isfinite(r_y) & np.isfinite(r_f)
    print(f"atr14 alone r={base:+.3f}   atr14+yesterday (vs 20d mean) "
          f"partial r={spearman(r_f[mok], r_y[mok]):+.3f}")


def part_intraday():
    b = load_tf("M15", since_ms=1420070400000)  # 2015+
    t = b["t"]
    hr = hour_utc(t)
    day = t // DAY_MS
    # true session range = max(high)-min(low) within the window
    df = pd.DataFrame({"day": day, "hr": hr, "h": b["h"], "l": b["l"]})

    def sess_range(mask):
        g = df[mask].groupby("day").agg(h=("h", "max"), l=("l", "min"))
        return ((g.h - g.l) / PIP).rename("rng")

    morn = sess_range((df.hr >= 0) & (df.hr < 12))
    win = sess_range((df.hr >= 12) & (df.hr < 16))
    # yesterday's full-day range from D1 bars (max high - min low per day)
    d = load_tf("D1", since_ms=1420070400000)
    dday = d["t"] // DAY_MS
    dd = pd.DataFrame({"day": dday, "h": d["h"], "l": d["l"]}) \
        .groupby("day").agg(h=("h", "max"), l=("l", "min"))
    yest = ((dd.h - dd.l) / PIP).rename("yest")
    j = pd.concat([morn, win, yest], axis=1).dropna()
    j.columns = ["morn", "win", "yest"]
    j = j[(j.morn > 0) & (j.win > 0) & (j.yest > 0)]
    print("\n== A2. morning range (00-12 UTC) -> 12-16 UTC window ==")
    print(f"spearman morn->win  r={spearman(j.morn.to_numpy(), j.win.to_numpy()):+.3f}  "
          f"days={len(j)}")
    print(f"spearman yest->win  r={spearman(j.yest.to_numpy(), j.win.to_numpy()):+.3f}")
    qs = pd.qcut(j.morn, 5, labels=False, duplicates="drop")
    for q in sorted(qs.unique()):
        sel = j[qs == q]
        print(f"Q{q+1}: morn_rng {sel.morn.mean():5.1f} pips -> "
              f"window {sel.win.mean():5.1f} pips (n={len(sel)})")


if __name__ == "__main__":
    part_daily()
    part_intraday()
