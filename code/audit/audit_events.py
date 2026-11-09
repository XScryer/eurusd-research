# -*- coding: utf-8 -*-
"""AUDIT — parameterized vectorized event generator for
Pivot+EMA12+RSI M5.

h4_mode : buggy=in-progress H4 bar FINAL close (lookahead ~4h)
          fixed=last COMPLETED H4 bar before the M5 signal close
          cur  =current price vs EMA20 of completed H4 bars
piv_mode: buggy=pv[j-1] (2 days ago) / fixed=pv[j] (prev day) /
          full=pivot from last FULL session day
mode    : normal|invert|rand|lagK
"""
import os
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eurusd_research.paths import (ticks_bin, impulso_dir, candles_dir,
    legs_dir, ctrader_bars_dir, bars_dir, results_dir, data_root)

PIP = 0.0001
f1 = str(ctrader_bars_dir() / "EURUSD_M1_ctrader_2020-01-01_2026-10-22.csv")

P = dict(h4_mode="buggy", piv_mode="buggy", zone=12.0,
         rsi_l=(30.0,55.0), rsi_s=(45.0,70.0),
         dist_min=15.0, dist_max=100.0, risk_min=3.0, risk_max=40.0,
         tp_ratio=1.7, mode="normal", lag=0)

_base = None
def load_base():
    global _base
    if _base is not None: return _base
    m1 = pd.read_csv(f1, parse_dates=["time"]).set_index("time").sort_index()
    m5 = m1.resample("5min").agg(o=("open","first"), h=("high","max"),
                                 l=("low","min"), c=("close","last")).dropna()
    h4 = m1.resample("4h").agg(c=("close","last")).dropna()
    h4e = h4.c.ewm(span=20, adjust=False).mean()
    c5 = m5.c.to_numpy(); n5=len(m5)
    ema12 = pd.Series(c5).ewm(span=12, adjust=False).mean().to_numpy()
    dc = np.diff(c5, prepend=c5[0])
    g = np.where(dc>0,dc,0.); ls = np.where(dc<0,-dc,0.)
    w=14; a=np.empty(n5); a[:w]=np.nan; a[w-1]=g[:w].sum()
    for i in range(w,n5): a[i]=a[i-1]-a[i-1]/w+g[i]
    ag=a.copy(); a2=np.empty(n5); a2[:w]=np.nan; a2[w-1]=ls[:w].sum()
    for i in range(w,n5): a2[i]=a2[i-1]-a2[i-1]/w+ls[i]
    al=a2
    rsi = 100-100/(1+ag/np.where(al==0,1e-9,al))
    _base = dict(m5=m5,h4=h4,h4e=h4e,c5=c5,h5=m5.h.to_numpy(),l5=m5.l.to_numpy(),
                 n5=n5,ema12=ema12,rsi=rsi,index=m5.index)
    return _base

