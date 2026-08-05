"""Scalability / capacity research for the small-cap long+lend strategy.

Binding constraint = small-cap liquidity. A position must be tradeable without
blowing past the assumed ~80 bps market impact. We pull each name's average
daily DOLLAR volume (2016-2019), and derive the AUM at which the average
position (5% of capital) equals a manageable multiple of one day's volume.
"""
import sys, json, numpy as np, pandas as pd
tickers = pd.read_csv("data/processed/smallcap_tickers.csv")["ticker"].tolist()
import yfinance as yf
advs = {}
try:
    px = yf.download(tickers, start="2016-01-01", end="2019-12-31",
                     auto_adjust=False, progress=False)
    close = px["Close"]; vol = px["Volume"]
    for t in tickers:
        try:
            dv = (close[t] * vol[t]).dropna()
            if len(dv) > 100:
                advs[t] = float(dv.median())    # median daily $ volume, robust to spikes
        except Exception:
            pass
except Exception as e:
    print("download issue:", e)

adv = pd.Series(advs).sort_values()
print(f"ADV coverage: {len(adv)}/{len(tickers)} names")
print(f"median daily $ volume (small-cap universe): ${adv.median()/1e6:.1f}M")
print(f"25th pct ${adv.quantile(0.25)/1e6:.1f}M   75th pct ${adv.quantile(0.75)/1e6:.1f}M")

FRAC = 0.05   # position = 5% of AUM
print("\nCapacity: AUM at which a 5%-of-capital position = k x one day's $volume")
print("(k = how many days of volume one position represents; lower k = safer)")
med = adv.median(); q25 = adv.quantile(0.25)
for k in [0.5, 1.0, 2.0, 3.0]:
    print(f"  k={k:>3}x ADV:  median-name AUM cap = ${med*k/FRAC/1e6:5.0f}M   "
          f"illiquid (25th pct) = ${q25*k/FRAC/1e6:5.0f}M")

out = {"n_names": len(adv), "median_adv_usd": float(med), "q25_adv_usd": float(q25),
       "q75_adv_usd": float(adv.quantile(0.75)),
       "aum_cap_usd": {f"k={k}": float(med*k/FRAC) for k in [0.5, 1.0, 2.0, 3.0]},
       "aum_cap_illiquid_usd": {f"k={k}": float(q25*k/FRAC) for k in [0.5, 1.0, 2.0, 3.0]}}
json.dump(out, open("data/processed/scalability.json", "w"), indent=2)
print("\nwrote data/processed/scalability.json")
