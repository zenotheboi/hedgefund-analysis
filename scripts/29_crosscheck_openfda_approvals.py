"""Cross-check BioPharmCatalyst 'Approved' events against openFDA Drugs@FDA
(free, public, official -- no login/paywall). For each Approved row, look up
the drug's FDA submission history and check whether an actual FDA approval
('AP' status) exists within +-45 days of BioPharmCatalyst's Catalyst Date.

This doesn't replace BioPharmCatalyst as a source, but gives an independent,
free way to spot-check date accuracy on the Approved side (roughly 3/4 of
the small-molecule dataset). CRLs are cross-checked separately via SEC EDGAR
(script 30) since openFDA doesn't systematically expose CRL dates.
"""
import re
import sys
import time
import requests
import pandas as pd

IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
OUT = "data/interim/29_openfda_crosscheck.csv"

WINDOW_DAYS = 45


def clean_candidates(raw: str) -> list:
    name = raw.strip()
    cands = []
    paren = re.search(r"\(([^)]+)\)", name)
    if paren:
        cands.append(paren.group(1).strip())
    no_paren = re.sub(r"\([^)]*\)", "", name).strip()
    before_dash = re.split(r"\s+-\s+", no_paren)[0].strip()
    if before_dash:
        cands.append(before_dash)
    cands.append(name)
    seen, out = set(), []
    for c in cands:
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


def query_openfda(name: str, timeout=15) -> list:
    """Return list of (submission_type, submission_status_date) for AP submissions."""
    out = []
    for field in ["openfda.brand_name", "openfda.generic_name", "openfda.substance_name"]:
        url = "https://api.fda.gov/drug/drugsfda.json"
        params = {"search": f'{field}:"{name}"', "limit": 5}
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            continue
        for result in data.get("results", []):
            for sub in result.get("submissions", []):
                if sub.get("submission_status") == "AP" and sub.get("submission_status_date"):
                    out.append((sub.get("submission_type"), sub["submission_status_date"]))
        if out:
            break
    return out


df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
approved = df[df["Approved or CRL"] == "Approved"].copy()

results = []
for i, row in approved.iterrows():
    cands = clean_candidates(row["Drug Name"])
    bpc_date = row["Catalyst Date"]
    match = None
    tried = []
    for cand in cands:
        tried.append(cand)
        subs = query_openfda(cand)
        time.sleep(0.2)
        if not subs:
            continue
        for sub_type, date_str in subs:
            fda_date = pd.Timestamp(date_str)
            delta = abs((fda_date - bpc_date).days)
            if match is None or delta < match["delta_days"]:
                match = {"matched_name": cand, "fda_date": str(fda_date.date()),
                         "submission_type": sub_type, "delta_days": delta}
        if match and match["delta_days"] <= WINDOW_DAYS:
            break

    results.append({
        "ticker": row["Ticker"], "drug_name": row["Drug Name"],
        "bpc_catalyst_date": str(bpc_date.date()),
        "candidates_tried": "|".join(tried),
        **(match or {"matched_name": None, "fda_date": None, "submission_type": None, "delta_days": None}),
        "confirmed": bool(match and match["delta_days"] <= WINDOW_DAYS),
    })
    if (len(results)) % 25 == 0:
        print(f"  {len(results)}/{len(approved)}")

out_df = pd.DataFrame(results)
out_df.to_csv(OUT, index=False)

n_confirmed = out_df["confirmed"].sum()
n_found_no_match = out_df["fda_date"].notna().sum() - n_confirmed
n_not_found = out_df["fda_date"].isna().sum()
print(f"\nApproved rows checked: {len(out_df)}")
print(f"confirmed (FDA AP date within {WINDOW_DAYS}d of BPC date): {n_confirmed}")
print(f"found in openFDA but date mismatch: {n_found_no_match}")
print(f"not found in openFDA at all: {n_not_found}")
if n_found_no_match:
    print("\nmismatches:")
    print(out_df[out_df["fda_date"].notna() & ~out_df["confirmed"]][
        ["ticker", "drug_name", "bpc_catalyst_date", "fda_date", "delta_days"]
    ].to_string())
