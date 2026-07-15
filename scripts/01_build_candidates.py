"""Day-1 pipeline step 1: filter CTOD human labels to industry-sponsored
Phase 1-3 trials and attach a candidate ticker/CIK via SEC fuzzy matching.

Modality (small molecule/peptide) filtering happens in script 02, since it
requires a per-trial ClinicalTrials.gov API call and we only want to spend
those calls on trials that already have a plausible ticker.
"""
import sys
sys.path.insert(0, "src")

import pandas as pd
from hedgefund.sec import load_company_tickers, match_sponsor_to_ticker, verify_pharma_sic

PHASES = ["PHASE1", "PHASE2", "PHASE3", "PHASE1/PHASE2", "PHASE2/PHASE3"]

def main():
    df = pd.read_csv("data/raw/ctod/human_labels_2020_2024.csv", low_memory=False)
    df = df[df["phase"].isin(PHASES) & (df["source_class"] == "INDUSTRY")].copy()
    print(f"Phase 1-3 + industry sponsored: {len(df)}")

    tickers = load_company_tickers("data/raw/sec/company_tickers.json")

    unique_sponsors = df["source"].dropna().unique()
    print(f"Unique sponsors to match: {len(unique_sponsors)}")

    sponsor_matches = {}
    sic_cache = {}
    for sponsor in unique_sponsors:
        m = match_sponsor_to_ticker(sponsor, tickers)
        if m["cik"]:
            if m["cik"] not in sic_cache:
                sic_cache[m["cik"]] = verify_pharma_sic(m["cik"])
            m["is_pharma_sic"] = sic_cache[m["cik"]]["is_pharma"]
            m["sic_description"] = sic_cache[m["cik"]]["sic_description"]
        else:
            m["is_pharma_sic"] = False
            m["sic_description"] = None
        sponsor_matches[sponsor] = m

    match_df = pd.DataFrame.from_dict(sponsor_matches, orient="index")
    match_df.index.name = "source"
    match_df = match_df.reset_index()

    out = df.merge(match_df, on="source", how="left")
    out.to_csv("data/interim/01_candidates_with_tickers.csv", index=False)

    matched = out[out["ticker"].notna()]
    print(f"Matched to a ticker: {len(matched)} ({matched['ticker'].nunique()} unique tickers)")
    print(f"  of which pharma-SIC verified: {matched['is_pharma_sic'].sum()}")
    print(f"Labels among ticker-matched: \n{matched['labels'].value_counts()}")

if __name__ == "__main__":
    main()
