# -*- coding: utf-8 -*-
"""AUDIT — sensitivity grid + placebos on the CORRECTED version
(h4_mode=fixed, piv_mode=full). Everything causal.
"""
import sys, itertools
import numpy as np
import pandas as pd
import audit_events as E

B = E.load_base()

def run(nome, **kw):
    P = dict(E.P); P.update(kw)
    A = E.build_pivots_h4(B, P)
    df = E.gen_events(B, A, P)
    if not len(df):
        print(f"{nome}: 0 trades"); return None
    gp=df.pips[df.pips>0].sum(); gl=-df.pips[df.pips<=0].sum()
    tstat=df.pips.mean()/(df.pips.std()/np.sqrt(len(df)))
    print(f"{nome:34s} n={len(df):5d} win={(df.pips>0).mean()*100:4.1f}% "
          f"avg={df.pips.mean():+6.2f} PF={gp/max(gl,1e-9):.2f} t={tstat:+5.1f}")
    return df

print("=== SENSIBILIDADE (h4=fixed, piv=full) ===")
# zona
for z in (8,12,16,20):
    run(f"zone={z}", zone=z, h4_mode="fixed", piv_mode="full")
# tp ratio
for tp in (1.3,1.5,1.7,2.0,2.5):
    run(f"tp={tp}", tp_ratio=tp, h4_mode="fixed", piv_mode="full")
# risk range
for r in ((2,30),(3,40),(5,50),(3,25)):
    run(f"risk={r}", risk_min=r[0], risk_max=r[1], h4_mode="fixed", piv_mode="full")
# dist filter
for dm in (0,10,15,25):
    run(f"dist_min={dm}", dist_min=dm, h4_mode="fixed", piv_mode="full")
for dx in (60,100,150,999):
    run(f"dist_max={dx}", dist_max=dx, h4_mode="fixed", piv_mode="full")
# rsi bands
for rl in ((20,60),(30,55),(40,65),(30,70)):
    run(f"rsiL={rl}", rsi_l=rl, h4_mode="fixed", piv_mode="full")
for rs in ((30,80),(45,70),(50,75),(35,65)):
    run(f"rsiS={rs}", rsi_s=rs, h4_mode="fixed", piv_mode="full")
# combinações extremas
run("zone16+tp2.0", zone=16, tp_ratio=2.0, h4_mode="fixed", piv_mode="full")
run("zone8+tp1.5", zone=8, tp_ratio=1.5, h4_mode="fixed", piv_mode="full")
run("zone20+tp2.5+risk5-50", zone=20, tp_ratio=2.5, risk_min=5, risk_max=50,
    h4_mode="fixed", piv_mode="full")
run("sem_dist", dist_min=0, dist_max=999, h4_mode="fixed", piv_mode="full")

print("\n=== PLACEBOS (h4=fixed, piv=full) ===")
run("INVERT", mode="invert", h4_mode="fixed", piv_mode="full")
run("RAND",   mode="rand",   h4_mode="fixed", piv_mode="full")
run("LAG1",   mode="normal", lag=1, h4_mode="fixed", piv_mode="full")
run("LAG3",   mode="normal", lag=3, h4_mode="fixed", piv_mode="full")
# placebos tambem na versao BUGGY para comparar
print("\n=== PLACEBOS (buggy original) ===")
run("BUGGY_INVERT", mode="invert")
run("BUGGY_RAND",   mode="rand")
run("BUGGY_LAG3",   mode="normal", lag=3)
