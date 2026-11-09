"""OHLCV bar loading and MT5 server-time -> UTC conversion.

Two bar sources exist in this project:

- ``data/bars/<TF>/<SYM>_<TF>_export.csv`` — MetaTrader 5 export.
  ``time`` is ``YYYY.MM.DD HH:MM`` in **server time** (Pepperstone:
  GMT+2 winter / GMT+3 summer, EU DST rules — see ``server_to_utc``).
  ``*_spread.csv`` carries the per-bar spread in price units
  (first tick of the bar).
- ``data/ctrader/<SYM>_<TF>_ctrader_<from>_<to>.csv`` — bars derived from
  cTrader ticks; ``time`` is already UTC (``YYYY.MM.DD HH:MM:SS``).

Weekday bars only: Saturday bars in the old MT5 history are weekend
leftovers (2–6 ticks) and are dropped, matching the original measurements.
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

WEEKDAYS_ONLY = True


def _ultimo_domingo(ano, mes):
    d = datetime(ano, mes, 31)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d


def _offset_utc(ts: datetime) -> int:
    """Server UTC offset for a server timestamp (Pepperstone MT5)."""
    for off in (3, 2):
        inst = ts - timedelta(hours=off)
        ini = _ultimo_domingo(inst.year, 3).replace(hour=1)
        fim = _ultimo_domingo(inst.year, 10).replace(hour=1)
        if ini <= inst < fim:
            return off
    return 2


def server_to_utc(ts: datetime) -> datetime:
    return ts - timedelta(hours=_offset_utc(ts))


def load_bars(csv_path, utc=True):
    """Yield (t_ms_utc, open, high, low, close) from an MT5 export CSV."""
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        rd = csv.reader(f)
        next(rd, None)
        for row in rd:
            if len(row) < 5:
                continue
            try:
                ts = datetime.strptime(row[0], "%Y.%m.%d %H:%M")
            except ValueError:
                continue
            if WEEKDAYS_ONLY and ts.weekday() >= 5:
                continue
            try:
                o, h, l, c = (float(row[1]), float(row[2]),
                              float(row[3]), float(row[4]))
            except ValueError:
                continue
            if utc:
                ts = server_to_utc(ts)
            yield int(ts.timestamp() * 1000), o, h, l, c


def load_bars_arrays(csv_path, utc=True):
    """bars CSV -> dict of numpy arrays {t,o,h,l,c} (t = ms epoch UTC)."""
    rows = list(load_bars(csv_path, utc=utc))
    if not rows:
        return {"t": np.array([], np.int64), "o": np.array([]),
                "h": np.array([]), "l": np.array([]), "c": np.array([])}
    a = np.array(rows, dtype=np.float64)
    return {"t": a[:, 0].astype(np.int64), "o": a[:, 1], "h": a[:, 2],
            "l": a[:, 3], "c": a[:, 4]}


def load_spread(csv_path):
    """Yield (t_ms_utc, spread_price) aligned to bar timestamps."""
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        rd = csv.reader(f)
        next(rd, None)
        for row in rd:
            if len(row) < 2:
                continue
            try:
                ts = datetime.strptime(row[0], "%Y.%m.%d %H:%M")
            except ValueError:
                continue
            if WEEKDAYS_ONLY and ts.weekday() >= 5:
                continue
            try:
                sp = float(row[1])
            except ValueError:
                continue
            yield int(server_to_utc(ts).timestamp() * 1000), sp


def load_spread_map(csv_path):
    """spread CSV -> dict {t_ms: spread_price}."""
    return dict(load_spread(csv_path))


def bars_path(tf_dir, sym="EURUSD", tf=None, suffix="export"):
    tf = tf or Path(tf_dir).name
    return Path(tf_dir) / f"{sym}_{tf}_{suffix}.csv"


def tf_dir(tf, sym="EURUSD"):
    """data/bars/<TF>/ for a timeframe like 'M15'."""
    from .paths import bars_dir
    return bars_dir() / tf


def load_tf(tf, sym="EURUSD", since_ms=None, until_ms=None):
    """Load one timeframe -> dict of numpy arrays.

    Returns {t,o,h,l,c,spread} where t is ms epoch UTC and spread is the
    per-bar spread in price units (NaN when the bar has no spread row).
    """
    d = tf_dir(tf, sym)
    bars = load_bars_arrays(bars_path(d, sym, tf, "export"), utc=True)
    sp = load_spread_map(bars_path(d, sym, tf, "spread"))
    spread = np.array([sp.get(int(t), np.nan) for t in bars["t"]])
    out = dict(bars)
    out["spread"] = spread
    if since_ms is not None or until_ms is not None:
        m = np.ones(len(out["t"]), bool)
        if since_ms is not None:
            m &= out["t"] >= since_ms
        if until_ms is not None:
            m &= out["t"] < until_ms
        out = {k: v[m] for k, v in out.items()}
    return out


def hour_utc(t_ms):
    """UTC hour (float, e.g. 14.5) of each ms timestamp."""
    return (t_ms // 3_600_000 % 24) + (t_ms % 3_600_000) / 3_600_000.0