def build_pivots_h4(B, P):
    m5=B["m5"]; n5=B["n5"]; c5=B["c5"]
    dd = m5.resample("1D").agg(h=("h","max"), l=("l","min"), c=("c","last")).dropna()
    ph,pl,pc = dd.h.shift(1), dd.l.shift(1), dd.c.shift(1)
    pv=((ph+pl+pc)/3).to_numpy(); r1=(2*pv-pl).to_numpy(); s1=(2*pv-ph).to_numpy()
    r2=(pv+(ph-pl)).to_numpy(); s2=(pv-(ph-pl)).to_numpy()
    days = dd.index.normalize().to_numpy()
    tnorm = m5.index.normalize().to_numpy()
    j = np.searchsorted(days, tnorm, side="left")
    okday = (j < len(days)) & (days[np.minimum(j,len(days)-1)] == tnorm)
    jj = np.where(okday, j, -1)
    if P["piv_mode"]=="full":
        # pivot do dia anterior COM sessão completa (>=150 barras M5 ~ 12.5h)
        cnt = m5.resample("1D").size().reindex(dd.index).fillna(0).to_numpy()
        full = cnt>=150
        pf = np.full(len(dd),-1); last=-1
        for a in range(len(dd)):
            pf[a]=last
            if full[a]: last=a
        okf = pf>=0
        ss = np.clip(pf,0,len(dd)-1)
        H=dd.h.to_numpy();L=dd.l.to_numpy();C=dd.c.to_numpy()
        Pv=(H[ss]+L[ss]+C[ss])/3; R1=2*Pv-L[ss]; S1=2*Pv-H[ss]
        R2=Pv+(H[ss]-L[ss]); S2=Pv-(H[ss]-L[ss])
        pvf=np.where(okf,Pv,np.nan); r1f=np.where(okf,R1,np.nan)
        s1f=np.where(okf,S1,np.nan); s2f=np.where(okf,S2,np.nan)
        r2f=np.where(okf,R2,np.nan)
        valid = jj>=0
        kk = np.clip(jj,0,len(dd)-1)
        pivv=np.where(valid,pvf[kk],np.nan); r1v=np.where(valid,r1f[kk],np.nan)
        s1v=np.where(valid,s1f[kk],np.nan); s2v=np.where(valid,s2f[kk],np.nan)
        r2v=np.where(valid,r2f[kk],np.nan)
    else:
        off = -1 if P["piv_mode"]=="buggy" else 0
        k = jj + off
        valid = (k>=0) & (k<len(dd))
        kk = np.clip(k,0,len(dd)-1)
        pivv=np.where(valid,pv[kk],np.nan); r1v=np.where(valid,r1[kk],np.nan)
        s1v=np.where(valid,s1[kk],np.nan); s2v=np.where(valid,s2[kk],np.nan)
        r2v=np.where(valid,r2[kk],np.nan)
    # H4
    h4=B["h4"]; h4e=B["h4e"]; h4_times=h4.index.to_numpy()
    hc=h4.c.to_numpy(); he=h4e.to_numpy()
    h4_up=np.zeros(n5,bool); h4_dn=np.zeros(n5,bool)
    if P["h4_mode"]=="buggy":
        jj2 = np.searchsorted(h4_times, m5.index.to_numpy(), side="right")-1
        okh = jj2>=25
        jh = np.clip(jj2,0,len(h4)-1)
        up = hc[jh]>he[jh]
        h4_up[okh & up]=True; h4_dn[okh & ~up]=True
    elif P["h4_mode"]=="cur":
        # causal alternativo: preco actual (close M5) vs EMA20 das H4 FECHADAS
        h4_fim = (h4.index+pd.Timedelta(hours=4)).to_numpy()
        tc = m5.index.to_numpy()+np.timedelta64(5,"m")
        jj2 = np.searchsorted(h4_fim, tc, side="right")-1
        okh = jj2>=25
        jh = np.clip(jj2,0,len(h4)-1)
        up = c5 > he[jh]
        h4_up[okh & up]=True; h4_dn[okh & ~up]=True
    else:
        # 'fixed': ultima barra H4 COMPLETED no fecho do sinal M5 (t+5min)
        h4_fim = (h4.index+pd.Timedelta(hours=4)).to_numpy()
        tc = m5.index.to_numpy()+np.timedelta64(5,"m")
        jj2 = np.searchsorted(h4_fim, tc, side="right")-1
        okh = jj2>=25
        jh = np.clip(jj2,0,len(h4)-1)
        up = hc[jh]>he[jh]
        h4_up[okh & up]=True; h4_dn[okh & ~up]=True
    return dict(pivv=pivv,r1v=r1v,s1v=s1v,s2v=s2v,r2v=r2v,h4_up=h4_up,h4_dn=h4_dn)

