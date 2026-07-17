"""Pull prices and compute CAR for each small-molecule Approved/CRL event.

Efficiency note: many tickers have multiple events (Approved then a later
CRL, or vice versa), and events cluster in 2017-2019. Rather than re-download
per event (what src/hedgefund/prices.py's fetch_event_data does), download
each ticker's full daily history ONCE (covering the whole 2009-2020 span)
and slice per-event windows out of that in memory. Reuses prices.py's
fit_market_model()/short_window_car() for the actual math so the estimator
is identical to the rest of the project (short T-2..T+2 CAR vs XBI).
"""
import sys
import time
import json
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, "src")
from hedgefund.prices import fit_market_model, short_window_car, DEFAULT_BENCHMARK

IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
OUT_CSV = "data/processed/biopharmcatalyst_small_molecule_car.csv"
OUT_JSON = "data/processed/biopharmcatalyst_event_windows.json"

EVENT_WINDOW_PRE = 30
EVENT_WINDOW_POST = 5
ESTIMATION_WINDOW = 120

df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
tickers = sorted(df["Ticker"].unique())
print(f"{len(df)} events, {len(tickers)} unique tickers")

HIST_START = "2008-06-01"
HIST_END = "2020-06-01"


def download_full(ticker: str) -> pd.Series:
    for attempt in range(3):
        try:
            d = yf.download(ticker, start=HIST_START, end=HIST_END, auto_adjust=True, progress=False)
            if d.empty:
                return None
            close = d["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            return close
        except Exception as e:
            time.sleep(1 + attempt)
    return None


print("downloading benchmark XBI...")
bench_close = download_full(DEFAULT_BENCHMARK)
if bench_close is None:
    raise RuntimeError("could not download XBI benchmark history")

print("downloading per-ticker history...")
ticker_close = {}
failed_tickers = []
for i, t in enumerate(tickers):
    c = download_full(t)
    if c is None:
        failed_tickers.append(t)
    else:
        ticker_close[t] = c
    if (i + 1) % 20 == 0:
        print(f"  {i+1}/{len(tickers)} tickers ({len(failed_tickers)} failed so far)")

print(f"tickers with price history: {len(ticker_close)} / {len(tickers)}")
print(f"tickers with NO data (likely delisted/renamed before Yahoo's coverage): {failed_tickers}")


def build_event_window(stock: pd.Series, bench: pd.Series, ann_date) -> pd.DataFrame:
    prices = pd.concat([stock, bench], axis=1, join="inner")
    prices.columns = ["stock_close", "benchmark_close"]
    prices = prices.sort_index()
    returns = prices.pct_change()
    returns.columns = ["stock_return", "benchmark_return"]
    out = prices.join(returns)

    ann = pd.Timestamp(ann_date)
    pos = out.index.searchsorted(ann)
    if pos >= len(out):
        raise ValueError("announcement after last available trading day")
    out["trading_day_offset"] = np.arange(len(out)) - pos

    lo = pos - (EVENT_WINDOW_PRE + ESTIMATION_WINDOW)
    hi = pos + EVENT_WINDOW_POST
    if lo < 0:
        raise ValueError("not enough price history before announcement")
    if hi >= len(out):
        raise ValueError("not enough price history after announcement")
    return out.iloc[lo:hi + 1].copy()


results = []
event_windows_dump = {}
errors = []

for idx, row in df.iterrows():
    ticker = row["Ticker"]
    ann_date = row["Catalyst Date"]
    key = f"{ticker}_{ann_date.date()}_{idx}"

    if ticker not in ticker_close:
        errors.append({"ticker": ticker, "date": str(ann_date.date()), "error": "no_price_history"})
        continue

    try:
        data = build_event_window(ticker_close[ticker], bench_close, ann_date)
        alpha, beta = fit_market_model(data, EVENT_WINDOW_PRE, ESTIMATION_WINDOW)
        event = data[(data["trading_day_offset"] >= -EVENT_WINDOW_PRE) &
                      (data["trading_day_offset"] <= EVENT_WINDOW_POST)].copy()
        event["expected_return"] = alpha + beta * event["benchmark_return"]
        event["abnormal_return"] = event["stock_return"] - event["expected_return"]
        sw = short_window_car(event, pre=2, post=2)

        results.append({
            "ticker": ticker,
            "drug_name": row["Drug Name"],
            "indication": row["Indication"],
            "status": row["Approved or CRL"],
            "catalyst_date": str(ann_date.date()),
            "mw": row.get("mw"),
            "alpha": alpha,
            "beta": beta,
            "car": sw["car"],
            "raw_return": sw["raw_return"],
            "benchmark_return": sw["benchmark_return"],
            "n_estimation_days": int((data["trading_day_offset"] < -EVENT_WINDOW_PRE).sum()),
        })
        ev_out = event.reset_index()
        ev_out = ev_out.rename(columns={ev_out.columns[0]: "date"})
        ev_out["date"] = ev_out["date"].astype(str)
        event_windows_dump[key] = ev_out.to_dict("records")
    except Exception as e:
        errors.append({"ticker": ticker, "date": str(ann_date.date()), "error": str(e)})

results_df = pd.DataFrame(results)
results_df.to_csv(OUT_CSV, index=False)
with open(OUT_JSON, "w") as f:
    json.dump(event_windows_dump, f)

errors_df = pd.DataFrame(errors)
errors_df.to_csv("data/interim/28_pricing_errors.csv", index=False)

print(f"\npriced events: {len(results_df)} / {len(df)}")
print(f"errors: {len(errors_df)}")
if len(errors_df):
    print(errors_df["error"].apply(lambda e: e if "history" in e else e.split(":")[0]).value_counts())
print(results_df["status"].value_counts())
