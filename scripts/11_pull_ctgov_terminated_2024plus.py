"""Extend the pipeline forward in time: pull TERMINATED/WITHDRAWN/SUSPENDED
industry-sponsored Phase 1-3 drug trials completing after CTOD's May-2024
cutoff, directly from ClinicalTrials.gov -- no CTOD label dependency (see
notebook discussion). Reuses the existing ticker/SIC, modality, and
outcome-category triage code unchanged; only the source of raw trial
metadata changes.
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
    "AND AREA[StudyType]INTERVENTIONAL AND AREA[OverallStatus](TERMINATED OR WITHDRAWN OR SUSPENDED) "
    "AND AREA[InterventionType]DRUG AND AREA[CompletionDate]RANGE[2024-05-01,2026-07-14]"
)
FIELDS = (
    "NCTId,BriefTitle,OfficialTitle,Phase,OverallStatus,CompletionDate,"
    "LeadSponsorName,LeadSponsorClass,WhyStopped,InterventionType,InterventionName"
)


def fetch_all():
    rows = []
    page_token = None
    with tqdm(desc="Pulling CT.gov pages") as pbar:
        while True:
            params = {"filter.advanced": QUERY, "fields": FIELDS, "pageSize": 200}
            if page_token:
                params["pageToken"] = page_token
            resp = requests.get(API_BASE, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for study in data.get("studies", []):
                ps = study["protocolSection"]
                ident = ps.get("identificationModule", {})
                status = ps.get("statusModule", {})
                sponsor = ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
                design = ps.get("designModule", {})
                arms = ps.get("armsInterventionsModule", {})
                interventions = arms.get("interventions", [])
                rows.append({
                    "nct_id": ident.get("nctId"),
                    "brief_title": ident.get("briefTitle"),
                    "official_title": ident.get("officialTitle"),
                    "phase": ";".join(design.get("phases", [])),
                    "overall_status": status.get("overallStatus"),
                    "completion_date": status.get("completionDateStruct", {}).get("date"),
                    "why_stopped": status.get("whyStopped"),
                    "source": sponsor.get("name"),
                    "intervention_types": ";".join(i.get("type", "") for i in interventions),
                    "intervention_names": ";".join(i.get("name", "") for i in interventions),
                })
            pbar.update(len(data.get("studies", [])))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.15)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = fetch_all()
    print(f"\nPulled {len(df)} trials")
    df.to_csv("data/interim/11_ctgov_terminated_2024plus.csv", index=False)
    print(df["overall_status"].value_counts())
