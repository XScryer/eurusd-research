#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test: shipped D1 bars load and have sane shape."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from eurusd_research.bars import load_tf  # noqa: E402


def test_d1_loads():
    b = load_tf("D1")
    assert len(b["t"]) > 5000
    assert (b["h"] >= b["l"]).all()
    assert b["c"].min() > 0.5 and b["c"].max() < 2.0  # EURUSD sane range


def test_spread_aligned():
    import numpy as np
    b = load_tf("D1")
    finite = b["spread"][np.isfinite(b["spread"])]
    assert len(finite) > 4000
    assert (finite > 0).all() and (finite < 0.01).all()


if __name__ == "__main__":
    test_d1_loads()
    test_spread_aligned()
    print("bars smoke test passed")
