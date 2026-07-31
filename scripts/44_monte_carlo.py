"""Monte Carlo robustness for the realistic backtest (2016-2019).

Three questions, kept clean by holding the DOMINANT driver (model accuracy)
constant so the others are comparable:

  A. TRADE luck        -> bootstrap over trades (which deals you happened to get)
  B. ASSUMPTION luck   -> MC over the 5 cost assumptions (borrow rate,
                          utilization, post-collapse, shortability, impact)
     B1. independent   -> each drawn on its own
     B2. correlated    -> drawn from a Gaussian copula so they CO-MOVE
                          (a stressed-liquidity regime makes borrow pricier,
                           utilization lower, shorting harder, costs higher all
                           at once) -- the realistic, wider-downside version.

All three are run at a COMMON accuracy baseline (90% and 80%) so trade-luck vs
assumption-luck sit on the same footing. Accuracy is the strongest single driver
-> it gets its own sweep in script 43, not blended in here.

A supplementary "full-risk" MC (accuracy ALSO random, correlated assumptions) is
kept at the end as the total-downside view.

Saves a distribution figure + a stats JSON for the report.
"""
import sys, json, math
from dataclasses import replace
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl
exec(open("scripts/43_sensitivity.py").read().split("REAL = Params")[0])  # run/metrics/sc/windows

REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
CAP = 10.0   # $M start
YEARS = 4    # 2016-2019
N_MC = 600
N_BOOT = 10000
BASELINES = [0.90, 0.80]

# ---- marginals for the 5 random cost assumptions -------------------------
#   borrow rate ~ triangular(0.25, 1.0, 2.5)  [clipped 0.1..3]
#   utilization ~ uniform(0.20, 0.60)
#   post-collapse ~ uniform(0.05, 0.25)
#   shortable   ~ uniform(0.40, 0.80)
#   impact bps  ~ uniform(40, 150)
# Correlated version: each variable loads on ONE latent "liquidity-stress"
# factor s (higher s = worse regime).  Signs reflect how each moves in stress:
#   borrow +  (pricier)   utilization -  (falls)   post-collapse -  (mild)
#   shortable - (harder)  impact +  (costlier).
# Single-factor loadings -> the implied correlation matrix is always valid (PSD).
LOAD = {"borrow": +0.55, "util": -0.60, "postc": -0.35, "shortx": -0.60, "impact": +0.70}


def _phi(x):                       # vectorized standard-normal CDF (no scipy)
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / np.sqrt(2.0)))


def _tri_ppf(u, a, c, b):          # inverse-CDF of triangular(a, mode=c, b)
    return np.where(u < (c - a) / (b - a),
                    a + np.sqrt(u * (b - a) * (c - a)),
                    b - np.sqrt((1.0 - u) * (b - a) * (b - c)))


def _params_from_uniforms(u_b, u_u, u_p, u_s, u_i):
    return dict(
        borrow_rate_annual=float(np.clip(_tri_ppf(u_b, 0.25, 1.0, 2.5), 0.1, 3.0)),
        utilization=float(0.20 + u_u * (0.60 - 0.20)),
        post_collapse_frac=float(0.05 + u_p * (0.25 - 0.05)),
        short_executable_frac=float(0.40 + u_s * (0.80 - 0.40)),
        impact_bps=float(40.0 + u_i * (150.0 - 40.0)))


def flip_labels(e, acc, seed):     # degrade the book to accuracy `acc`
    e2 = e.copy(); rng = np.random.default_rng(seed)
    flip = rng.random(len(e2)) > acc
    e2.loc[flip, "success"] = ~e2.loc[flip, "success"].astype(bool)
    return e2


def run_fixed_acc(params, acc, seed):
    e2 = flip_labels(sc, acc, seed)
    return metrics(run(params, events=e2.sort_values("date"), seed=seed))["final"] / 1e6


# ---- A. bootstrap over trades, at a fixed accuracy baseline --------------
def per_trade(params, e):
    unshort = set()
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


def bootstrap_at(acc, n_books=8, boot_seed=1):
    # Isolate PURE trade-selection luck: pool per-trade P&L over several
    # accuracy-`acc` books so the result does not hinge on one lucky/unlucky
    # draw of *which* labels are wrong (that mislabel draw is model luck, not
    # trade luck). Resample ~one book's worth of trades from the pool.
    pool, counts = [], []
    for fs in range(n_books):
        e = flip_labels(sc, acc, 1000 + fs)
        tr = per_trade(REAL, e)
        pool.append(tr); counts.append(len(tr))
    pool = np.concatenate(pool)
    n = int(round(np.mean(counts)))
    rng = np.random.default_rng(boot_seed)
    return np.array([(CAP * 1e6 + rng.choice(pool, n, replace=True).sum()) / 1e6
                     for _ in range(N_BOOT)])


# ---- B1. independent assumptions MC, fixed accuracy ----------------------
def mc_independent(acc, N=N_MC, seed=7):
    rng = np.random.default_rng(seed); out = []
    for i in range(N):
        p = replace(REAL, **_params_from_uniforms(
            rng.random(), rng.random(), rng.random(), rng.random(), rng.random()))
        out.append(run_fixed_acc(p, acc, i))
    return np.array(out)


