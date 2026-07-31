"""Manager-requested extensions (2016-2019), DEPLOYED BOOK = LONG + LEND.

The short leg is shown once, per scenario, as the PROOF it does not pay (only
turns positive in BULL) -> then dropped from the deployed strategy, headline,
charts and MC.

Outputs:
  - per-scenario leg split WITH short (the justification table)
  - long+lend headline (with vs without lending = the lending uplift)
  - hedged vs un-hedged (long+lend)
  - benchmark vs S&P 500 + XBI, incl. the strategy at a realistic 90% model
  - stacked-area equity (long+lend) and equity-vs-benchmark line chart
  - one-at-a-time Monte Carlo at 90% AND 80% accuracy (long+lend variables)
"""
import sys, json, base64
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
sc = ev[ev.tier == "small"].sort_values("date").reset_index(drop=True)          # full book
sc = sc[(sc.date.dt.year >= 2016) & (sc.date.dt.year <= 2019)].reset_index(drop=True)
sc_long = sc[sc.success].sort_values("date").reset_index(drop=True)             # DEPLOYED book

CAP = 10_000_000


def offset_to_date(anchor, off):
    return pd.Timestamp(np.busday_offset(anchor.date(), off, roll="forward"))


def run_full(params, events, seed=0):
    """-> (equity Series, attrib dict, comp_cum DataFrame). `events` explicit."""
    e = events
    marks_by_date = {}
    comp_by_date = defaultdict(lambda: defaultdict(float))
    attrib = {"long_price": 0.0, "long_income": 0.0, "short_net": 0.0, "frictions": 0.0,
              "n_long": 0, "n_short": 0}
    open_pos = []
    rng = np.random.default_rng(seed)
    unshort = set()
    if params.short_gate_mode == "worst_first" and (~e.success).any():
        f = e[~e.success].sort_values("car_short")
        unshort = set(f.head(int(round((1 - params.short_executable_frac) * len(f)))).index)
    for _, r in e.iterrows():
        is_long = bool(r.success)
        eoff = params.long_entry if is_long else params.short_entry
        xoff = params.long_exit if is_long else params.short_exit
        ed, xd = offset_to_date(r.date, eoff), offset_to_date(r.date, xoff)
        if not is_long:
            blocked = (r.name in unshort) if params.short_gate_mode == "worst_first" \
                else (rng.random() > params.short_executable_frac)
            if blocked:
                continue
        open_pos = [o for o in open_pos if o[0] > ed]
        gross = sum(o[1] for o in open_pos); tk = sum(o[1] for o in open_pos if o[2] == r.ticker)
        t = min(params.frac_per_position * params.capital0,
                params.per_ticker_cap * params.capital0 - tk,
                params.max_gross * params.capital0 - gross)
        if t <= 0:
            continue
        pnl = position_pnl(r.to_dict(), windows[r.key], t, params)
        open_pos.append((xd, t, r.ticker))
        if is_long:
            attrib["long_price"] += pnl["price_pnl"]; attrib["long_income"] += pnl["income_pnl"]; attrib["n_long"] += 1
        else:
            attrib["short_net"] += pnl["price_pnl"] + pnl["income_pnl"]; attrib["n_short"] += 1
        attrib["frictions"] += -(t * (params.impact_bps + params.commission_bps) / 1e4)
        prev = 0.0
        for off, cum in pnl["marks"]:
            d = offset_to_date(r.date, off)
            marks_by_date[d] = marks_by_date.get(d, 0.0) + (cum - prev); prev = cum
        for band, ms in pnl["comp_marks"].items():
            prev = 0.0
            for off, cum in ms:
                d = offset_to_date(r.date, off)
                comp_by_date[band][d] += (cum - prev); prev = cum
    if not marks_by_date:
        return pd.Series(dtype=float), attrib, pd.DataFrame()
    idx = pd.date_range(min(marks_by_date), max(marks_by_date), freq="B")
    equity = params.capital0 + pd.Series({d: marks_by_date.get(d, 0.0) for d in idx}).cumsum()
    comp_cum = pd.DataFrame({b: pd.Series({d: comp_by_date[b].get(d, 0.0) for d in idx}).cumsum()
                             for b in ["long_price", "long_income", "short_net", "frictions"]})
    return equity, attrib, comp_cum


