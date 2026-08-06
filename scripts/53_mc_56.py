"""Re-run the robustness tests on a SELECTION-BIAS-ADJUSTED universe (56% success,
the realistic phase-weighted rate) instead of the dataset's flattering 68%.

Construction: resample events to ~320 total at 56% success -- subsample winners,
top up failures (with replacement) -- so trade count/timing stay comparable and
the $ finals are directly comparable to the 68% run. Averaged over resample seeds.

Reports, at model accuracy 90% and 80%, on the 56% universe:
  - no-model long-everything (trade-luck floor)
  - bootstrap (trade luck)
  - assumption MC: independent + correlated (copula)
  - PRECISION at each accuracy.
"""
import sys, json, math
from dataclasses import replace
from collections import defaultdict, deque
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl

ev = pd.read_csv("data/processed/backtest_events.csv", parse_dates=["date"])
w = json.load(open("data/processed/backtest_windows.json"))
kq = defaultdict(deque)
for k in sorted(w, key=lambda s: int(s.rsplit("_", 1)[1])):
    tk, rest = k.split("_", 1); kq[(tk, rest.rsplit("_", 1)[0])].append(k)
ev = ev.reset_index(drop=True)
ev["key"] = [kq[(r.ticker, str(r.date.date()))].popleft()
             if kq[(r.ticker, str(r.date.date()))] else None for _, r in ev.iterrows()]
ev = ev[ev.key.notna()]
sc = ev[ev.tier == "small"]; sc = sc[(sc.date.dt.year >= 2016) & (sc.date.dt.year <= 2019)].reset_index(drop=True)
WIN = sc[sc.success].reset_index(drop=True); LOS = sc[~sc.success].reset_index(drop=True)
REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
CAP, YEARS, N_MC, N_BOOT = 10.0, 4, 400, 8000
TARGET_P, N_TOTAL = 0.56, 320
LOAD = {"borrow": +0.55, "util": -0.60, "postc": -0.35, "impact": +0.70}


def o2d(a, o): return pd.Timestamp(np.busday_offset(a.date(), o, roll="forward"))
def _phi(x): return 0.5 * (1 + np.vectorize(math.erf)(x / np.sqrt(2)))
def _tri(u, a, c, b): return np.where(u < (c-a)/(b-a), a+np.sqrt(u*(b-a)*(c-a)), b-np.sqrt((1-u)*(b-a)*(b-c)))


def universe_56(seed):
    """Resample to N_TOTAL events at TARGET_P success (subsample winners, resample failures)."""
    ns = int(round(TARGET_P * N_TOTAL)); nf = N_TOTAL - ns
    rng = np.random.default_rng(seed)
    wi = WIN.iloc[rng.choice(len(WIN), ns, replace=ns > len(WIN))]
    lo = LOS.iloc[rng.choice(len(LOS), nf, replace=True)]
    return pd.concat([wi, lo]).sort_values("date").reset_index(drop=True)


def deployed_book(u, acc, seed):
    e = u.copy(); rng = np.random.default_rng(seed)
    fl = rng.random(len(e)) > acc
    e.loc[fl, "success"] = ~e.loc[fl, "success"].astype(bool)
    return e[e.success].sort_values("date").reset_index(drop=True)


def run_book(events, params, force_long=False):
    marks = {}; open_pos = []
    for _, r in events.iterrows():
        rr = r.to_dict()
        if force_long: rr["success"] = True
        ed, xd = o2d(r.date, params.long_entry), o2d(r.date, params.long_exit)
        open_pos = [x for x in open_pos if x[0] > ed]
        g = sum(x[1] for x in open_pos); tk = sum(x[1] for x in open_pos if x[2] == r.ticker)
        t = min(params.frac_per_position*params.capital0, params.per_ticker_cap*params.capital0-tk,
                params.max_gross*params.capital0-g)
        if t <= 0: continue
        pn = position_pnl(rr, w[r.key], t, params); open_pos.append((xd, t, r.ticker)); prev = 0.0
        for off, cum in pn["marks"]:
            d = o2d(r.date, off); marks[d] = marks.get(d, 0.0)+(cum-prev); prev = cum
    if not marks: return np.nan
    idx = pd.date_range(min(marks), max(marks), freq="B")
    return (params.capital0 + pd.Series({d: marks.get(d, 0.0) for d in idx}).cumsum()).iloc[-1]/1e6


