# Measure candle microstructure: on <=5min candles with a reasonable body,
# does price revert at the START and/or END of the candle?
#
# For each candle (M1=60s, M5=300s, clock-aligned like real ones):
#   - open, high, low, close of BID
#   - body = |close-open| in pips; wicks = high-max(o,c), min(o,c)-low
#   - trajectory: price at the 1st tick of each decile of the candle life
#     (p0..p9) + close
# Saved per year to data/candle/<TF>_<year>.pkl for analysis.
#
# "Reasonable body" filter applied in analysis: body>=BMIN pips and
# total wicks <= WMAX% of range (range = high-low).
import os
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

BIN = str(ticks_bin())
OUT = str(candles_dir())
os.makedirs(OUT, exist_ok=True)
PIP = 0.0001

DURS = {"M1": 60_000, "M5": 300_000}
NDEC = 10  # deciis


def candles_ano(ano, dur):
    z = np.load(os.path.join(BIN, "BID_%d.npz" % ano))
    ts = z["ts"].astype(np.int64)
    px = z["px"].astype(np.float64)
    cid = ts // dur
    start = cid * dur
    frac = (ts - start) / dur
    dec = np.minimum((frac * NDEC).astype(np.int64), NDEC - 1)

    df = pd.DataFrame({"cid": cid, "dec": dec, "px": px})
    # preco do 1o tick de cada decil + OHLC
    g = df.groupby(["cid", "dec"], sort=False)["px"].first().unstack()
    g.columns = ["p%d" % i for i in range(NDEC)]
    ohlc = df.groupby("cid", sort=False)["px"].agg(
        ["first", "last", "max", "min"])
    ohlc.columns = ["open", "close", "high", "low"]
    ohlc["t"] = ohlc.index.to_numpy() * dur
    res = ohlc.join(g)
    res["ano"] = ano
    return res.reset_index(drop=True)


def main():
    for tf, dur in DURS.items():
        for ano in range(2019, 2027):
            fp = os.path.join(BIN, "BID_%d.npz" % ano)
            if not os.path.exists(fp):
                continue
            dest = os.path.join(OUT, "%s_%d.pkl" % (tf, ano))
            if os.path.exists(dest):
                continue
            df = candles_ano(ano, dur)
            df.to_pickle(dest)
            print("%s %d: %d candles" % (tf, ano, len(df)), flush=True)
            del df


if __name__ == "__main__":
    main()
