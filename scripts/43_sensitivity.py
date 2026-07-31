"""Comprehensive sensitivity + bear/base/bull scenarios on the REALISTIC
backtest (borrow crashes post-catalyst, worst shorts un-borrowable).

- One-at-a-time sweep of every parameter that could plausibly change ->
  tornado chart (which assumption moves the result most).
- Explicit bear / base / bull combined scenarios (bad times vs good times).
- Regime breakdown ON the realistic case.

Reuses the position P&L from src/hedgefund/backtest.py; the sim loop is
duplicated here (small) so this runs standalone off the cached windows.
"""
import sys, json
from dataclasses import replace
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl

ev = pd.read_csv("data/processed/backtest_events.csv", parse_dates=["date"])
windows = json.load(open("data/processed/backtest_windows.json"))
from collections import defaultdict, deque
key_queue = defaultdict(deque)
for k in sorted(windows, key=lambda s: int(s.rsplit("_", 1)[1])):
    tk, rest = k.split("_", 1)
    key_queue[(tk, rest.rsplit("_", 1)[0])].append(k)
ev = ev.reset_index(drop=True)
ev["key"] = [key_queue[(r.ticker, str(r.date.date()))].popleft()
             if key_queue[(r.ticker, str(r.date.date()))] else None for _, r in ev.iterrows()]
ev = ev[ev.key.notna()]
YEAR_MIN, YEAR_MAX = 2016, 2019
sc = ev[ev.tier == "small"].sort_values("date").reset_index(drop=True)
sc = sc[(sc.date.dt.year >= YEAR_MIN) & (sc.date.dt.year <= YEAR_MAX)].reset_index(drop=True)


def offset_to_date(anchor, off):
    return pd.Timestamp(np.busday_offset(anchor.date(), off, roll="forward"))


def run(params, events=None, seed=0):
    e = sc if events is None else events
    marks_by_date = {}
    open_positions = []
    rng = np.random.default_rng(seed)
    unshortable = set()
    if params.short_gate_mode == "worst_first":
        fails = e[~e.success].sort_values("car_short")
        n_drop = int(round((1 - params.short_executable_frac) * len(fails)))
        unshortable = set(fails.head(n_drop).index)
    for _, r in e.iterrows():
        anchor = r.date
        is_long = bool(r.success)
        entry_off = params.long_entry if is_long else params.short_entry
        exit_off = params.long_exit if is_long else params.short_exit
        entry_date = offset_to_date(anchor, entry_off)
        exit_date = offset_to_date(anchor, exit_off)
        if not is_long:
            blocked = (r.name in unshortable) if params.short_gate_mode == "worst_first" \
                else (rng.random() > params.short_executable_frac)
            if blocked:
                continue
        open_positions = [op for op in open_positions if op[0] > entry_date]
        gross = sum(op[1] for op in open_positions)
        ticker_expo = sum(op[1] for op in open_positions if op[2] == r.ticker)
        target = params.frac_per_position * params.capital0
        target = min(target, params.per_ticker_cap * params.capital0 - ticker_expo)
        target = min(target, params.max_gross * params.capital0 - gross)
        if target <= 0:
            continue
        pnl = position_pnl(r.to_dict(), windows[r.key], target, params)
        open_positions.append((exit_date, target, r.ticker))
        prev = 0.0
        for off, cum in pnl["marks"]:
            d = offset_to_date(anchor, off)
            marks_by_date[d] = marks_by_date.get(d, 0.0) + (cum - prev)
            prev = cum
    if not marks_by_date:
        return pd.Series(dtype=float)
    idx = pd.date_range(min(marks_by_date), max(marks_by_date), freq="B")
    return params.capital0 + pd.Series({d: marks_by_date.get(d, 0.0) for d in idx}).cumsum()


def metrics(equity):
    if len(equity) < 2:
        return {"final": np.nan, "cagr": np.nan, "sharpe": np.nan, "maxdd": np.nan}
    monthly = equity.resample("ME").last().dropna()
    rets = monthly.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    sharpe = (rets.mean() / rets.std() * np.sqrt(12)) if rets.std() > 0 else np.nan
    dd = (equity / equity.cummax() - 1).min()
    return {"final": equity.iloc[-1], "cagr": cagr, "sharpe": sharpe, "maxdd": dd}


def run_acc(params, acc):
    finals = []
    for s in range(5):
        e2 = sc.copy()
        rng = np.random.default_rng(s)
        flip = rng.random(len(e2)) > acc
        e2.loc[flip, "success"] = ~e2.loc[flip, "success"].astype(bool)
        finals.append(metrics(run(params, events=e2.sort_values("date"), seed=s))["final"])
    return float(np.nanmean(finals))


REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
base_final = metrics(run(REAL))["final"]
print(f"realistic base final: ${base_final/1e6:.1f}M")

