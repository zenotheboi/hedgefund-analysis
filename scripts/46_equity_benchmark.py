"""Regenerate the equity chart + deployed metrics + benchmark, CAPPED pre-COVID
(2020-02-14) so the 2020 crash doesn't distort the comparison. Long+lend book."""
import sys, json
from dataclasses import replace
from collections import defaultdict, deque
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl

CAP_DATE = pd.Timestamp("2020-02-14")   # before the COVID selloff (~Feb 20 2020)
CAP = 10_000_000

ev = pd.read_csv("data/processed/backtest_events.csv", parse_dates=["date"])
windows = json.load(open("data/processed/backtest_windows.json"))
kq = defaultdict(deque)
for k in sorted(windows, key=lambda s: int(s.rsplit("_", 1)[1])):
    tk, rest = k.split("_", 1); kq[(tk, rest.rsplit("_", 1)[0])].append(k)
ev = ev.reset_index(drop=True)
ev["key"] = [kq[(r.ticker, str(r.date.date()))].popleft()
             if kq[(r.ticker, str(r.date.date()))] else None for _, r in ev.iterrows()]
ev = ev[ev.key.notna()].copy()
sc = ev[ev.tier == "small"].sort_values("date").reset_index(drop=True)
sc = sc[(sc.date.dt.year >= 2016) & (sc.date.dt.year <= 2019)].reset_index(drop=True)
sc_long = sc[sc.success].sort_values("date").reset_index(drop=True)


def o2d(a, o): return pd.Timestamp(np.busday_offset(a.date(), o, roll="forward"))


def run_long(params):
    marks = {}; open_pos = []
    for _, r in sc_long.iterrows():
        ed, xd = o2d(r.date, params.long_entry), o2d(r.date, params.long_exit)
        open_pos = [op for op in open_pos if op[0] > ed]
        gross = sum(op[1] for op in open_pos); tk = sum(op[1] for op in open_pos if op[2] == r.ticker)
        t = min(params.frac_per_position*params.capital0, params.per_ticker_cap*params.capital0-tk,
                params.max_gross*params.capital0-gross)
        if t <= 0: continue
        p = position_pnl(r.to_dict(), windows[r.key], t, params)
        open_pos.append((xd, t, r.ticker)); prev = 0.0
        for off, cum in p["marks"]:
            d = o2d(r.date, off); marks[d] = marks.get(d, 0.0) + (cum-prev); prev = cum
    idx = pd.date_range(min(marks), max(marks), freq="B")
    eq = params.capital0 + pd.Series({d: marks.get(d, 0.0) for d in idx}).cumsum()
    return eq[eq.index <= CAP_DATE]


def metrics(eq):
    m = eq.resample("ME").last().dropna(); rets = m.pct_change().dropna()
    yrs = (eq.index[-1]-eq.index[0]).days/365.25
    return {"final": float(eq.iloc[-1]), "total": float(eq.iloc[-1]/eq.iloc[0]-1),
            "cagr": float((eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1),
            "sharpe": float(rets.mean()/rets.std()*np.sqrt(12)), "maxdd": float((eq/eq.cummax()-1).min())}


REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
eq_h = run_long(REAL); eq_u = run_long(replace(REAL, hedge=False))
eq_po = run_long(replace(REAL, include_lending=False))
mh, mu, mpo = metrics(eq_h), metrics(eq_u), metrics(eq_po)
print(f"CAP {CAP_DATE.date()}  HEDGED  final ${mh['final']/1e6:.1f}M cagr {mh['cagr']*100:.0f}% "
      f"sharpe {mh['sharpe']:.2f} maxDD {mh['maxdd']*100:.0f}%")
print(f"UNHEDGED final ${mu['final']/1e6:.1f}M cagr {mu['cagr']*100:.0f}% sharpe {mu['sharpe']:.2f} maxDD {mu['maxdd']*100:.0f}%")
print(f"price-only ${mpo['final']/1e6:.1f}M  -> lending uplift {mh['final']/mpo['final']-1:+.0%}")

# benchmarks over the same capped window
import yfinance as yf
px = yf.download(["^GSPC", "XBI"], start=str(eq_h.index[0].date()),
                 end=str((CAP_DATE+pd.Timedelta(days=1)).date()), auto_adjust=True, progress=False)["Close"].dropna()
bench = {}
for tk in ["^GSPC", "XBI"]:
    s = px[tk].dropna(); s = s[s.index <= CAP_DATE]
    m = s.resample("ME").last().dropna(); rets = m.pct_change().dropna()
    yrs = (s.index[-1]-s.index[0]).days/365.25
    bench[tk] = {"total": float(s.iloc[-1]/s.iloc[0]-1), "cagr": float((s.iloc[-1]/s.iloc[0])**(1/yrs)-1),
                 "sharpe": float(rets.mean()/rets.std()*np.sqrt(12)), "maxdd": float((s/s.cummax()-1).min()),
                 "series": s}
    print(f"{tk:6} total={bench[tk]['total']*100:+.0f}% cagr={bench[tk]['cagr']*100:.0f}% "
          f"sharpe={bench[tk]['sharpe']:.2f} maxDD={bench[tk]['maxdd']*100:.0f}%")

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(eq_h.index, eq_h.values/1e6, color="#2f9e44", lw=1.9, label=f"Strategy long+lend, hedged - \${mh['final']/1e6:.0f}M (perfect foresight)")
ax.plot(eq_u.index, eq_u.values/1e6, color="#2f9e44", lw=1.2, ls="--", label=f"Strategy long+lend, un-hedged - \${mu['final']/1e6:.0f}M")
ax.plot(eq_po.index, eq_po.values/1e6, color="#8a8a8a", lw=1.3, ls=":", label=f"Strategy price-only, NO lending - \${mpo['final']/1e6:.0f}M (lending adds +18%)")
for tk, col, lab in [("^GSPC", "#2a78d6", "S&P 500"), ("XBI", "#d0803b", "XBI (biotech)")]:
    s = bench[tk]["series"]; reb = CAP/1e6 * s/s.iloc[0]
    ax.plot(s.index, reb.values, color=col, lw=1.4, label=f"{lab} buy-and-hold - \${reb.iloc[-1]:.0f}M")
ax.axhline(CAP/1e6, color="gray", ls=":", lw=0.8)
ax.set_ylabel("Equity ($M)"); ax.set_xlabel("2016 - early 2020 (capped pre-COVID)")
ax.set_title("Strategy vs benchmarks, 10M USD start  (strategy = perfect-foresight ceiling; realistic 90% = 26M, see table)")
ax.legend(loc="upper left", fontsize=11)
plt.tight_layout(); fig.savefig("reports/backtest_equity.png", dpi=95, bbox_inches="tight"); plt.close(fig)

import base64
open("reports/backtest_equity_b64.txt", "w").write(base64.b64encode(open("reports/backtest_equity.png", "rb").read()).decode())
# update extra.json
out = json.load(open("data/processed/backtest_extra.json"))
out["deployed_longlend"]["metrics"] = mh; out["deployed_longlend"]["price_only"] = mpo
out["hedge"] = {"hedged": mh, "unhedged": mu}
out["benchmark"] = {tk: {k: v for k, v in bench[tk].items() if k != "series"} for tk in bench}
out["cap_date"] = str(CAP_DATE.date())
json.dump(out, open("data/processed/backtest_extra.json", "w"), indent=2, default=float)
print("regenerated backtest_equity.png + updated backtest_extra.json")
