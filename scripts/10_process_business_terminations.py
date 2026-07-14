"""Extend the pipeline to the business_termination bucket, which was
categorized early on but never taken through date-finding/verification/
pricing -- needed now for a 3-way phase x outcome-category price comparison.
Reuses the same verified-filing-search machinery as script 04.
"""
import sys
sys.path.insert(0, "src")

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

import pandas as pd
import requests
from tqdm import tqdm

from hedgefund.sec import get_all_filings_in_range
from hedgefund.news_fallback import load_news_index, candidate_dates_in_window

sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("s04", "scripts/04_find_announcement_dates.py")
s04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s04)

MAX_WORKERS = 5


def main():
    df = pd.read_csv("data/interim/04_pubchem_verified.csv", low_memory=False)
    df = df[df["pubchem_verified_small_molecule_or_peptide"] == True].copy()
    df = df[df["outcome_category"] == "business_termination"]
    print(f"Business-termination candidates: {len(df)}")

    news_index = load_news_index("data/raw/ctod/news_lfs.csv")

    filings_by_cik = {}
    for cik_raw, group in df.groupby("cik"):
        cik = str(int(cik_raw)).zfill(10)
        starts = pd.to_datetime(group["completion_date"])
        date_from = starts.min().strftime("%Y-%m-%d")
        date_to = (starts.max() + pd.Timedelta(days=400)).strftime("%Y-%m-%d")
        try:
            filings_by_cik[cik] = get_all_filings_in_range(cik, s04.FORMS, date_from, date_to)
        except requests.RequestException as e:
            filings_by_cik[cik] = []
            print(f"WARN CIK {cik}: {e}")

    def resolve_trial(row):
        cik = str(int(row["cik"])).zfill(10)
        names = [n.strip() for n in str(row["intervention_names"]).split(";") if n.strip()]
        title = row["official_title"] if pd.notna(row.get("official_title")) else row["brief_title"]
        start = row["completion_date"]
        end = (pd.Timestamp(start) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        candidates = sorted(
            [f for f in filings_by_cik.get(cik, []) if start <= f["filingDate"] <= end],
            key=lambda f: f["filingDate"],
        )
        verified = s04.verify_candidate_accessions(cik, candidates, names, title)
        method = "edgar_primary" if verified else None
        if not verified:
            news_hits = candidate_dates_in_window(row["nct_id"], news_index, row["completion_date"])
            for nh in news_hits:
                lo = (nh["date"] - timedelta(days=5)).strftime("%Y-%m-%d")
                hi = (nh["date"] + timedelta(days=5)).strftime("%Y-%m-%d")
                rescue = [f for f in filings_by_cik.get(cik, []) if lo <= f["filingDate"] <= hi]
                verified = s04.verify_candidate_accessions(cik, rescue, names, title)
                if verified:
                    method = "news_rescue"
                    break
        if not verified:
            method = "unresolved_needs_manual_check"
        return row["nct_id"], method, verified

    methods, verified_hits = {}, {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(resolve_trial, row) for _, row in df.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures)):
            nct_id, method, verified = fut.result()
            methods[nct_id] = method
            verified_hits[nct_id] = verified

    df["resolution_method"] = df["nct_id"].map(methods)
    df["verified_filing_url"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("url"))
    df["verified_filing_date"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("file_date"))
    df["verified_context"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("context"))

    df.to_csv("data/interim/10_business_termination_filings.csv", index=False)
    print(df["resolution_method"].value_counts(dropna=False))

if __name__ == "__main__":
    main()
