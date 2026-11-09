"""Market regime classifier — the project's "opinion" module.

For each CLOSED bar, says which state the market is in:

    opin[i] ==  2  confirmed UP run    -> blocks fades (reversal entries)
    opin[i] ==  3  confirmed DOWN run  -> blocks fades
    opin[i] ==  1  confirmed RANGE     -> dead/choppy market
    opin[i] == -1  NO OPINION (transition/ambiguous) -> default: trade

CAUSALITY GUARANTEE: opin[i] uses ONLY bars with index <= i (all already
closed). It never reads a future bar. The "pers" consensus looks BACKWARD
(bars i-pers+1..i), never forward.

HOW TO USE (the "book"):

    import numpy as np
    from eurusd_research.regime_opinion import opiniao_regime

    # bars: numpy dict with keys "o","h","l","c" (price arrays)
    opin = opiniao_regime(bars)                 # validated parameters
    # opin is an int8 array of the same length as bars["c"]

Parameters (all optional; defaults = validated quilate_regK config for
EURUSD M15):

    K        analysis window in bars            (12 = 3h on M15)
    net_min  minimum net move in pips           (10.0)
    er_hi    min efficiency for a run           (0.45)
    er_lo    max ER for range                   (0.25)
    rng_max  max range in pips for range        (25.0)
    pers     consecutive bars agreeing          (6)
    pip      instrument pip size                (0.0001 EURUSD; US500=1.0 pt)

Definitions (all in pips, computed on closes):
    net[i]  = close[i] - close[i-K]          (net move over K bars)
    path[i] = sum |close[j]-close[j-1]|     (total distance, j=i-K+1..i)
    er[i]   = |net[i]| / path[i]             (0=sawtooth, 1=straight line)
    rng[i]  = max(high)-min(low) over K bars

Raw label per bar i (needs i >= K):
    RUN_UP  if net >= +net_min  and er >= er_hi
    RUN_DN  if net <= -net_min  and er >= er_hi
    RANGE   if er <= er_lo      and rng <= rng_max
    (else: no opinion)

Final opinion: only exists if the last `pers` bars ALL carry the same
label — backward consensus. Otherwise -1.

VALIDATION (see docs/regime-detection.md):
    - Causal by construction; verified identical to the reference
      implementation; future-perturbation audit shows zero lookahead.
    - Gate on a fade-style EURUSD M15 strategy (real cTrader ticks):
      2015-19 OOS -$60->-$52; 2020-24 -$60->-$8.7 (PF 0.75->0.95);
      2025-26 +$108->+$137 (PF 1.90->3.25). Total 11.8y: -$12 -> +$76.
    - During run states ~100% of that strategy's trades are counter-trend.
    - Run frequency ~6-7% of bars in the 14-18h UTC window, stable
      2014-2026 — the filter depends on price structure, not the year.

HONEST LIMITATIONS:
    - Measures RECENT activity/direction, does not predict the future.
    - A run is only confirmed after it has moved (inherent ~1-3h lag).
    - Reduces damage for fades; creates no edge in structureless markets.
    - Parameters were selected on EURUSD M15 — for another instrument or
      timeframe re-validate (start by scaling net_min/rng_max to the
      timeframe's typical range).
"""

import numpy as np
import pandas as pd


def opiniao_regime(b, K=12, net_min=10.0, er_hi=0.45, er_lo=0.25,
                   rng_max=25.0, pers=6, pip=0.0001):
    """Return int8 array with the regime opinion per bar (causal).

    b: dict with "o","h","l","c" (float arrays, price) — "t0" unused.
    """
    pc = np.asarray(b["c"], dtype=np.float64) / pip
    ph = np.asarray(b["h"], dtype=np.float64) / pip
    pl = np.asarray(b["l"], dtype=np.float64) / pip
    n = len(pc)

    net = np.full(n, np.nan)
    net[K:] = pc[K:] - pc[:-K]
    d1 = np.abs(np.diff(pc, prepend=pc[0]))
    pre = np.concatenate([[0.0], np.cumsum(d1)])
    path = np.full(n, np.nan)
    path[K:] = pre[K + 1:] - pre[1:n - K + 1]
    er = np.abs(net) / np.where(path == 0, np.nan, path)
    rng = (pd.Series(ph).rolling(K).max()
           - pd.Series(pl).rolling(K).min()).to_numpy()

    raw = np.full(n, -1, dtype=np.int8)
    raw[(er <= er_lo) & (rng <= rng_max)] = 1
    raw[(net >= net_min) & (er >= er_hi)] = 2
    raw[(net <= -net_min) & (er >= er_hi)] = 3

    # backward consensus: `pers` consecutive bars with the same label
    opin = np.full(n, -1, dtype=np.int8)
    for v in (1, 2, 3):
        m = (raw == v).astype(np.int32)
        cs = np.concatenate([[0], np.cumsum(m)])
        ok = (cs[pers:] - cs[:-pers]) == pers
        opin[np.where(ok)[0] + pers - 1] = v
    return opin


# human-readable state names
ROTULOS = {-1: "NO_OPINION", 1: "RANGE", 2: "RUN_UP", 3: "RUN_DOWN"}