def per_trade(events, params):
    open_pos, tr = [], []
    for _, r in events.iterrows():
        ed, xd = o2d(r.date, params.long_entry), o2d(r.date, params.long_exit)
        open_pos = [x for x in open_pos if x[0] > ed]
        g = sum(x[1] for x in open_pos); tk = sum(x[1] for x in open_pos if x[2] == r.ticker)
        t = min(params.frac_per_position*params.capital0, params.per_ticker_cap*params.capital0-tk,
                params.max_gross*params.capital0-g)
        if t <= 0: continue
        tr.append(position_pnl(r.to_dict(), w[r.key], t, params)["total"]); open_pos.append((xd, t, r.ticker))
    return np.array(tr)


def params_u(pp, ub, uu, up, ui):
    return replace(pp, borrow_rate_annual=float(np.clip(_tri(ub,0.25,1.0,2.5),0.1,3)),
                   utilization=float(0.2+uu*0.4), post_collapse_frac=float(0.05+up*0.2), impact_bps=float(40+ui*110))


def stats(f):
    f = np.array(f); return {"median": float(np.median(f)), "p5": float(np.percentile(f,5)),
        "p95": float(np.percentile(f,95)), "p_loss": float((f<CAP).mean()),
        "cagr_med": float((np.median(f)/CAP)**(1/YEARS)-1)}


U = universe_56(0)     # one representative 56% universe for the MC
print(f"56% universe: {len(U)} events, {U.success.mean()*100:.0f}% success")
res = {"base_rate": TARGET_P}
for acc in [0.90, 0.80]:
    prec = (TARGET_P*acc)/(TARGET_P*acc+(1-TARGET_P)*(1-acc))
    # bootstrap (trade luck): pool per-trade over degraded books, resample
    pool = np.concatenate([per_trade(deployed_book(U, acc, 1000+s), REAL) for s in range(6)])
    n = len(pool)//6; rng = np.random.default_rng(1)
    boot = [(CAP*1e6 + rng.choice(pool, n, replace=True).sum())/1e6 for _ in range(N_BOOT)]
    # assumption MC independent + correlated
    rng = np.random.default_rng(7)
    ind = [run_book(deployed_book(U,acc,i), params_u(REAL,rng.random(),rng.random(),rng.random(),rng.random())) for i in range(N_MC)]
    rng = np.random.default_rng(11); s0 = rng.standard_normal(N_MC)
    def cu(load): return _phi(load*s0+np.sqrt(1-load**2)*rng.standard_normal(N_MC))
    ub,uu,up,ui = cu(LOAD["borrow"]),cu(LOAD["util"]),cu(LOAD["postc"]),cu(LOAD["impact"])
    cor = [run_book(deployed_book(U,acc,i), params_u(REAL,ub[i],uu[i],up[i],ui[i])) for i in range(N_MC)]
    res[f"acc{int(acc*100)}"] = {"precision": prec, "bootstrap": stats(boot),
                                 "mc_indep": stats(ind), "mc_corr": stats(cor)}
    print(f"\n=== 56% universe, {int(acc*100)}% model (precision {prec*100:.0f}%) ===")
    for nm in ["bootstrap","mc_indep","mc_corr"]:
        v=res[f"acc{int(acc*100)}"][nm]; print(f"  {nm:10} median ${v['median']:.1f}M CI[{v['p5']:.1f},{v['p95']:.1f}] CAGR {v['cagr_med']*100:.0f}% P(loss){v['p_loss']*100:.0f}%")
# no-model floor at 56% (avg over universe seeds)
nm = np.mean([run_book(universe_56(s), REAL, force_long=True) for s in range(8)])
res["no_model"] = {"final": float(nm), "cagr": float((nm/CAP)**(1/YEARS)-1)}
print(f"\nno-model long-everything @56%: ${nm:.1f}M / CAGR {((nm/CAP)**(1/YEARS)-1)*100:.0f}%")
json.dump(res, open("data/processed/mc_56.json","w"), indent=2, default=float)
print("wrote data/processed/mc_56.json")
