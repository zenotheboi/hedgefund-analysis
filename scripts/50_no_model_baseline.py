"""NO-MODEL baseline: how does the strategy do with ZERO predictive skill?

The crowd shorts biotech into catalysts (~90% fail). The model-free "go against
the flow" strategy = go LONG + LEND *every* tradable catalyst, winners AND
losers, no cherry-picking. This is the honest floor: if we can't predict, does
just-be-long-against-the-crowd still work?

Compares:
  - Winners-only (100% foresight)      -> the ceiling we quote
  - Long EVERYTHING (no model)         -> the floor (includes the failures)
  both with a 60%-tradable (executability) haircut.

CRITICAL: the result depends on the dataset's success ratio, which is NOT the
real-world ~90% failure rate -> flagged.
"""
import sys, json, numpy as np, pandas as pd
from dataclasses import replace
from collections import defaultdict, deque
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
ns, nf = int(sc.success.sum()), int((~sc.success).sum())
print(f"universe: {len(sc)} events = {ns} successes + {nf} failures  "
      f"(success rate {ns/len(sc)*100:.0f}%  -- real-world biotech is ~10%!)")


def o2d(a, o): return pd.Timestamp(np.busday_offset(a.date(), o, roll="forward"))


def run_long_book(events, params, tradable=1.0, seed=0):
    """Long+lend every row in `events` (all forced long). Returns (final, price, lend)."""
    rng = np.random.default_rng(seed)
    marks = {}; open_pos = []; agg = {"price": 0.0, "lend": 0.0}
    for _, r in events.iterrows():
        if rng.random() > tradable:      # executability haircut
            continue
        rr = r.to_dict(); rr["success"] = True            # force LONG regardless of outcome
        ed, xd = o2d(r.date, params.long_entry), o2d(r.date, params.long_exit)
        open_pos = [x for x in open_pos if x[0] > ed]
        g = sum(x[1] for x in open_pos); tk = sum(x[1] for x in open_pos if x[2] == r.ticker)
        t = min(params.frac_per_position*params.capital0, params.per_ticker_cap*params.capital0-tk,
                params.max_gross*params.capital0-g)
        if t <= 0: continue
        pn = position_pnl(rr, w[r.key], t, params)
        open_pos.append((xd, t, r.ticker)); agg["price"] += pn["price_pnl"]; agg["lend"] += pn["income_pnl"]
        prev = 0.0
        for off, cum in pn["marks"]:
            d = o2d(r.date, off); marks[d] = marks.get(d, 0.0)+(cum-prev); prev = cum
    idx = pd.date_range(min(marks), max(marks), freq="B")
    eq = params.capital0 + pd.Series({d: marks.get(d, 0.0) for d in idx}).cumsum()
    return eq.iloc[-1]/1e6, agg["price"]/1e6, agg["lend"]/1e6


REAL = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
scl = sc[sc.success].reset_index(drop=True)     # winners only

print("\n--- WINNERS ONLY (100% foresight = perfect model) ---")
for trd in [1.0, 0.6]:
    f, p, l = run_long_book(scl, REAL, tradable=trd)
    print(f"  tradable {int(trd*100)}%:  final ${f:5.1f}M   price ${p:5.1f}M  lend ${l:4.1f}M")

print("\n--- LONG EVERYTHING (NO model, against the crowd) ---")
for trd in [1.0, 0.6]:
    fs = [run_long_book(sc, REAL, tradable=trd, seed=s) for s in range(5)]
    f = np.mean([x[0] for x in fs]); p = np.mean([x[1] for x in fs]); l = np.mean([x[2] for x in fs])
    print(f"  tradable {int(trd*100)}%:  final ${f:5.1f}M   price ${p:5.1f}M  lend ${l:4.1f}M")

# what do the failures cost as longs?
fail = sc[~sc.success].reset_index(drop=True)
f_f, f_p, f_l = run_long_book(fail, REAL, tradable=1.0)
print(f"\n  failures alone as longs: price ${f_p:.1f}M (the crash) + lend ${f_l:.1f}M -> ${f_f-10:.1f}M drag")
print("\nCAVEAT: 'long everything works' hinges on this dataset being 68% success.")
print("Real biotech is ~10% success -> long-everything would be a disaster there.")
print("=> the model's REAL job is to restore that ~2:1 edge in a ~10%-success world.")