def gen_events(B, A, P):
    c5=B["c5"]; h5=B["h5"]; l5=B["l5"]; n5=B["n5"]
    ema12=B["ema12"]; rsi=B["rsi"]; idx=B["index"]
    pivv=A["pivv"];r1v=A["r1v"];s1v=A["s1v"];s2v=A["s2v"];r2v=A["r2v"]
    h4_up=A["h4_up"];h4_dn=A["h4_dn"]
    zone=P["zone"]*PIP; rmin=P["risk_min"]*PIP; rmax=P["risk_max"]*PIP
    tpR=P["tp_ratio"]; lag=P["lag"]; mode=P["mode"]

    cross_up=np.zeros(n5,bool); cross_dn=np.zeros(n5,bool)
    cross_up[1:]=(c5[:-1]<=ema12[:-1])&(c5[1:]>ema12[1:])
    cross_dn[1:]=(c5[:-1]>=ema12[:-1])&(c5[1:]>-1e18)&(c5[1:]<ema12[1:])
    warm=(np.arange(n5)>=300)&(np.arange(n5)<n5-60)

    def prep(d):
        if d==1:
            cands=np.vstack([s1v,pivv,s2v])
            trig=h4_up&cross_up&(rsi>P["rsi_l"][0])&(rsi<P["rsi_l"][1])
        else:
            cands=np.vstack([r1v,pivv,r2v])
            trig=h4_dn&cross_dn&(rsi>P["rsi_s"][0])&(rsi<P["rsi_s"][1])
        cn=~np.isnan(cands)
        near=((np.abs(c5[None,:]-cands)<=zone)&cn).any(axis=0)
        if d==1:
            bm=(cands<c5[None,:]-2*PIP)&cn
            bv=np.where(bm,cands,-np.inf); mx=bv.max(axis=0)
            sl=np.where(np.isfinite(mx),mx-2*PIP,np.nan)
        else:
            am=(cands>c5[None,:]+2*PIP)&cn
            av=np.where(am,cands,np.inf); mn=av.min(axis=0)
            sl=np.where(np.isfinite(mn),mn+2*PIP,np.nan)
        risk=np.abs(c5-sl)
        ok=trig&near&warm&(risk>=rmin)&(risk<=rmax)&~np.isnan(sl)
        # filtro distancia (usa r1,p,s1 - igual p/ os dois lados, como o original)
        dk=~(np.isnan(pivv)|np.isnan(r1v)|np.isnan(s1v))
        d1=np.abs(r1v-pivv)/PIP; d2=np.abs(pivv-s1v)/PIP
        dok=dk&((np.minimum(d1,d2)>=P["dist_min"])&(np.maximum(d1,d2)<=P["dist_max"]))
        # original: so aplica o filtro quando NAO ha nan; se ha nan -> nao filtra
        ok=ok&(~dk|dok)
        return ok,sl

    okL,slL=prep(1); okS,slS=prep(-1)
    stat=okL|okS

    trades=[]; rng=np.random.default_rng(7)
    i=300
    while i<n5-60:
        if not stat[i]: i+=1; continue
        if okL[i]: d=1
        elif okS[i]: d=-1
        else: i+=1; continue
        if mode=="invert": d=-d
        elif mode=="rand": d=int(rng.choice([-1,1]))
        sl = slL[i] if d==1 else slS[i]
        if np.isnan(sl):
            cands=[s1v[i],pivv[i],s2v[i]] if d==1 else [r1v[i],pivv[i],r2v[i]]
            cn=[z for z in cands if not np.isnan(z)]
            if d==1:
                below=[z for z in cn if z<c5[i]-2*PIP]
                if not below: i+=1; continue
                sl=max(below)-2*PIP
            else:
                above=[z for z in cn if z>c5[i]+2*PIP]
                if not above: i+=1; continue
                sl=min(above)+2*PIP
        ie=min(i+lag,n5-1)
        ent=c5[ie]; risk=abs(ent-sl)
        if risk<1e-12: i+=1; continue
        tp=ent+d*tpR*risk
        j=ie+1; motivo="fim"; lim=min(ie+200,n5)
        px=c5[min(ie+200,n5-1)]
        while j<lim:
            if d==1:
                if l5[j]<=sl: motivo="sl"; px=min(sl,l5[j]); break
                if h5[j]>=tp: motivo="tp"; px=tp; break
            else:
                if h5[j]>=sl: motivo="sl"; px=max(sl,h5[j]); break
                if l5[j]<=tp: motivo="tp"; px=tp; break
            j+=1
        pips=(px-ent)/PIP*d
        trades.append({"t":idx[i],"t_ent":idx[min(ie+1,n5-1)],"dir":d,"pips":pips,
                       "motivo":motivo,"sl":sl,"ent_bar":ent,"risk":risk/PIP,
                       "sig_i":int(i),"ent_i":int(ie),"exit_i":int(j)})
        i=j+3
    return pd.DataFrame(trades)

def summarize(df,nome):
    if not len(df): print(f"{nome}: 0 trades"); return df
    gp=df.pips[df.pips>0].sum(); gl=-df.pips[df.pips<=0].sum()
    tstat=df.pips.mean()/(df.pips.std()/np.sqrt(len(df))) if len(df)>1 else 0
    print(f"{nome}: n={len(df)} win={(df.pips>0).mean()*100:.1f}% "
          f"avg={df.pips.mean():+.2f} PF={gp/max(gl,1e-9):.2f} t={tstat:.1f} "
          f"net~{df.pips.mean()-0.6:+.2f}/tr (${(df.pips.mean()-0.6)*0.10*len(df):+.0f})")
    return df

if __name__=="__main__":
    nome=sys.argv[1] if len(sys.argv)>1 else "x"
    for a in sys.argv[2:]:
        k,v=a.split("=")
        if k in ("zone","dist_min","dist_max","risk_min","risk_max","tp_ratio","lag"):
            P[k]=float(v)
        elif k in ("h4_mode","piv_mode","mode"): P[k]=v
        elif k=="rsi_l": P[k]=tuple(float(x) for x in v.split(","))
        elif k=="rsi_s": P[k]=tuple(float(x) for x in v.split(","))
    B=load_base(); A=build_pivots_h4(B,P)
    df=gen_events(B,A,P)
    summarize(df,nome)
    df.to_pickle(str(impulso_dir() / "events_{nome}.pkl"))
    print("dump:",str(impulso_dir() / "events_{nome}.pkl"))
