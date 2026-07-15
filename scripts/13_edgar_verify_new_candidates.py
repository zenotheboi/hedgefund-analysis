"""EDGAR verification for the 33 new candidates found via the CT.gov-direct
extension (terminated-with-efficacy-reason + completed-with-missed-
significance tracks). Reuses the exact same per-CIK-cached search +
verify_filing_mentions_trial logic as script 04 -- only the candidate source
differs.
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


def load_combined_candidates():
    t = pd.read_csv("data/interim/11_failure_candidates_pubchem.csv", low_memory=False)
    t = t[t["pubchem_verified"]].copy()
    t["outcome_category"] = "failure_efficacy_safety"
    t["source_track"] = "ctgov_terminated_2024plus"

    c = pd.read_csv("data/interim/12_completed_pubchem.csv", low_memory=False)
    c = c[c["pubchem_verified"]].copy()
    c["intervention_names"] = c["intervention_names_y"]
    c["outcome_category"] = "failure_efficacy_safety"
    c["source_track"] = "ctgov_completed_missed_significance"

    cols = ["nct_id", "brief_title", "official_title", "phase", "completion_date",
            "source", "ticker", "cik", "intervention_names", "outcome_category", "source_track"]
    combined = pd.concat([t[cols], c[cols]], ignore_index=True)

    # dedupe against trials already in the existing dataset
    existing = pd.read_csv("data/interim/08_final_candidates.csv", low_memory=False)
    combined = combined[~combined["nct_id"].isin(existing["nct_id"])]
    return combined.drop_duplicates(subset="nct_id")


def main():
    df = load_combined_candidates()
    print(f"New candidates to verify: {len(df)}")
    print(df["source_track"].value_counts())

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
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(resolve_trial, row) for _, row in df.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures)):
            nct_id, method, verified = fut.result()
            methods[nct_id] = method
            verified_hits[nct_id] = verified

    df["resolution_method"] = df["nct_id"].map(methods)
    df["verified_filing_url"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("url"))
    df["verified_filing_date"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("file_date"))
    df["verified_context"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("context"))

    df.to_csv("data/interim/13_new_candidates_edgar_verified.csv", index=False)
    json.dump(verified_hits, open("data/interim/13_new_candidates_hits.json", "w"), indent=2)

    print(df["resolution_method"].value_counts(dropna=False))

if __name__ == "__main__":
    main()
