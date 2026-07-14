"""EDGAR rematch rebuild, stage 1: pull acronym + primary_completion_date +
results_first_posted_date from the ClinicalTrials.gov API for all 260
trials. These are the inputs the discovery-stage search (stage 2) needs:
acronym (or lack of one) picks the query term, and the date pair picks the
search window anchor. Rate-limited (0.25s/request) to be polite to CT.gov.
"""
import sys
sys.path.insert(0, "src")

import time
import requests
import pandas as pd

df = pd.read_csv("data/processed/combined_phase_outcome_analysis.csv")
nct_ids = df["nct_id"].tolist()

rows = []
for i, nct in enumerate(nct_ids):
    try:
        r = requests.get(f"https://clinicaltrials.gov/api/v2/studies/{nct}", timeout=15)
        r.raise_for_status()
        d = r.json()
        proto = d.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        rows.append({
            "nct_id": nct,
            "acronym": ident.get("acronym"),
            "primary_completion": status.get("primaryCompletionDateStruct", {}).get("date"),
            "results_posted": status.get("resultsFirstPostDateStruct", {}).get("date"),
        })
    except Exception as e:
        rows.append({"nct_id": nct, "error": str(e)})
    if (i + 1) % 25 == 0:
        print(f"{i+1}/{len(nct_ids)}")
    time.sleep(0.25)

out = pd.DataFrame(rows)
out.to_csv("data/interim/20_ctgov_acronym_dates_all260.csv", index=False)
print(f"\nDone. {out['acronym'].notna().sum()} of {len(out)} trials have a CT.gov acronym.")
print(f"{out['primary_completion'].notna().sum()} have a primary_completion_date.")