def metrics(equity):
    if len(equity) < 2:
        return {}
    monthly = equity.resample("ME").last().dropna(); rets = monthly.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    dd = (equity / equity.cummax() - 1).min()
    return {"final": float(equity.iloc[-1]), "total": float(equity.iloc[-1] / equity.iloc[0] - 1),
            "cagr": float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1),
            "sharpe": float(rets.mean() / rets.std() * np.sqrt(12)) if rets.std() > 0 else None,
            "maxdd": float(dd)}


def flip(e, acc, seed):
    e2 = e.copy(); rng = np.random.default_rng(seed)
    fl = rng.random(len(e2)) > acc
    e2.loc[fl, "success"] = ~e2.loc[fl, "success"].astype(bool)
    return e2.sort_values("date")


def deployed_book(acc, seed):
    """Deployed long+lend book at model accuracy `acc`: act on the names the
    MODEL calls success (drawn from the FULL universe), so a misclassified true
    failure enters as a landmine long. acc=1.0 -> exactly the true successes."""
    e = flip(sc, acc, seed)
    return e[e.success].sort_values("date").reset_index(drop=True)


REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
out = {}

# ---------- 1. per-scenario leg split WITH short (the proof to DROP short) ----------
# Uniform 100% accuracy across all three so the leg differences are PURELY the
# cost/borrow/executability assumptions (labelled), not model noise.
scen_params = {
    "BEAR": replace(REAL, borrow_rate_annual=0.30, utilization=0.20, post_collapse_frac=0.05,
                    short_executable_frac=0.30, impact_bps=150),
    "BASE": REAL,
    "BULL": replace(REAL, borrow_rate_annual=2.0, utilization=0.60, post_collapse_frac=0.25,
                    short_executable_frac=0.70, impact_bps=50),
}
scen_attr = {}
for name, pp in scen_params.items():
    _, a, _ = run_full(pp, events=sc)                       # 100% accuracy (true labels)
    a["gross"] = a["long_price"] + a["long_income"] + a["short_net"] + a["frictions"]
    a["inputs"] = {"borrow_rate_pct": pp.borrow_rate_annual * 100, "utilization_pct": pp.utilization * 100,
                   "post_catalyst_pct": pp.post_collapse_frac * 100,
                   "shortable_pct": pp.short_executable_frac * 100, "impact_bps": pp.impact_bps,
                   "accuracy_pct": 100}
    scen_attr[name] = a
    print(f"{name:5} borrow={pp.borrow_rate_annual*100:.0f}% util={pp.utilization*100:.0f}% "
          f"short%={pp.short_executable_frac*100:.0f}% | long_price={a['long_price']/1e6:5.1f} "
          f"long_lend={a['long_income']/1e6:5.1f} short_net={a['short_net']/1e6:5.1f} "
          f"frict={a['frictions']/1e6:5.1f} gross={a['gross']/1e6:5.1f}")
out["scenario_attrib_withshort"] = scen_attr

# ---------- 2. DEPLOYED long+lend headline (with vs without lending) ----------
eq_ll, attr_ll, comp_ll = run_full(REAL, events=sc_long)
eq_ll_nolend, attr_nl, _ = run_full(replace(REAL, include_lending=False), events=sc_long)
out["deployed_longlend"] = {"metrics": metrics(eq_ll), "attrib": attr_ll,
                            "price_only": metrics(eq_ll_nolend)}
print(f"\nDEPLOYED long+lend: final ${metrics(eq_ll)['final']/1e6:.1f}M  "
      f"(price-only ${metrics(eq_ll_nolend)['final']/1e6:.1f}M -> lending uplift "
      f"{metrics(eq_ll)['final']/metrics(eq_ll_nolend)['final']-1:+.0%})")

