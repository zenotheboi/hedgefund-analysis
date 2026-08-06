"""Base-rate sensitivity: how the success rate of the universe drives everything.

Our dataset is 68% success. Real biotech is ~10%. This tests how BOTH the
no-model strategy AND the with-model (accuracy a) strategy degrade as the
success rate falls -- via the base-rate / precision problem:

  a 90%-accurate model in a 10%-success world is mostly WRONG when it says
  "success", because there are so many more failures to misclassify.

Uses mean per-position return RATES (P&L / notional), so it's size-independent.
"""
import sys, json, numpy as np, pandas as pd
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
P = Params(post_collapse_frac=0.10)
NOTION = 500_000


def rate(r):   # per-position return rate if held LONG (price + lending - cost) / notional
    rr = r.to_dict(); rr["success"] = True
    return position_pnl(rr, w[r.key], NOTION, P)["total"] / NOTION


win = np.array([rate(r) for _, r in sc[sc.success].iterrows()])
los = np.array([rate(r) for _, r in sc[~sc.success].iterrows()])
W, L = win.mean(), los.mean()
print(f"mean return if you LONG a winner: {W*100:+.1f}%   a loser: {L*100:+.1f}%")
print(f"dataset success rate = {sc.success.mean()*100:.0f}%\n")

# no-model long-everything break-even base rate: p*W + (1-p)*L = 0
p_star = -L / (W - L)
print(f"NO-MODEL break-even success rate = {p_star*100:.0f}%  "
      f"(above this, long-everything is +; below, it loses)\n")

print(f"{'success rate':>12} | {'no-model':>9} | {'model 100%':>10} | {'model 90%':>10} | {'model 80%':>10}")
print("-"*62)
rows = {}
for p in [0.68, 0.50, 0.30, 0.10]:
    nomodel = p*W + (1-p)*L
    line = f"{int(p*100):>10}%  | {nomodel*100:>+7.1f}% |"
    prec_rec = {}
    for a in [1.0, 0.90, 0.80]:
        # precision = P(true success | model says success), base rate p, accuracy a
        prec = (p*a) / (p*a + (1-p)*(1-a)) if (p*a + (1-p)*(1-a)) > 0 else 1.0
        book = prec*W + (1-prec)*L
        line += f" {book*100:>+8.1f}% |"
        prec_rec[a] = {"precision": prec, "book_return": book}
    print(line)
    rows[f"{int(p*100)}%"] = {"no_model": nomodel, "by_accuracy": prec_rec}

# required accuracy for a POSITIVE book at the realistic 10% base rate
p = 0.10
print(f"\nAt the realistic {int(p*100)}% success rate, model must be accurate enough that")
for a in [0.90, 0.95, 0.98, 0.99]:
    prec = (p*a)/(p*a+(1-p)*(1-a)); book = prec*W+(1-prec)*L
    print(f"  accuracy {a*100:.0f}% -> precision {prec*100:.0f}% -> book return {book*100:+.1f}%")
json.dump({"win_rate": float(W), "los_rate": float(L), "breakeven_success_rate": float(p_star),
           "by_base_rate": rows}, open("data/processed/base_rate.json", "w"), indent=2, default=float)
print("\nwrote data/processed/base_rate.json")
