"""Standalone: uniform-100% per-scenario leg split + labelled inputs."""
import sys, json
from dataclasses import replace
from collections import defaultdict, deque
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl

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


def o2d(a, o): return pd.Timestamp(np.busday_offset(a.date(), o, roll="forward"))


def attrib(params):
    a = {"long_price": 0.0, "long_income": 0.0, "short_net": 0.0, "frictions": 0.0}
    open_pos = []
    unshort = set()
    f = sc[~sc.success].sort_values("car_short")
    unshort = set(f.head(int(round((1 - params.short_executable_frac) * len(f)))).index)
    for _, r in sc.iterrows():
        is_long = bool(r.success)
        eoff = params.long_entry if is_long else params.short_entry
        xoff = params.long_exit if is_long else params.short_exit
        ed, xd = o2d(r.date, eoff), o2d(r.date, xoff)
        if not is_long and r.name in unshort:
            continue
        open_pos = [op for op in open_pos if op[0] > ed]
        gross = sum(op[1] for op in open_pos); tk = sum(op[1] for op in open_pos if op[2] == r.ticker)
        t = min(params.frac_per_position * params.capital0, params.per_ticker_cap * params.capital0 - tk,
                params.max_gross * params.capital0 - gross)
        if t <= 0:
            continue
        p = position_pnl(r.to_dict(), windows[r.key], t, params)
        open_pos.append((xd, t, r.ticker))
        if is_long:
            a["long_price"] += p["price_pnl"]; a["long_income"] += p["income_pnl"]
        else:
            a["short_net"] += p["price_pnl"] + p["income_pnl"]
        a["frictions"] += -(t * (params.impact_bps + params.commission_bps) / 1e4)
    a["gross"] = a["long_price"] + a["long_income"] + a["short_net"] + a["frictions"]
    return a


REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
scen = {"BEAR": replace(REAL, borrow_rate_annual=0.30, utilization=0.20, post_collapse_frac=0.05,
                        short_executable_frac=0.30, impact_bps=150),
        "BASE": REAL,
        "BULL": replace(REAL, borrow_rate_annual=2.0, utilization=0.60, post_collapse_frac=0.25,
                        short_executable_frac=0.70, impact_bps=50)}
res = {}
for n, pp in scen.items():
    a = attrib(pp)
    res[n] = {"attrib": a, "inputs": {"borrow_pct": pp.borrow_rate_annual*100, "util_pct": pp.utilization*100,
              "postc_pct": pp.post_collapse_frac*100, "short_pct": pp.short_executable_frac*100,
              "impact_bps": pp.impact_bps}}
    print(f"{n:5} borrow={pp.borrow_rate_annual*100:3.0f}% util={pp.utilization*100:2.0f}% "
          f"short%={pp.short_executable_frac*100:2.0f}% impact={pp.impact_bps:3.0f}bps | "
          f"Lprice={a['long_price']/1e6:5.1f} Llend={a['long_income']/1e6:5.1f} "
          f"short={a['short_net']/1e6:5.1f} frict={a['frictions']/1e6:5.1f} gross={a['gross']/1e6:5.1f}")
json.dump(res, open("data/processed/scenario_100.json", "w"), indent=2)
print("wrote scenario_100.json")
