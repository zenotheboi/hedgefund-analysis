"""Cross-check BioPharmCatalyst 'CRL' events against SEC EDGAR full-text
search (free, public, no login). For each CRL row, search the company's own
CIK for 8-K/6-K filings mentioning "Complete Response Letter" within a
window around BioPharmCatalyst's Catalyst Date.

Reuses src/hedgefund/sec.py, same approach as the CTOD/EDGAR track's filing
search (see STATUS.md) -- this is an independent confirmation channel, not
a replacement for BioPharmCatalyst.
"""
import json
import sys
import time
import pandas as pd

sys.path.insert(0, "src")
from hedgefund.sec import fulltext_search

IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
TICKERS_JSON = "data/raw/sec/company_tickers.json"
OUT = "data/interim/30_edgar_crl_crosscheck.csv"

WINDOW_DAYS = 30

with open(TICKERS_JSON) as f:
    raw = json.load(f)
ticker_to_cik = {v["ticker"]: str(v["cik_str"]).zfill(10) for v in raw.values()}

df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
crls = df[df["Approved or CRL"] == "CRL"].copy()

results = []
for i, row in crls.iterrows():
    ticker = row["Ticker"]
    cik = ticker_to_cik.get(ticker)
    bpc_date = row["Catalyst Date"]
    date_from = (bpc_date - pd.Timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    date_to = (bpc_date + pd.Timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")

    if cik is None:
        results.append({"ticker": ticker, "drug_name": row["Drug Name"],
                         "bpc_catalyst_date": str(bpc_date.date()), "cik": None,
                         "hits": 0, "confirmed": False, "error": "ticker_not_in_sec"})
        continue

    try:
        hits = fulltext_search(cik, forms="8-K,6-K", date_from=date_from, date_to=date_to,
                                query='"Complete Response Letter"')
        error = None
    except Exception as e:
        hits, error = [], str(e)

    results.append({
        "ticker": ticker, "drug_name": row["Drug Name"],
        "bpc_catalyst_date": str(bpc_date.date()), "cik": cik,
        "hits": len(hits), "confirmed": len(hits) > 0, "error": error,
        "filing_dates": "|".join(h["_source"].get("file_date", "") for h in hits[:5]) if hits else "",
    })
    if len(results) % 20 == 0:
        print(f"  {len(results)}/{len(crls)}")

out_df = pd.DataFrame(results)
out_df.to_csv(OUT, index=False)

n_confirmed = out_df["confirmed"].sum()
n_no_cik = (out_df["cik"].isna()).sum()
print(f"\nCRL rows checked: {len(out_df)}")
print(f"confirmed (>=1 8-K/6-K mentions 'Complete Response Letter' within +-{WINDOW_DAYS}d): {n_confirmed}")
print(f"ticker not found in SEC company list: {n_no_cik}")
print(f"unconfirmed (searched, no hit): {len(out_df) - n_confirmed - n_no_cik}")