# ---- B2. correlated (Gaussian copula) assumptions MC, fixed accuracy -----
def _copula_uniforms(rng, N):
    s = rng.standard_normal(N)                    # common liquidity-stress factor

    def unif(load):
        eps = rng.standard_normal(N)
        return _phi(load * s + np.sqrt(1.0 - load ** 2) * eps)   # correlated uniform

    return (unif(LOAD["borrow"]), unif(LOAD["util"]), unif(LOAD["postc"]),
            unif(LOAD["shortx"]), unif(LOAD["impact"]))


def mc_correlated(acc, N=N_MC, seed=11):
    rng = np.random.default_rng(seed)
    u_b, u_u, u_p, u_s, u_i = _copula_uniforms(rng, N)
    out = []
    for i in range(N):
        p = replace(REAL, **_params_from_uniforms(u_b[i], u_u[i], u_p[i], u_s[i], u_i[i]))
        out.append(run_fixed_acc(p, acc, i))
    return np.array(out)


def mc_fullrisk(acc_lo=0.70, acc_hi=1.0, N=N_MC, seed=23):
    """Supplementary: accuracy ALSO random + correlated assumptions -> total risk."""
    rng = np.random.default_rng(seed)
    u_b, u_u, u_p, u_s, u_i = _copula_uniforms(rng, N)
    out = []
    for i in range(N):
        p = replace(REAL, **_params_from_uniforms(u_b[i], u_u[i], u_p[i], u_s[i], u_i[i]))
        out.append(run_fixed_acc(p, float(rng.uniform(acc_lo, acc_hi)), i))
    return np.array(out)


def stats(f):
    c = (np.maximum(f, 1e-6) / CAP) ** (1 / YEARS) - 1
    return {"median": float(np.median(f)), "p5": float(np.percentile(f, 5)),
            "p95": float(np.percentile(f, 95)), "cagr_med": float(np.median(c)),
            "cagr_p5": float(np.percentile(c, 5)), "cagr_p95": float(np.percentile(c, 95)),
            "p_loss": float((f < CAP).mean())}


# ==========================================================================
res, runs = {}, {}
for acc in BASELINES:
    key = f"acc_{int(acc*100)}"
    boot, ind, cor = bootstrap_at(acc), mc_independent(acc), mc_correlated(acc)
    runs[key] = {"bootstrap": boot, "mc_indep": ind, "mc_corr": cor}
    res[key] = {"bootstrap": stats(boot), "mc_indep": stats(ind), "mc_corr": stats(cor)}
    print(f"\n=== baseline accuracy {int(acc*100)}% ===")
    for name in ["bootstrap", "mc_indep", "mc_corr"]:
        v = res[key][name]
        print(f"  {name:10} median ${v['median']:5.1f}M  90%CI[${v['p5']:5.1f},${v['p95']:5.1f}]  "
              f"CAGR {v['cagr_med']*100:4.0f}%  P(loss) {v['p_loss']*100:4.1f}%")

full = mc_fullrisk()
res["full_risk_acc70_100_corr"] = stats(full)
v = res["full_risk_acc70_100_corr"]
print(f"\nfull-risk (accuracy 70-100% random + correlated assumptions): "
      f"median ${v['median']:.1f}M  90%CI[${v['p5']:.1f},${v['p95']:.1f}]  P(loss) {v['p_loss']*100:.1f}%")

json.dump(res, open("data/processed/backtest_montecarlo.json", "w"), indent=2)

# ---- figure: one panel per baseline; bootstrap vs assumptions (indep + corr)
fig, axes = plt.subplots(len(BASELINES), 1, figsize=(11, 8), sharex=True)
bins = np.linspace(0, 40, 45)
for ax, acc in zip(axes, BASELINES):
    d = runs[f"acc_{int(acc*100)}"]
    ax.hist(d["bootstrap"], bins=bins, color="#3a7d44", alpha=0.55, label="A. trade luck (bootstrap)")
    ax.hist(d["mc_indep"], bins=bins, color="#9aa0a6", alpha=0.45, label="B1. assumption luck (independent)")
    ax.hist(d["mc_corr"], bins=bins, color="#d0803b", alpha=0.55, label="B2. assumption luck (correlated / copula)")
    for arr, col in [(d["bootstrap"], "#3a7d44"), (d["mc_corr"], "#d0803b")]:
        ax.axvline(np.median(arr), color=col, lw=2)
        ax.axvline(np.percentile(arr, 5), color=col, lw=1.1, ls="--")
    ax.axvline(CAP, color="#c0392f", lw=1.4, label="break-even ($10M)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Baseline model accuracy fixed at {int(acc*100)}%  "
                 f"(bootstrap N={N_BOOT}, assumptions N={N_MC})", fontsize=10)
    if acc == BASELINES[0]:
        ax.legend(fontsize=8, loc="upper right")
axes[-1].set_xlabel("Final equity in USD millions (10M start).  Solid = median, dashed = 5th pct (bad luck).  "
                    "Correlated (orange) shifts the downside left vs independent (grey).")
fig.suptitle("Same-baseline decomposition: trade luck vs assumption luck, at 90% and 80% accuracy", y=0.995)
plt.tight_layout(); fig.savefig("reports/backtest_montecarlo.png", dpi=95, bbox_inches="tight"); plt.close(fig)

import base64
open("reports/backtest_montecarlo_b64.txt", "w").write(
    base64.b64encode(open("reports/backtest_montecarlo.png", "rb").read()).decode())
print("\nwrote reports/backtest_montecarlo.png + data/processed/backtest_montecarlo.json")
