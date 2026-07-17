"""Long-window (T-1yr..T+1yr) raw price trend around Approved/CRL events,
same method as notebooks/build_notebook.py section 13 (Phase 3 Success):
index each ticker's daily close to 100 at the event date, plot the full
year on each side. Raw price, NOT benchmark-adjusted -- complements the
tight T-2..T+2 CAR analysis by showing the shape of the move (run-up
before, drift after) which a short window can't show by design.
"""
import sys
import pandas as pd
import yfinance as yf

IN = "data/processed/biopharmcatalyst_small_molecule_car.csv"
OUT = "data/processed/biopharmcatalyst_long_window_prices.csv"

df = pd.read_csv(IN, parse_dates=["catalyst_date"])
df = df.dropna(subset=["car"])  # same 249 events already priced short-window

records = []
failed = []
for i, row in df.iterrows():
    ticker, event_date, status = row["ticker"], row["catalyst_date"], row["status"]
    start, end = event_date - pd.Timedelta(days=370), event_date + pd.Timedelta(days=370)
    try:
        px = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    except Exception as e:
        failed.append((ticker, str(event_date.date()), str(e)))
        continue
    if isinstance(px, pd.DataFrame):
        px = px.iloc[:, 0]
    if px.empty:
        failed.append((ticker, str(event_date.date()), "empty"))
        continue
    px.index = pd.to_datetime(px.index)
    anchor_pos = px.index.searchsorted(event_date)
    if anchor_pos >= len(px):
        failed.append((ticker, str(event_date.date()), "no_data_after_event"))
        continue
    indexed = px / px.iloc[anchor_pos] * 100
    days_from_event = (px.index - px.index[anchor_pos]).days
    records.extend({
        "event_id": i, "ticker": ticker, "status": status,
        "days_from_event": d, "indexed_price": float(v),
    } for d, v in zip(days_from_event, indexed))
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(df)}")

out_df = pd.DataFrame(records)
out_df.to_csv(OUT, index=False)

print(f"\nevents priced (long window): {out_df['event_id'].nunique()} / {len(df)}")
print(f"failed: {len(failed)}")

# Quick summary: average indexed price at T-365, T0, T+365 by status
for status in ["Approved", "CRL"]:
    g = out_df[out_df["status"] == status]
    near_start = g[(g["days_from_event"] >= -370) & (g["days_from_event"] <= -360)]["indexed_price"].mean()
    at_zero = g[g["days_from_event"] == 0]["indexed_price"].mean()
    near_end = g[(g["days_from_event"] >= 360) & (g["days_from_event"] <= 370)]["indexed_price"].mean()
    print(f"{status}: T-365 avg={near_start:.1f}  T0={at_zero:.1f}  T+365 avg={near_end:.1f}  "
          f"n_events={g['event_id'].nunique()}")
