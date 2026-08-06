"""Two manager-requested charts + the price-vs-lending (80/20) validation.

1. Events per year: successes (green) vs failures (red).
2. Per-trade return breakdown (100% accuracy, deployed long+lend): for every
   trade, the stock price P&L vs the securities-lending income (Stylianos's plot).
3. Aggregate the two -> the honest price-vs-lending split of total profit.
Also dumps the unique small-cap tickers for the scalability analysis.
"""
import sys, json
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
    tk, rest = k.split("_", 1); kq[(tk, rest.rsplit("_", 1)[0])].append(k)
ev = ev.reset_index(drop=True)
ev["key"] = [kq[(r.ticker, str(r.date.date()))].popleft()
             if kq[(r.ticker, str(r.date.date()))] else None for _, r in ev.iterrows()]
ev = ev[ev.key.notna()].copy()
sc = ev[ev.tier == "small"].sort_values("date").reset_index(drop=True)
sc = sc[(sc.date.dt.year >= 2016) & (sc.date.dt.year <= 2019)].reset_index(drop=True)
sc_long = sc[sc.success].sort_values("date").reset_index(drop=True)


def o2d(a, o): return pd.Timestamp(np.busday_offset(a.date(), o, roll="forward"))


# ---------- 1. events per year: success vs failure ----------
by = sc.groupby([sc.date.dt.year, sc.success]).size().unstack(fill_value=0)
years = by.index.tolist()
succ = by.get(True, pd.Series(0, index=by.index)).tolist()
fail = by.get(False, pd.Series(0, index=by.index)).tolist()
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(years)); w = 0.4
ax.bar(x - w/2, succ, w, color="#2f9e44", label=f"Successes (long+lend)  n={sum(succ)}")
ax.bar(x + w/2, fail, w, color="#d0383b", label=f"Failures  n={sum(fail)}")
for i, (s, f) in enumerate(zip(succ, fail)):
    ax.text(x[i]-w/2, s+1, str(s), ha="center", fontsize=10, color="#2f9e44")
    ax.text(x[i]+w/2, f+1, str(f), ha="center", fontsize=10, color="#d0383b")
ax.set_xticks(x); ax.set_xticklabels(years); ax.set_ylabel("Number of catalyst events")
ax.set_title("Small-cap catalyst events per year (2016-2019): successes vs failures")
ax.legend(); plt.tight_layout()
fig.savefig("reports/events_per_year.png", dpi=110, bbox_inches="tight"); plt.close(fig)

# ---------- 2. per-trade breakdown (100% accuracy long+lend) ----------
P = Params(post_collapse_frac=0.10, short_gate_mode="worst_first")
open_pos, trades = [], []
for _, r in sc_long.iterrows():
    ed, xd = o2d(r.date, P.long_entry), o2d(r.date, P.long_exit)
    open_pos = [x for x in open_pos if x[0] > ed]
    gross = sum(x[1] for x in open_pos); tk = sum(x[1] for x in open_pos if x[2] == r.ticker)
    t = min(P.frac_per_position*P.capital0, P.per_ticker_cap*P.capital0-tk, P.max_gross*P.capital0-gross)
    if t <= 0: continue
    pn = position_pnl(r.to_dict(), windows[r.key], t, P)
    open_pos.append((xd, t, r.ticker))
    trades.append({"ticker": r.ticker, "date": r.date, "price": pn["price_pnl"]/1e6,
                   "lending": pn["income_pnl"]/1e6, "net": pn["total"]/1e6})
td = pd.DataFrame(trades)
tot_price = td.price.sum(); tot_lend = td.lending.sum(); tot = tot_price + tot_lend
print(f"trades taken: {len(td)}")
print(f"TOTAL price P&L  = ${tot_price:.1f}M  ({tot_price/tot*100:.0f}% of price+lending)")
print(f"TOTAL lending    = ${tot_lend:.1f}M  ({tot_lend/tot*100:.0f}% of price+lending)")
print(f"price-losing trades cushioned by lending: {(td.price<0).sum()} trades had negative price P&L")

fig, ax = plt.subplots(figsize=(13, 5.5)); ax.set_facecolor("#111318"); fig.set_facecolor("#111318")
xi = np.arange(len(td))
# Two colours = two SOURCES OF PROFIT (not profit/loss). Stock return can still
# go below zero (bar dips under the line); lending is always a positive add-on.
ax.bar(xi, td.price, color="#4f8ff7", label="From stock price move")
ax.bar(xi, td.lending, bottom=np.where(td.price > 0, td.price, 0), color="#e0a458", label="From lending fees")
neg = td.price < 0
ax.bar(xi[neg], td.lending[neg], bottom=td.price[neg], color="#e0a458")
ax.scatter(xi, td.net, color="white", s=7, zorder=5, label="Net profit (this trade)")
ax.axhline(0, color="#c7ccd2", lw=1.0)
for s in ax.spines.values(): s.set_color("#3a4048")
ax.tick_params(colors="#c7ccd2"); ax.yaxis.label.set_color("#c7ccd2"); ax.xaxis.label.set_color("#c7ccd2")
ax.set_xlabel("Trade index (chronological)"); ax.set_ylabel("Profit / loss ($M)")
ax.set_title(f"Per-trade return breakdown (100% accuracy) - price {tot_price/tot*100:.0f}% / lending {tot_lend/tot*100:.0f}% of profit",
             color="white")
leg = ax.legend(facecolor="#1a1d23", edgecolor="#3a4048", labelcolor="white", loc="upper left")
plt.tight_layout(); fig.savefig("reports/per_trade_breakdown.png", dpi=110, bbox_inches="tight"); plt.close(fig)

json.dump({"price_M": float(tot_price), "lending_M": float(tot_lend),
           "price_share": float(tot_price/tot), "lending_share": float(tot_lend/tot),
           "n_trades": int(len(td)), "n_price_negative": int((td.price < 0).sum())},
          open("data/processed/price_vs_lending.json", "w"), indent=2)
# tickers for scalability
pd.Series(sc_long.ticker.unique()).to_csv("data/processed/smallcap_tickers.csv", index=False, header=["ticker"])
print(f"unique small-cap long tickers: {sc_long.ticker.nunique()}")
print("wrote events_per_year.png + per_trade_breakdown.png + price_vs_lending.json")
