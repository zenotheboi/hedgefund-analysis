"""6-month CAAR path (T-126..T+5 trading days), Approved vs CRL.

Methodology note: over ~126 trading days a fitted daily alpha compounds into
drift error, AND a 6-month pre-event window overlaps the T-31..T-150
estimation window the market-model alpha/beta were fit on. So for this long
horizon we use the MARKET-ADJUSTED return (stock_return - XBI_return, i.e.
beta=1, alpha=0) instead of the full market model -- the standard robust
choice for long-horizon event studies (MacKinlay 1997), with no fitted
parameter to compound. This is deliberately a different estimator from the
30-day CAAR chart; both are labelled as such.
"""
import time
from collections import defaultdict
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf

IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
PRE, POST = 126, 5   # trading days (~6 months before, 1 week after)
GOOD, BAD = "#0ca30c", "#d03b3b"

df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
tickers = sorted(df["Ticker"].unique())


def download_full(t):
    for a in range(3):
        try:
            d = yf.download(t, start="2008-06-01", end="2020-06-01",
                            auto_adjust=True, progress=False)
            if d.empty:
                return None
            c = d["Close"]
            return c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
        except Exception:
            time.sleep(1 + a)
    return None


print("downloading XBI + tickers...")
bench = download_full("XBI")
close = {}
for i, t in enumerate(tickers):
    c = download_full(t)
    if c is not None:
        close[t] = c
    if (i + 1) % 40 == 0:
        print(f"  {i+1}/{len(tickers)}")

byoff = {"Approved": defaultdict(list), "CRL": defaultdict(list)}
n_used = {"Approved": 0, "CRL": 0}
skipped = 0
for _, row in df.iterrows():
    tk, ed, status = row["Ticker"], row["Catalyst Date"], row["Approved or CRL"]
    if tk not in close:
        skipped += 1
        continue
    prices = pd.concat([close[tk], bench], axis=1, join="inner").sort_index()
    prices.columns = ["s", "b"]
    ret = prices.pct_change()
    pos = prices.index.searchsorted(pd.Timestamp(ed))
    if pos >= len(prices) or pos - PRE < 1 or pos + POST >= len(prices):
        skipped += 1
        continue
    n_used[status] += 1
    for off in range(-PRE, POST + 1):
        r = ret.iloc[pos + off]
        adj = r["s"] - r["b"]           # market-adjusted abnormal return
        if pd.notna(adj):
            byoff[status][off].append(adj)

offsets = list(range(-PRE, POST + 1))
caar = {}
for st in ["Approved", "CRL"]:
    run, path = 0.0, []
    for o in offsets:
        vals = byoff[st][o]
        run += (np.mean(vals) if vals else 0.0)
        path.append(run * 100)
    caar[st] = path

print(f"used Approved={n_used['Approved']} CRL={n_used['CRL']} skipped={skipped}")
print(f"Approved CAAR: T-126={caar['Approved'][0]:.1f}%  T0={caar['Approved'][PRE]:.1f}%  T+5={caar['Approved'][-1]:.1f}%")
print(f"CRL CAAR:      T-126={caar['CRL'][0]:.1f}%  T0={caar['CRL'][PRE]:.1f}%  T+5={caar['CRL'][-1]:.1f}%")

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(offsets, caar["Approved"], color=GOOD, linewidth=2, label=f"Approved (n={n_used['Approved']})")
ax.plot(offsets, caar["CRL"], color=BAD, linewidth=2, label=f"CRL (n={n_used['CRL']})")
ax.axvline(0, color="black", linestyle="--", linewidth=1)
ax.axhline(0, color="gray", linestyle=":", linewidth=0.8)
ax.set_xlabel("Trading days from catalyst (T0). ~126 trading days = 6 months.")
ax.set_ylabel("Cumulative market-adjusted return (%)")
ax.set_title("6-month CAAR path (market-adjusted, stock - XBI)\n"
             "Does the Approved run-up start earlier than 30 days?")
ax.legend(loc="upper left")
plt.tight_layout()
fig.savefig("reports/caar_6month.png", dpi=95, bbox_inches="tight")
plt.close(fig)
with open("reports/caar_6month.png", "rb") as f:
    open("reports/caar_6month_b64.txt", "w").write(base64.b64encode(f.read()).decode())
print("saved reports/caar_6month.png + b64")
