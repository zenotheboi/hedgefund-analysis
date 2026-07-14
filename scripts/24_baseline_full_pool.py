"""Baseline model v2: corrects two errors in scripts/23_*.

1. scripts/23 only priced trials that had already survived the OLD
   EDGAR-matching pipeline (the 260-trial combined dataset) -- so despite
   changing the pricing DATE to remove EDGAR dependency, it silently kept
   the EDGAR-driven SAMPLE. This version starts from the actual chemically
   in-scope pool (04_pubchem_verified.csv, correctly filtered this time --
   see point 2) BEFORE any EDGAR search or filing-match filtering, so the
   sample itself is independent of the EDGAR-matching quality problem the
   whole session has been investigating, not just the price date.

2. 04_pubchem_verified.csv is a CANDIDATE pool that was checked against
   PubChem, not a pre-filtered result -- only rows where
   pubchem_verified_small_molecule_or_peptide == True are actually in
   scope (628 of 1839). Using the file unfiltered was a real bug caught
   by the user.

Ground truth label: this pool's own `outcome_category` field (success /
failure_efficacy_safety / business_termination / ambiguous_termination /
logistics_termination) -- this predates the session's later hidden-negative
label corrections, so it's closer to the original study's own labeling,
not our downstream patches. ambiguous_termination and logistics_termination
are excluded from the phase x outcome comparison (STATUS.md already flags
these as never manually re-read / genuinely unclear), same treatment as
the rest of the project gives them.

Pricing date: results_first_posted_date, same rationale as scripts/23.
"""
import sys
sys.path.insert(0, "src")

import re
import time
import pandas as pd
from hedgefund.prices import compute_abnormal_returns, short_window_car

PHASE_MAP = {
    "PHASE1": "Phase 1", "PHASE2": "Phase 2", "PHASE3": "Phase 3",
    "PHASE1/PHASE2": "Phase 1/2", "PHASE2/PHASE3": "Phase 2/3",
}
CATEGORY_MAP = {
    "success": "Success",
    "failure_efficacy_safety": "Failure",
    "business_termination": "Business Termination",
}

pool = pd.read_csv("data/interim/04_pubchem_verified.csv", low_memory=False)
verified = pool[pool["pubchem_verified_small_molecule_or_peptide"] == True].copy()
verified = verified.dropna(subset=["results_first_posted_date", "ticker"])
verified = verified[verified["outcome_category"].isin(CATEGORY_MAP.keys())]
verified["phase_clean"] = verified["phase"].map(PHASE_MAP)
verified["category_clean"] = verified["outcome_category"].map(CATEGORY_MAP)
verified = verified.dropna(subset=["phase_clean"])

print(f"{len(verified)} trials: correctly PubChem-verified, have a results_first_posted_date, "
      f"clean phase, and a clear (non-ambiguous) outcome label")

rows, errors = [], []
n = len(verified)
for i, (_, row) in enumerate(verified.iterrows()):
    try:
        result = compute_abnormal_returns(row["ticker"], row["results_first_posted_date"])
        short = short_window_car(result["event_window"], pre=2, post=2)
        rows.append({
            "nct_id": row["nct_id"], "ticker": row["ticker"],
            "phase_clean": row["phase_clean"], "category_clean": row["category_clean"],
            "results_posted": row["results_first_posted_date"],
            "baseline_car": short["car"], "baseline_raw": short["raw_return"],
        })
    except Exception as e:
        errors.append({"nct_id": row["nct_id"], "ticker": row["ticker"], "error": str(e)})
    if (i + 1) % 25 == 0:
        print(f"{i+1}/{n}")
    time.sleep(0.05)

out = pd.DataFrame(rows)
out.to_csv("data/processed/baseline_full_pool_model.csv", index=False)
print(f"\nPriced {len(out)} of {n}, {len(errors)} errors")
if errors:
    pd.DataFrame(errors).to_csv("data/interim/24_baseline_full_pool_errors.csv", index=False)
