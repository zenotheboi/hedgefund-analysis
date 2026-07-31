"""Monte Carlo robustness for the realistic backtest (2016-2019):
  1. Bootstrap over trades  -> trade-selection luck (how much depends on which
     deals you happened to get).
  2. MC over the assumptions -> draw borrow rate, utilization, post-collapse,
     executability, cost, and model accuracy JOINTLY at random and re-run,
     for two accuracy bands (82-100% and 70-100%).

Saves a distribution figure + a stats JSON for the report.
"""
import sys, json
from dataclasses import replace
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl
exec(open("scripts/43_sensitivity.py").read().split("REAL = Params")[0])  # loads run/metrics/sc/windows

REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
CAP = 10.0  # $M start
YEARS = 4   # 2016-2019


def per_trade(params, e):
    rng = np.random.default_rng(0); unshort = set()
    if params.short_gate_mode == "worst_first":
        f = e[~e.success].sort_values("car_short")
        unshort = set(f.head(int(round((1 - params.short_executable_frac) * len(f)))).index)
    open_pos, trades = [], []
    for _, r in e.iterrows():
        is_long = bool(r.success)
        eoff = params.long_entry if is_long else params.short_entry
        xoff = params.long_exit if is_long else params.short_exit
        ed, xd = offset_to_date(r.date, eoff), offset_to_date(r.date, xoff)
        if not is_long and r.name in unshort:
            continue
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


def run_acc1(params, acc, seed):
    e2 = sc.copy(); rng = np.random.default_rng(seed)
    flip = rng.random(len(e2)) > acc
    e2.loc[flip, "success"] = ~e2.loc[flip, "success"].astype(bool)
    return metrics(run(params, events=e2.sort_values("date"), seed=seed))["final"] / 1e6


def mc_assumptions(acc_lo, acc_hi, N=600):
    rng = np.random.default_rng(7); out = []
    for i in range(N):
        p = replace(REAL,
            borrow_rate_annual=float(np.clip(rng.triangular(0.25, 1.0, 2.5), 0.1, 3)),
            utilization=float(rng.uniform(0.2, 0.6)),
            post_collapse_frac=float(rng.uniform(0.05, 0.25)),
            short_executable_frac=float(rng.uniform(0.4, 0.8)),
            impact_bps=float(rng.uniform(40, 150)))
        out.append(run_acc1(p, float(rng.uniform(acc_lo, acc_hi)), i))
    return np.array(out)


def stats(f):
    c = (f / CAP) ** (1 / YEARS) - 1
    return {"median": float(np.median(f)), "p5": float(np.percentile(f, 5)),
            "p95": float(np.percentile(f, 95)), "cagr_med": float(np.median(c)),
            "cagr_p5": float(np.percentile(c, 5)), "cagr_p95": float(np.percentile(c, 95)),
            "p_loss": float((f < CAP).mean()), "worst5": float(np.percentile(f, 5))}


# 1. bootstrap
tr = per_trade(REAL, sc)
rng = np.random.default_rng(1)
boot = np.array([(CAP * 1e6 + rng.choice(tr, len(tr), replace=True).sum()) / 1e6 for _ in range(10000)])
# 2. assumptions MC, two accuracy bands
mc_hi = mc_assumptions(0.82, 1.0)
mc_lo = mc_assumptions(0.70, 1.0)

res = {"bootstrap": stats(boot), "mc_acc_82_100": stats(mc_hi), "mc_acc_70_100": stats(mc_lo)}
json.dump(res, open("data/processed/backtest_montecarlo.json", "w"), indent=2)
for k, v in res.items():
    print(f"{k:16} median ${v['median']:.1f}M  90%CI[${v['p5']:.1f},${v['p95']:.1f}]  "
          f"CAGR {v['cagr_med']*100:.0f}%  P(loss) {v['p_loss']*100:.1f}%")

# ---- distribution figure: the two assumption-MC bands overlaid ----
fig, ax = plt.subplots(figsize=(11, 5))
bins = np.linspace(5, 45, 40)
ax.hist(mc_hi, bins=bins, color="#2a78d6", alpha=0.55, label="model accuracy 82-100% (avg 90%)")
ax.hist(mc_lo, bins=bins, color="#d0803b", alpha=0.55, label="model accuracy 70-100% (avg 85%)")
for arr, col in [(mc_hi, "#2a78d6"), (mc_lo, "#d0803b")]:
    ax.axvline(np.median(arr), color=col, lw=2, ls="-")
    ax.axvline(np.percentile(arr, 5), color=col, lw=1.2, ls="--")
ax.axvline(CAP, color="#c0392f", lw=1.5, label="break-even ($10M)")
ax.set_xlabel("Final equity in USD millions (from a 10M start).  Solid line = median, dashed = 5th percentile (bad-luck).")
ax.set_ylabel("Frequency (600 random draws each)")
ax.set_title("Monte Carlo over the assumptions - how model accuracy widens the downside")
ax.legend()
plt.tight_layout(); fig.savefig("reports/backtest_montecarlo.png", dpi=95, bbox_inches="tight"); plt.close(fig)
import base64
open("reports/backtest_montecarlo_b64.txt", "w").write(base64.b64encode(open("reports/backtest_montecarlo.png", "rb").read()).decode())
print("wrote reports/backtest_montecarlo.png + json")
