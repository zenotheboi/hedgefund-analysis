"""Same-baseline Monte Carlo for the DEPLOYED long+lend book (2016-2019).

Model accuracy is held at a common baseline (90% and 80%) so the two other
sources of uncertainty are comparable:
  A. TRADE luck      -> bootstrap over deals (pooled over degraded books)
  B. ASSUMPTION luck -> MC over the 4 cost assumptions (borrow rate, utilization,
     post-catalyst borrow, impact), drawn independently (B1) and correlated via
     a Gaussian copula (B2, a shared liquidity-stress factor).

Also runs the correlated MC for the UN-HEDGED book so the hedge decision can be
compared as two distributions (not as a random variable).

The deployed book at accuracy `acc` = the names the MODEL calls success, drawn
from the FULL universe, so a misclassified true failure enters as a landmine.

Saves distribution figure + stats JSON.
"""
import sys, json, math
from dataclasses import replace
from collections import defaultdict, deque
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl

ev = pd.read_csv("data/processed/backtest_events.csv", parse_dates=["date"])
windows = json.load(open("data/processed/backtest_windows.json"))
kq = defaultdict(deque)
for k in sorted(windows, key=lambda s: int(s.rsplit("_", 1)[1])):
    tk, rest = k.split("_", 1)
    kq[(tk, rest.rsplit("_", 1)[0])].append(k)
ev = ev.reset_index(drop=True)
ev["key"] = [kq[(r.ticker, str(r.date.date()))].popleft()
             if kq[(r.ticker, str(r.date.date()))] else None for _, r in ev.iterrows()]
ev = ev[ev.key.notna()].copy()
sc = ev[ev.tier == "small"].sort_values("date").reset_index(drop=True)
sc = sc[(sc.date.dt.year >= 2016) & (sc.date.dt.year <= 2019)].reset_index(drop=True)

REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
CAP = 10.0; YEARS = 4; N_MC = 500; N_BOOT = 10000; BASELINES = [0.90, 0.80]
LOAD = {"borrow": +0.55, "util": -0.60, "postc": -0.35, "impact": +0.70}


def offset_to_date(a, o):
    return pd.Timestamp(np.busday_offset(a.date(), o, roll="forward"))


def deployed_book(acc, seed):
    e = sc.copy(); rng = np.random.default_rng(seed)
    fl = rng.random(len(e)) > acc
    e.loc[fl, "success"] = ~e.loc[fl, "success"].astype(bool)
    return e[e.success].sort_values("date").reset_index(drop=True)


def run(params, events, seed=0):
    e = events; marks = {}
    open_pos = []
    for _, r in e.iterrows():
        eoff, xoff = params.long_entry, params.long_exit         # long+lend only
        ed, xd = offset_to_date(r.date, eoff), offset_to_date(r.date, xoff)
        open_pos = [o for o in open_pos if o[0] > ed]
        gross = sum(o[1] for o in open_pos); tk = sum(o[1] for o in open_pos if o[2] == r.ticker)
        t = min(params.frac_per_position * params.capital0,
                params.per_ticker_cap * params.capital0 - tk,
                params.max_gross * params.capital0 - gross)
        if t <= 0:
            continue
        pnl = position_pnl(r.to_dict(), windows[r.key], t, params)
        open_pos.append((xd, t, r.ticker))
        prev = 0.0
        for off, cum in pnl["marks"]:
            d = offset_to_date(r.date, off); marks[d] = marks.get(d, 0.0) + (cum - prev); prev = cum
    if not marks:
        return pd.Series(dtype=float)
    idx = pd.date_range(min(marks), max(marks), freq="B")
    return params.capital0 + pd.Series({d: marks.get(d, 0.0) for d in idx}).cumsum()


def final_M(params, events, seed=0):
    eq = run(params, events, seed)
    return (eq.iloc[-1] / 1e6) if len(eq) else np.nan


def per_trade(params, e):
    open_pos, trades = [], []
    for _, r in e.iterrows():
        ed = offset_to_date(r.date, params.long_entry); xd = offset_to_date(r.date, params.long_exit)
        open_pos = [o for o in open_pos if o[0] > ed]
        gross = sum(o[1] for o in open_pos); tk = sum(o[1] for o in open_pos if o[2] == r.ticker)
        t = min(params.frac_per_position * params.capital0,
                params.per_ticker_cap * params.capital0 - tk,
                params.max_gross * params.capital0 - gross)
        if t <= 0:
            continue
        trades.append(position_pnl(r.to_dict(), windows[r.key], t, params)["total"])
        open_pos.append((xd, t, r.ticker))
    return np.array(trades)


def _phi(x):
    return 0.5 * (1 + np.vectorize(math.erf)(x / np.sqrt(2)))


def _tri(u, a, c, b):
    return np.where(u < (c - a) / (b - a), a + np.sqrt(u * (b - a) * (c - a)),
                    b - np.sqrt((1 - u) * (b - a) * (b - c)))


def params_from_u(pp, ub, uu, up, ui):
    return replace(pp, borrow_rate_annual=float(np.clip(_tri(ub, 0.25, 1.0, 2.5), 0.1, 3)),
                   utilization=float(0.2 + uu * 0.4), post_collapse_frac=float(0.05 + up * 0.2),
                   impact_bps=float(40 + ui * 110))


