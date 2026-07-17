"""Robustness check: re-fit the market-model alpha/beta on a TRIMMED
estimation window that drops extreme daily returns (proxy for earnings /
other one-off news), then recompute T-2..T+2 CAR and compare to the
original (untrimmed) numbers.

Rationale: the estimation window (120 trading days ending T-31) may contain
an earnings day or two whose large move distorts the fitted alpha/beta. We
don't have an exact earnings feed, so we drop any estimation-window day with
|abnormal-ish move| beyond TRIM_SIGMA standard deviations and re-fit. A
single day out of 120 has limited leverage, so the expectation is the CARs
barely move -- which is itself the useful result (shows the headline isn't
an artifact of estimation-window contamination).
"""
import time
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
OUT = "data/interim/35_earnings_trim_compare.csv"
EVENT_PRE, EVENT_POST, EST_WINDOW = 30, 5, 120
TRIM_SIGMA = 3.0
GOOD_STATUSES = ("Approved", "CRL")

df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
tickers = sorted(df["Ticker"].unique())


def dl(t):
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
bench = dl("XBI")
close = {}
for i, t in enumerate(tickers):
    c = dl(t)
    if c is not None:
        close[t] = c
    if (i + 1) % 40 == 0:
        print(f"  {i+1}/{len(tickers)}")


def fit(est, trim):
    """OLS alpha/beta; if trim, drop |residual| > TRIM_SIGMA*resid_std and refit once."""
    x = est["benchmark_return"].values
    y = est["stock_return"].values
    beta, alpha = np.polyfit(x, y, 1)
    if not trim:
        return alpha, beta, 0
    resid = y - (alpha + beta * x)
    sd = resid.std()
    keep = np.abs(resid) <= TRIM_SIGMA * sd
    dropped = int((~keep).sum())
    if dropped and keep.sum() > EST_WINDOW // 2:
        beta, alpha = np.polyfit(x[keep], y[keep], 1)
    return alpha, beta, dropped


rows = []
for _, r in df.iterrows():
    tk, ed, status = r["Ticker"], r["Catalyst Date"], r["Approved or CRL"]
    if tk not in close:
        continue
    prices = pd.concat([close[tk], bench], axis=1, join="inner").sort_index()
    prices.columns = ["stock_close", "benchmark_close"]
    ret = prices.pct_change()
    ret.columns = ["stock_return", "benchmark_return"]
    data = prices.join(ret)
    pos = data.index.searchsorted(pd.Timestamp(ed))
    lo = pos - (EVENT_PRE + EST_WINDOW)
    if lo < 1 or pos + EVENT_POST >= len(data):
        continue
    data = data.iloc[lo:pos + EVENT_POST + 1].copy()
    data["off"] = np.arange(len(data)) - (EVENT_PRE + EST_WINDOW)
    est = data[data["off"] < -EVENT_PRE].dropna(subset=["stock_return", "benchmark_return"])
    if len(est) < EST_WINDOW // 2:
        continue
    ev = data[(data["off"] >= -2) & (data["off"] <= 2)]

    car = {}
    for trim in (False, True):
        a, b, dropped = fit(est, trim)
        ab = ev["stock_return"] - (a + b * ev["benchmark_return"])
        car[trim] = (ab.sum(), a, b, dropped)

    rows.append({
        "ticker": tk, "status": status, "date": str(ed.date()),
        "car_orig": car[False][0], "alpha_orig": car[False][1], "beta_orig": car[False][2],
        "car_trim": car[True][0], "alpha_trim": car[True][1], "beta_trim": car[True][2],
        "days_dropped": car[True][3],
    })

res = pd.DataFrame(rows)
res["car_delta"] = res["car_trim"] - res["car_orig"]
res.to_csv(OUT, index=False)

print(f"\nevents: {len(res)}  | avg est-days dropped by trim: {res['days_dropped'].mean():.1f}")
print(f"median |CAR change| from trimming: {res['car_delta'].abs().median()*100:.3f} pp")
print(f"max |CAR change|: {res['car_delta'].abs().max()*100:.2f} pp\n")

for label, col in [("ORIGINAL", "car_orig"), ("TRIMMED", "car_trim")]:
    a = res[res.status == "Approved"][col]
    c = res[res.status == "CRL"][col]
    mw = stats.mannwhitneyu(a, c, alternative="two-sided")[1]
    pa = stats.wilcoxon(a)[1]
    pc = stats.wilcoxon(c)[1]
    print(f"{label:9} Appr med={a.median()*100:+.2f}% (vs0 p={pa:.2g}) | "
          f"CRL med={c.median()*100:+.2f}% (vs0 p={pc:.2g}) | Appr-vs-CRL p={mw:.2g}")
