"""Completed trials (post-CTOD-cutoff) that have posted structured results.
Extract the primary outcome's reported p-value directly from CT.gov's own
data -- an unbiased, scalable "negative signal" for completed trials, which
otherwise have no why_stopped-equivalent triage field. Still needs EDGAR
verification afterward for a real announcement date/market reaction; this is
a candidate-discovery step, not a replacement for verification.
"""
import sys
sys.path.insert(0, "src")

import time
import requests
import pandas as pd
from tqdm import tqdm

API_BASE = "https://clinicaltrials.gov/api/v2/studies"
QUERY = (
    "AREA[LeadSponsorClass]INDUSTRY AND AREA[Phase](PHASE1 OR PHASE2 OR PHASE3) "
    "AND AREA[StudyType]INTERVENTIONAL AND AREA[OverallStatus]COMPLETED "
    "AND AREA[InterventionType]DRUG AND AREA[CompletionDate]RANGE[2024-05-01,2026-07-14] "
    "AND AREA[ResultsFirstPostDate]RANGE[2020-01-01,2026-12-31]"
)
LIST_FIELDS = "NCTId,BriefTitle,OfficialTitle,Phase,CompletionDate,LeadSponsorName"


def fetch_nct_ids():
    ids = []
    page_token = None
    with tqdm(desc="Listing candidates") as pbar:
        while True:
            params = {"filter.advanced": QUERY, "fields": LIST_FIELDS, "pageSize": 200}
            if page_token:
                params["pageToken"] = page_token
            resp = requests.get(API_BASE, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for study in data.get("studies", []):
                ps = study["protocolSection"]
                ids.append({
                    "nct_id": ps["identificationModule"]["nctId"],
                    "brief_title": ps["identificationModule"].get("briefTitle"),
                    "official_title": ps["identificationModule"].get("officialTitle"),
                    "phase": ";".join(ps.get("designModule", {}).get("phases", [])),
                    "completion_date": ps.get("statusModule", {}).get("completionDateStruct", {}).get("date"),
                    "source": ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
                })
            pbar.update(len(data.get("studies", [])))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.1)
    return pd.DataFrame(ids)


def get_primary_pvalue(nct_id, sleep=0.1):
    try:
        resp = requests.get(f"{API_BASE}/{nct_id}", params={"fields": "NCTId,ResultsSection,ArmsInterventionsModule"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None, None, None
    finally:
        time.sleep(sleep)

    om = data.get("resultsSection", {}).get("outcomeMeasuresModule", {})
    measures = om.get("outcomeMeasures", [])
    primary = [m for m in measures if m.get("type") == "PRIMARY"]
    if not primary:
        return None, None, None
    m = primary[0]
    analyses = m.get("analyses", [])
    if not analyses:
        return None, m.get("title"), None
    p_raw = analyses[0].get("pValue")
    names = [i.get("name", "") for i in data.get("protocolSection", {})
             .get("armsInterventionsModule", {}).get("interventions", [])]
    try:
        p = float(p_raw.replace("<", "").replace(">", "").replace("=", "").strip())
    except (ValueError, AttributeError):
        p = None
    return p, m.get("title"), ";".join(names)


if __name__ == "__main__":
    df = fetch_nct_ids()
    print(f"\nListed {len(df)} completed trials with posted results")

    pvals, titles, names = [], [], []
    for nct in tqdm(df["nct_id"], desc="Fetching primary outcome p-values"):
        p, title, n = get_primary_pvalue(nct)
        pvals.append(p)
        titles.append(title)
        names.append(n)
    df["primary_outcome_title"] = titles
    df["primary_pvalue"] = pvals
    df["intervention_names"] = names

    df.to_csv("data/interim/12_ctgov_completed_pvalues.csv", index=False)

    has_p = df["primary_pvalue"].notna()
    print(f"Have a parseable primary-outcome p-value: {has_p.sum()} of {len(df)}")
    non_sig = df[has_p & (df["primary_pvalue"] >= 0.05)]
    print(f"p >= 0.05 (missed significance -- candidate negative signal): {len(non_sig)}")
