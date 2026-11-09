"""Tick file loading for the cTrader .npz format.

Each year has two files: ``BID_<year>.npz`` and ``ASK_<year>.npz`` with
columns ``ts`` (int64 ms, UTC) and ``px`` (float64). Produced by
tick-replay's downloader/converter pipeline.
"""

import os
from pathlib import Path

import numpy as np

from .paths import ticks_bin


def tick_years(bin_dir=None):
    d = Path(bin_dir) if bin_dir else ticks_bin()
    return sorted(int(f[4:8]) for f in os.listdir(d)
                  if f.startswith("BID_") and f.endswith(".npz"))


def load_side(year, side="BID", bin_dir=None):
    """-> (ts int64 ms, px float64) for one year/side."""
    d = Path(bin_dir) if bin_dir else ticks_bin()
    z = np.load(d / f"{side}_{year}.npz")
    return z["ts"], z["px"]


def load_year(year, bin_dir=None):
    """-> dict(ts_b, px_b, ts_a, px_a) for one year."""
    d = Path(bin_dir) if bin_dir else ticks_bin()
    zb = np.load(d / f"BID_{year}.npz")
    za = np.load(d / f"ASK_{year}.npz")
    return {"ts_b": zb["ts"], "px_b": zb["px"],
            "ts_a": za["ts"], "px_a": za["px"]}