def bootstrap_at(acc, base, n_books=8, seed=1):
    pool, cnt = [], []
    for fs in range(n_books):
        tr = per_trade(base, deployed_book(acc, 1000 + fs)); pool.append(tr); cnt.append(len(tr))
    pool = np.concatenate(pool); n = int(round(np.mean(cnt))); rng = np.random.default_rng(seed)
    return np.array([(CAP * 1e6 + rng.choice(pool, n, replace=True).sum()) / 1e6 for _ in range(N_BOOT)])


def mc_indep(acc, base, N=N_MC, seed=7):
    rng = np.random.default_rng(seed)
    return np.array([final_M(params_from_u(base, rng.random(), rng.random(), rng.random(), rng.random()),
                             deployed_book(acc, i), i) for i in range(N)])


def mc_corr(acc, base, N=N_MC, seed=11):
    rng = np.random.default_rng(seed); s = rng.standard_normal(N)
    def u(load):
        return _phi(load * s + np.sqrt(1 - load ** 2) * rng.standard_normal(N))
    ub, uu, up, ui = u(LOAD["borrow"]), u(LOAD["util"]), u(LOAD["postc"]), u(LOAD["impact"])
    return np.array([final_M(params_from_u(base, ub[i], uu[i], up[i], ui[i]), deployed_book(acc, i), i)
                     for i in range(N)])


def stats(f):
    c = (np.maximum(f, 1e-6) / CAP) ** (1 / YEARS) - 1
    return {"median": float(np.median(f)), "p5": float(np.percentile(f, 5)),
            "p95": float(np.percentile(f, 95)), "cagr_med": float(np.median(c)),
            "p_loss": float((f < CAP).mean())}


HEDGED = REAL
UNHEDGED = replace(REAL, hedge=False)
res, runs = {}, {}
for acc in BASELINES:
    k = f"acc_{int(acc*100)}"
    boot = bootstrap_at(acc, HEDGED); ind = mc_indep(acc, HEDGED); cor = mc_corr(acc, HEDGED)
    cor_unh = mc_corr(acc, UNHEDGED)
    runs[k] = {"bootstrap": boot, "mc_indep": ind, "mc_corr": cor, "mc_corr_unhedged": cor_unh}
    res[k] = {n: stats(v) for n, v in runs[k].items()}
    print(f"\n=== baseline {int(acc*100)}% (long+lend) ===")
    for n in ["bootstrap", "mc_indep", "mc_corr", "mc_corr_unhedged"]:
        v = res[k][n]
        print(f"  {n:18} median ${v['median']:5.1f}M  90%CI[${v['p5']:5.1f},${v['p95']:5.1f}]  P(loss) {v['p_loss']*100:4.1f}%")

json.dump(res, open("data/processed/backtest_montecarlo.json", "w"), indent=2)

fig, axes = plt.subplots(len(BASELINES), 1, figsize=(11, 8), sharex=True)
bins = np.linspace(5, 45, 45)
for ax, acc in zip(axes, BASELINES):
    d = runs[f"acc_{int(acc*100)}"]
    # density=True so all four are comparable despite different sample counts
    # (bootstrap N=10000 vs MC N=500) -- otherwise the bootstrap dwarfs the rest.
    ax.hist(d["bootstrap"], bins=bins, density=True, color="#3a7d44", alpha=0.35, label=f"A. trade luck (bootstrap, N={N_BOOT})")
    ax.hist(d["mc_indep"], bins=bins, density=True, histtype="step", color="#9aa0a6", lw=1.6, label=f"B1. assumptions independent (N={N_MC})")
    ax.hist(d["mc_corr"], bins=bins, density=True, color="#d0803b", alpha=0.5, label=f"B2. assumptions correlated (hedged, N={N_MC})")
    ax.hist(d["mc_corr_unhedged"], bins=bins, density=True, histtype="step", color="#7048e8", lw=1.8, label=f"B2 correlated, UN-hedged (N={N_MC})")
    for arr, col in [(d["bootstrap"], "#3a7d44"), (d["mc_corr"], "#d0803b")]:
        ax.axvline(np.median(arr), color=col, lw=2); ax.axvline(np.percentile(arr, 5), color=col, lw=1, ls="--")
    ax.axvline(CAP, color="#c0392f", lw=1.4, label="break-even ($10M)")
    ax.set_ylabel("Probability density"); ax.set_title(f"Baseline model accuracy fixed at {int(acc*100)}% (long+lend)", fontsize=12)
    if acc == BASELINES[0]:
        ax.legend(fontsize=10, loc="upper right")
axes[-1].set_xlabel("Final equity ($M, 10M start).  Solid=median, dashed=5th pct.  Purple outline = un-hedged.", fontsize=11)
fig.suptitle("Same-baseline MC (long+lend): trade vs assumption luck, hedged vs un-hedged, at 90% and 80%", y=0.995)
plt.tight_layout(); fig.savefig("reports/backtest_montecarlo.png", dpi=95, bbox_inches="tight"); plt.close(fig)
import base64
open("reports/backtest_montecarlo_b64.txt", "w").write(
    base64.b64encode(open("reports/backtest_montecarlo.png", "rb").read()).decode())
print("\nwrote backtest_montecarlo.json + backtest_montecarlo.png")
