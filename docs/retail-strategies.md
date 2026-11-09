# Retail strategies from YouTube — mechanically tested

Five popular retail strategies were transcribed into mechanical rules and
tested on real data. Source material was video summaries (some via AI
summaries); rules were implemented as literally as the summaries allowed.
All died. One was spectacularly alive — because of a bug (see
[case-study-lookahead.md](case-study-lookahead.md)).

| # | Strategy | Market/TF | Trades | Result | Verdict |
|---|---|---|---|---|---|
| 1 | Ryan Brown — "impulse + correction" elastic scalping (ADX + 7–10min impulse + snapback + TP 2–3 pips + grid/martingale averaging) | EURUSD M1, 2020–2026, 2.5M bars | — | After a qualified impulse price *reverts* (fade +0.14 to +0.60 pip), but expected trade value TP/SL ≈ **+0.08 to +0.29 pip — below the ~0.5 cost**. ADX doesn't help. The averaging grid is martingale: converts small edge into tail risk without creating edge | Dead |
| 2 | Pivot Points + MA200 + bearish engulfing + StochRSI (retail confluence classic) | EURUSD M15, 2019–2026 | ~0.1–0.3/week | 12 configs (zone P/R1/R2 × StochRSI OB70/80 × MA filters): **all negative**, win 28–43%, avg −0.13 to −2.02 pip gross | Dead |
| 3 | Kristina Forex "20 pips/day" (EMA20/50 M15 bias + FVG supply/demand zone M5 + TP 20 pips) | EURUSD M15/M5, 2019–2026 | 21,398 | win 19%, PF 0.66, **−1.80 pip/trade gross, −$62/month at 0.01**, negative every year | Dead |
| 4 | Pivot + EMA12 + RSI M5 + H4 trend filter (see case study) | EURUSD M5/M15, 2019–2026 | 1,251 | Reported +2.72 pip/trade — **100% lookahead artifact**; corrected: −0.35 pip/trade, −$195 net, 30 param variants all negative | Dead (audit) |
| 5 | Box Theory "gringos" (fade pre-market box halves, claim 84% win / 884% in 5 months) | EURUSD M5 | 1,154 signals | All variants **−8 to −16 pips/trade, PF ~0.32, win 10–36%**. NY session breaks the box rather than respecting it; the 884% claim = 63-trade sample or unspecified pattern | Dead |

## The pattern

- **Confluence of popular indicators ≠ edge.** Pivots, MAs, StochRSI,
  engulfing, FVG zones — each is a repackaged way of saying "price was here
  before" or "momentum exists". At EURUSD's efficiency, none of it survives
  the spread.
- **Backtested-on-video profits rarely survive mechanical transcription.**
  Discretionary elements ("wait for confirmation", "read the context") are
  where the claimed edge usually lives — and where it can't be verified.
- **Grid/martingale averaging** appears in several of these and converts
  small negative edges into account-ending tails. Banned in this project.

## One caveat, honestly

These tests cover the *mechanical core* of each strategy. Discretionary
layers we could not transcribe (news filters, session judgment, manual
zone selection) are untested by definition — but they are also unverifiable,
which is the point: a strategy that only works with discretion cannot be
reproduced, audited, or trusted with capital.