# ---- one-at-a-time sweeps ----
sweeps = {
    "borrow rate (25-400 %/yr)": ("borrow_rate_annual", [0.25, 0.5, 1.0, 2.0, 4.0]),
    "utilization (20-80 % lent)": ("utilization", [0.2, 0.4, 0.6, 0.8]),
    "post-catalyst borrow (0-50 % of rate)": ("post_collapse_frac", [0.0, 0.1, 0.25, 0.5]),
    "shortable fraction (30-90 %)": ("short_executable_frac", [0.3, 0.5, 0.7, 0.9]),
    "round-trip impact (20-150 bps)": ("impact_bps", [20, 50, 80, 150]),
    "size / position (2-8 % of capital)": ("frac_per_position", [0.02, 0.05, 0.08]),
    "long entry (T-30 to T-10 days)": ("long_entry", [-30, -20, -10]),
    "long exit (T+42 to T+84 days)": ("long_exit", [42, 63, 84]),
    "max gross exposure (1.0-2.0x)": ("max_gross", [1.0, 1.5, 2.0]),
}
sweep_results = {}
for label, (attr, vals) in sweeps.items():
    finals = [metrics(run(replace(REAL, **{attr: v})))["final"] / 1e6 for v in vals]
    sweep_results[label] = {"vals": vals, "finals_Musd": finals}
    print(f"{label:22} {[round(f) for f in finals]}")

# accuracy sweep (separate: needs label flips)
acc_vals = [1.0, 0.9, 0.8, 0.7]
acc_finals = [run_acc(REAL, a) / 1e6 for a in acc_vals]
sweep_results["model accuracy (70-100 %)"] = {"vals": acc_vals, "finals_Musd": acc_finals}
print(f"{'model accuracy':22} {[round(f) for f in acc_finals]}")

# ---- tornado: range of final across each single-variable sweep ----
tornado = sorted(((lbl, max(d["finals_Musd"]) - min(d["finals_Musd"]),
                   min(d["finals_Musd"]), max(d["finals_Musd"]))
                  for lbl, d in sweep_results.items()), key=lambda x: x[1])

fig, ax = plt.subplots(figsize=(9, 5))
labels = [t[0] for t in tornado]
lows = [t[2] for t in tornado]; highs = [t[3] for t in tornado]
b = base_final / 1e6
for i, (lbl, rng_, lo, hi) in enumerate(tornado):
    ax.barh(i, hi - lo, left=lo, height=0.6, color="#2a78d6", alpha=0.75)
ax.axvline(b, color="#d03b3b", lw=1.5, label=f"realistic base ${b:.0f}M")
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
ax.set_xlabel("Ending equity in USD millions (from a 10M start).  Each bar = the range as that one variable is swept across the shown span.")
ax.set_title("Sensitivity tornado - realistic backtest (longer bar = result depends on it more)")
ax.legend()
plt.tight_layout(); fig.savefig("reports/backtest_tornado.png", dpi=95, bbox_inches="tight"); plt.close(fig)

# ---- bear / base / bull scenarios (bad vs good times) ----
scenarios = {
    "BEAR (bad times)": replace(REAL, borrow_rate_annual=0.30, utilization=0.20,
                                post_collapse_frac=0.05, short_executable_frac=0.30,
                                impact_bps=150),
    "BASE (realistic)": REAL,
    "BULL (good times)": replace(REAL, borrow_rate_annual=2.0, utilization=0.60,
                                 post_collapse_frac=0.25, short_executable_frac=0.70,
                                 impact_bps=50),
}
scen = {}
print("\n=== scenarios ===")
for name, p in scenarios.items():
    # bear also assumes a worse model (85% acc); bull assumes perfect
    acc = 0.85 if "BEAR" in name else 1.0
    f = run_acc(p, acc)
    eq = run(p)
    mm = metrics(eq)
    scen[name] = {"final_Musd": f / 1e6, "cagr": mm["cagr"], "sharpe": mm["sharpe"], "maxdd": mm["maxdd"]}
    print(f"{name:20} final=${f/1e6:5.1f}M  cagr={mm['cagr']*100:5.1f}%  sharpe={mm['sharpe']:.2f}  maxDD={mm['maxdd']*100:.0f}%")

# ---- regime breakdown on realistic ----
regimes = {"2016 crash": ("2016-01-01", "2016-12-31"), "2017": ("2017-01-01", "2017-12-31"),
           "2018": ("2018-01-01", "2018-12-31"), "2019": ("2019-01-01", "2019-12-31")}
reg = {}
print("\n=== realistic by regime ===")
for name, (a, b_) in regimes.items():
    sub = sc[(sc.date >= a) & (sc.date <= b_)]
    if len(sub):
        eq = run(REAL, events=sub)
        m = metrics(eq)
        reg[name] = {"total": (m["final"] / REAL.capital0 - 1) if not np.isnan(m["final"]) else None,
                     "sharpe": m["sharpe"], "n": int(len(sub))}
        print(f"{name:12} total={reg[name]['total']*100:+.0f}%  sharpe={m['sharpe']:.2f}  n={len(sub)}")

out = {"base_final_Musd": base_final / 1e6, "sweeps": sweep_results,
       "scenarios": scen, "regime_realistic": reg}
json.dump(out, open("data/processed/backtest_sensitivity.json", "w"), indent=2, default=float)
print("\nwrote data/processed/backtest_sensitivity.json + reports/backtest_tornado.png")
