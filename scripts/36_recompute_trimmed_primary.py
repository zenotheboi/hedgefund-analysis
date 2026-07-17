"""Recompute the whole CAR pipeline with the earnings-TRIMMED estimation as
the PRIMARY estimator (drop estimation-window days > TRIM_SIGMA from the
market-model fit, then re-fit), overwriting the main CSV and event-windows
JSON so every downstream chart reflects the trimmed version.

Trimmed vs untrimmed differed by ~0.3pp median (script 35), so nothing
material changes -- this just makes the cleaner estimator the default.
Backs up the untrimmed outputs first.
"""
import time, json, shutil
import numpy as np
import pandas as pd
import yfinance as yf

IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
OUT_CSV = "data/processed/biopharmcatalyst_small_molecule_car.csv"
OUT_JSON = "data/processed/biopharmcatalyst_event_windows.json"
EVENT_PRE, EVENT_POST, EST_WINDOW, TRIM_SIGMA = 30, 5, 120, 3.0

# back up untrimmed
shutil.copy(OUT_CSV, OUT_CSV.replace(".csv", "_untrimmed.csv"))
shutil.copy(OUT_JSON, OUT_JSON.replace(".json", "_untrimmed.json"))

df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
tickers = sorted(df["Ticker"].unique())


def dl(t):
    for a in range(3):
        try:
            d = yf.download(t, start="2008-06-01", end="2020-06-01", auto_adjust=True, progress=False)
            if d.empty:
                return None
            c = d["Close"]
            return c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
        except Exception:
            time.sleep(1 + a)
    return None


print("downloading...")
bench = dl("XBI")
close = {}
for i, t in enumerate(tickers):
    c = dl(t)
    if c is not None:
        close[t] = c
    if (i + 1) % 40 == 0:
        print(f"  {i+1}/{len(tickers)}")


def fit_trimmed(est):
    x, y = est["benchmark_return"].values, est["stock_return"].values
    beta, alpha = np.polyfit(x, y, 1)
    resid = y - (alpha + beta * x)
    sd = resid.std()
    keep = np.abs(resid) <= TRIM_SIGMA * sd
    if (~keep).sum() and keep.sum() > EST_WINDOW // 2:
        beta, alpha = np.polyfit(x[keep], y[keep], 1)
    return float(alpha), float(beta), int((~keep).sum())


results, windows = [], {}
for idx, r in df.iterrows():
    tk, ed, status = r["Ticker"], r["Catalyst Date"], r["Approved or CRL"]
    if tk not in close:
        continue
    prices = pd.concat([close[tk], bench], axis=1, join="inner").sort_index()
    prices.columns = ["stock_close", "benchmark_close"]
    ret = prices.pct_change(); ret.columns = ["stock_return", "benchmark_return"]
    data = prices.join(ret)
    pos = data.index.searchsorted(pd.Timestamp(ed))
    lo = pos - (EVENT_PRE + EST_WINDOW)
    if lo < 1 or pos + EVENT_POST >= len(data):
        continue
    data = data.iloc[lo:pos + EVENT_POST + 1].copy()
    data["trading_day_offset"] = np.arange(len(data)) - (EVENT_PRE + EST_WINDOW)
    est = data[data["trading_day_offset"] < -EVENT_PRE].dropna(subset=["stock_return", "benchmark_return"])
    if len(est) < EST_WINDOW // 2:
        continue
    alpha, beta, dropped = fit_trimmed(est)

    ev = data[(data["trading_day_offset"] >= -EVENT_PRE) & (data["trading_day_offset"] <= EVENT_POST)].copy()
    ev["expected_return"] = alpha + beta * ev["benchmark_return"]
    ev["abnormal_return"] = ev["stock_return"] - ev["expected_return"]
    sw = ev[(ev["trading_day_offset"] >= -2) & (ev["trading_day_offset"] <= 2)]
    car = float(sw["abnormal_return"].sum())
    raw = float((1 + sw["stock_return"]).prod() - 1)
    benr = float((1 + sw["benchmark_return"]).prod() - 1)

    results.append({"ticker": tk, "drug_name": r["Drug Name"], "indication": r["Indication"],
                    "status": status, "catalyst_date": str(ed.date()), "mw": r.get("mw"),
                    "alpha": alpha, "beta": beta, "car": car, "raw_return": raw,
                    "benchmark_return": benr, "est_days_dropped": dropped})
    key = f"{tk}_{ed.date()}_{idx}"
    evo = ev.reset_index().rename(columns={ev.index.name or "index": "date"})
    evo["date"] = evo["date"].astype(str)
    windows[key] = evo[["date", "trading_day_offset", "stock_close", "benchmark_close",
                        "stock_return", "benchmark_return", "expected_return", "abnormal_return"]].to_dict("records")

pd.DataFrame(results).to_csv(OUT_CSV, index=False)
json.dump(windows, open(OUT_JSON, "w"))

res = pd.DataFrame(results)
print(f"\nrecomputed {len(res)} events (TRIMMED primary). avg est-days dropped: {res['est_days_dropped'].mean():.1f}")
from scipy import stats
a, c = res[res.status == "Approved"]["car"], res[res.status == "CRL"]["car"]
print(f"Approved n={len(a)} median={a.median()*100:+.2f}% mean={a.mean()*100:+.2f}%")
print(f"CRL      n={len(c)} median={c.median()*100:+.2f}% mean={c.mean()*100:+.2f}%")
print(f"Mann-Whitney p={stats.mannwhitneyu(a, c, alternative='two-sided')[1]:.2g}")