# ---------- 3. hedged vs un-hedged (long+lend) ----------
eq_unh, _, _ = run_full(replace(REAL, hedge=False), events=sc_long)
out["hedge"] = {"hedged": metrics(eq_ll), "unhedged": metrics(eq_unh)}
print("HEDGED  ", {k: round(v, 2) if isinstance(v, float) else v for k, v in metrics(eq_ll).items()})
print("UNHEDGED", {k: round(v, 2) if isinstance(v, float) else v for k, v in metrics(eq_unh).items()})

# ---------- 4. benchmark vs SPX + XBI (+ strategy @90%) ----------
bench = {}; bench_px = {}
try:
    import yfinance as yf
    px = yf.download(["^GSPC", "XBI"], start=str(eq_ll.index[0].date()),
                     end=str(eq_ll.index[-1].date()), auto_adjust=True, progress=False)["Close"].dropna()
    for tk in ["^GSPC", "XBI"]:
        s = px[tk].dropna(); bench_px[tk] = s
        monthly = s.resample("ME").last().dropna(); rets = monthly.pct_change().dropna()
        years = (s.index[-1] - s.index[0]).days / 365.25
        bench[tk] = {"total": float(s.iloc[-1] / s.iloc[0] - 1),
                     "cagr": float((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1),
                     "sharpe": float(rets.mean() / rets.std() * np.sqrt(12)),
                     "maxdd": float((s / s.cummax() - 1).min())}
        print(f"{tk:6} total={bench[tk]['total']*100:+.0f}% cagr={bench[tk]['cagr']*100:.0f}% "
              f"sharpe={bench[tk]['sharpe']:.2f} maxDD={bench[tk]['maxdd']*100:.0f}%")
except Exception as e:
    print("benchmark download failed:", e); bench = {"error": str(e)}
# strategy at a realistic 90% model (fair comparison) -- predicted-success book
finals90 = [metrics(run_full(REAL, events=deployed_book(0.90, s), seed=s)[0])["final"] for s in range(5)]
out["strategy_at_90"] = {"final": float(np.mean(finals90)),
                         "total": float(np.mean(finals90) / CAP - 1)}
print(f"strategy@90% model: ${np.mean(finals90)/1e6:.1f}M ({np.mean(finals90)/CAP-1:+.0%})")
out["benchmark"] = bench; out["strategy_perfect"] = metrics(eq_ll)

# ---------- 5a. stacked-area equity (long+lend) ----------
comp_M = comp_ll / 1e6
fig, ax = plt.subplots(figsize=(11, 5))
baseline = np.full(len(comp_M), CAP / 1e6)
bands = [("long_price", "#2f9e44", "Long - price appreciation"),
         ("long_income", "#8ce99a", "Long - lending income"),
         ("frictions", "#adb5bd", "Frictions (impact + commission)")]
for band, col, lab in bands:
    top = baseline + comp_M[band].values
    ax.fill_between(comp_M.index, baseline, top, color=col, alpha=0.85, label=lab); baseline = top
ax.plot(eq_ll.index, eq_ll.values / 1e6, color="#141b33", lw=1.6, label="Total equity (long+lend)")
ax.axhline(CAP / 1e6, color="gray", ls=":", lw=0.8)
ax.set_ylabel("Equity ($M)"); ax.set_xlabel("2016-2019")
ax.set_title("Cumulative contribution by leg (stacked) - deployed long+lend book")
ax.legend(loc="upper left", fontsize=9)
plt.tight_layout(); fig.savefig("reports/backtest_stacked.png", dpi=95, bbox_inches="tight"); plt.close(fig)

# ---------- 5b. equity vs benchmarks (perfect-foresight caveat on chart) ----------
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(eq_ll.index, eq_ll.values / 1e6, color="#2f9e44", lw=1.9, label=f"Strategy long+lend, hedged - ${metrics(eq_ll)['final']/1e6:.0f}M (perfect foresight)")
ax.plot(eq_unh.index, eq_unh.values / 1e6, color="#2f9e44", lw=1.2, ls="--", label=f"Strategy long+lend, un-hedged - ${metrics(eq_unh)['final']/1e6:.0f}M")
for tk, col, lab in [("^GSPC", "#2a78d6", "S&P 500"), ("XBI", "#d0803b", "XBI (biotech)")]:
    if tk in bench_px:
        s = bench_px[tk]; reb = CAP / 1e6 * s / s.iloc[0]
        ax.plot(s.index, reb.values, color=col, lw=1.4, label=f"{lab} buy-and-hold - ${reb.iloc[-1]:.0f}M")
ax.axhline(CAP / 1e6, color="gray", ls=":", lw=0.8)
ax.set_ylabel("Equity ($M)"); ax.set_xlabel("2016-2019")
ax.set_title("Strategy vs benchmarks, $10M start  (strategy = perfect-foresight ceiling; see 90% row in table)")
ax.legend(loc="upper left", fontsize=8.5)
plt.tight_layout(); fig.savefig("reports/backtest_equity.png", dpi=95, bbox_inches="tight"); plt.close(fig)

# ---------- 6. one-at-a-time Monte Carlo at 90% AND 80% (long+lend variables) ----------
def draw(name, rng):
    if name == "borrow_rate_annual": return float(np.clip(rng.triangular(0.25, 1.0, 2.5), 0.1, 3))
    if name == "utilization":        return float(rng.uniform(0.20, 0.60))
    if name == "post_collapse_frac": return float(rng.uniform(0.05, 0.25))
    if name == "impact_bps":         return float(rng.uniform(40, 150))

oat_labels = {"borrow_rate_annual": "Borrow rate (cost of lending)", "utilization": "Utilization",
              "post_collapse_frac": "Post-catalyst borrow", "impact_bps": "Round-trip impact"}
N = 250
oat = {}
for acc in [0.90, 0.80]:
    key = f"acc_{int(acc*100)}"; oat[key] = {}
    for name in oat_labels:
        rng = np.random.default_rng((hash(name) + int(acc*100)) % 2**32)
        finals = []
        for i in range(N):
            p = replace(REAL, **{name: draw(name, rng)})
            finals.append(metrics(run_full(p, events=deployed_book(acc, i), seed=i)[0])["final"] / 1e6)
        finals = np.array(finals)
        oat[key][name] = {"median": float(np.median(finals)), "p5": float(np.percentile(finals, 5)),
                          "p95": float(np.percentile(finals, 95))}
        print(f"OAT {int(acc*100)}% {oat_labels[name]:28} median ${oat[key][name]['median']:.1f}M "
              f"[{oat[key][name]['p5']:.1f}, {oat[key][name]['p95']:.1f}]")
out["oat_mc"] = oat

# OAT chart: two rows per variable (90% and 80%)
fig, ax = plt.subplots(figsize=(10, 5))
order = sorted(oat_labels, key=lambda n: oat["acc_90"][n]["p95"] - oat["acc_90"][n]["p5"])
yt, ytl = [], []
for i, name in enumerate(order):
    for j, (acc, col) in enumerate([("acc_90", "#2a78d6"), ("acc_80", "#d0803b")]):
        d = oat[acc][name]; y = i * 2.2 + (0.5 if j == 0 else -0.5)
        ax.plot([d["p5"], d["p95"]], [y, y], color=col, lw=7, alpha=0.55, solid_capstyle="round")
        ax.plot(d["median"], y, "o", color="#141b33", ms=7)
        yt.append(y); ytl.append(f"{oat_labels[name]} @{acc[-2:]}%")
ax.set_yticks(yt); ax.set_yticklabels(ytl, fontsize=9)
ax.set_xlabel("Final equity ($M) - vary THIS assumption alone; blue=90% model, orange=80% model")
ax.set_title("One-at-a-time Monte Carlo (long+lend) - borrow rate (cost of lending) dominates")
plt.tight_layout(); fig.savefig("reports/backtest_oat_mc.png", dpi=95, bbox_inches="tight"); plt.close(fig)

json.dump(out, open("data/processed/backtest_extra.json", "w"), indent=2, default=float)
for png in ["backtest_stacked", "backtest_oat_mc", "backtest_equity"]:
    open(f"reports/{png}_b64.txt", "w").write(
        base64.b64encode(open(f"reports/{png}.png", "rb").read()).decode())
print("\nwrote backtest_extra.json + stacked/oat_mc/equity PNGs")
