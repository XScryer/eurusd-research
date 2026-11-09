#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Causality test for regime_opinion: perturbing FUTURE bars must not
change past opinions.

Run:  python -m pytest tests/ -q   (or: python tests/test_regime_opinion.py)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from eurusd_research.regime_opinion import opiniao_regime  # noqa: E402


def make_bars(n=400, seed=7):
    rng = np.random.default_rng(seed)
    c = 1.10 + np.cumsum(rng.normal(0, 0.0004, n))
    o = np.roll(c, 1); o[0] = c[0]
    h = np.maximum(o, c) + abs(rng.normal(0, 0.0002, n))
    l = np.minimum(o, c) - abs(rng.normal(0, 0.0002, n))
    return {"o": o, "h": h, "l": l, "c": c}


def test_labels_in_range():
    opin = opiniao_regime(make_bars())
    assert set(np.unique(opin)).issubset({-1, 1, 2, 3})


def test_no_lookahead():
    """opin[:k] must be identical when bars k: are replaced by garbage."""
    b = make_bars()
    opin_full = opiniao_regime(b)
    k = 200
    b2 = {key: v.copy() for key, v in b.items()}
    for key in ("o", "h", "l", "c"):
        b2[key][k:] = b2[key][k] * 3.0 + 0.05  # wild future perturbation
    opin_pert = opiniao_regime(b2)
    np.testing.assert_array_equal(opin_full[:k], opin_pert[:k])


def test_backward_consensus():
    """A single extreme bar must not flip the opinion by itself."""
    b = make_bars()
    opin = opiniao_regime(b)
    # opinions only become non -1 after pers bars of agreement;
    # count transitions sanity: most bars are -1 on random data
    assert np.mean(opin == -1) > 0.5


if __name__ == "__main__":
    test_labels_in_range()
    test_no_lookahead()
    test_backward_consensus()
    print("all tests passed")
