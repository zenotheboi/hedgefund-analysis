"""Completed trials (post-CTOD-cutoff) with NO posted structured results on
CT.gov -- no p-value pre-filter available, so every survivor of ticker/
modality filtering gets read directly via EDGAR (same as always), keeping
whatever the filing actually says -- positive or negative, not just hunting
for failures. Pulled and processed in small batches (BATCH_SIZE) rather than
all 3,283 at once, to check yield before committing more effort.
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
    "AND NOT AREA[ResultsFirstPostDate]RANGE[2020-01-01,2026-12-31]"
)
FIELDS = "NCTId,BriefTitle,OfficialTitle,Phase,CompletionDate,LeadSponsorName,InterventionType,InterventionName"
BATCH_SIZE = 300


def fetch_batch(limit=BATCH_SIZE):
    rows = []
    page_token = None
    with tqdm(desc="Pulling CT.gov batch", total=limit) as pbar:
        while len(rows) < limit:
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
                interventions = ps.get("armsInterventionsModule", {}).get("interventions", [])
                rows.append({
                    "nct_id": ident.get("nctId"),
                    "brief_title": ident.get("briefTitle"),
                    "official_title": ident.get("officialTitle"),
                    "phase": ";".join(design.get("phases", [])),
                    "completion_date": status.get("completionDateStruct", {}).get("date"),
                    "source": sponsor.get("name"),
                    "intervention_types": ";".join(i.get("type", "") for i in interventions),
                    "intervention_names": ";".join(i.get("name", "") for i in interventions),
                })
                pbar.update(1)
                if len(rows) >= limit:
                    break
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.1)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = fetch_batch()
    print(f"\nPulled {len(df)} trials (no posted results)")
    df.to_csv("data/interim/14_completed_no_results_batch1.csv", index=False)
