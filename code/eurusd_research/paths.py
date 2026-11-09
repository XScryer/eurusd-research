"""Data path resolution.

Layout expected under the data root (default ``<repo>/data``, override with
``EURUSD_DATA_DIR``):

    data/
      bars/           OHLCV CSVs per timeframe (MT5 export format)
      ctrader/        cTrader-derived bar CSVs (UTC)
      ticks_bin/      BID_<year>.npz / ASK_<year>.npz  (override:
                      EURUSD_TICKS_BIN — e.g. produced by tick-replay)
      results/        measurement outputs cited by the docs
      impulso/        scalping event pickles (ev_*.pkl, fade_*.pkl, ...)

Nothing here downloads data — see the repo README for the tick pipeline.
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
CODE_DIR = PACKAGE_DIR.parent
REPO_ROOT = CODE_DIR.parent


def data_root() -> Path:
    env = os.environ.get("EURUSD_DATA_DIR")
    return Path(env) if env else REPO_ROOT / "data"


def ticks_bin() -> Path:
    env = os.environ.get("EURUSD_TICKS_BIN")
    return Path(env) if env else data_root() / "ticks_bin"


def bars_dir() -> Path:
    return data_root() / "bars"


def ctrader_bars_dir() -> Path:
    return data_root() / "ctrader"


def results_dir() -> Path:
    return data_root() / "results"


def impulso_dir() -> Path:
    """Scalping event/simulation pickles (the ev_*.pkl family)."""
    return data_root() / "impulso"


def candles_dir() -> Path:
    return data_root() / "candle"


def legs_dir() -> Path:
    return data_root() / "pernadas"


def ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
