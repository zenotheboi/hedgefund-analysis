"""Day-1 pipeline step 5 (final): reclassify the 12 confirmed/candidate hidden
negatives found by manual filing review, fold NCT03990363 in from the
unresolved pool (it now has a verified date), then assemble the final
event dataset with price data.

Reclassification is logged, not silent -- CTOD's original label is kept
alongside the corrected one so the correction is auditable.
"""
import sys
sys.path.insert(0, "src")

import json
import pandas as pd
from tqdm import tqdm

from hedgefund.prices import compute_abnormal_returns

CONFIRMED_HIDDEN_NEGATIVES = {
    "NCT03745820": "BIIB104 TALLY study: did not meet primary/secondary endpoints",
    "NCT03931291": "eprenetapopt+azacitidine TP53-MDS: failed primary endpoint (complete remission)",
    "NCT04402866": "nezulcitinib COVID ALI: did not meet primary endpoint",
    "NCT03750552": "ampreloxetine nOH: did not meet primary endpoint",
    "NCT04657666": "nabiximols RELEASE MSS1 (NCT ID cited by name): did not meet primary endpoint",
    "NCT05047601": "Paxlovid EPIC-PEP: primary endpoint not met",
    "NCT04410991": "tolebrutinib GEMINI 1: did not show significance in primary endpoint",
    "NCT04410978": "tolebrutinib GEMINI 2: did not show significance in primary endpoint",
    "NCT03990363": "verinurad: AstraZeneca discontinued development (R&D impairment disclosure)",
}
NUANCED_MIXED_RESULT_NEGATIVES = {
    "NCT02892149": "vadadustat PRO2TECT: met efficacy, missed primary SAFETY endpoint (MACE non-inferiority)",
    "NCT02680574": "vadadustat PRO2TECT: met efficacy, missed primary SAFETY endpoint (MACE non-inferiority)",
    "NCT02865850": "vadadustat PRO2TECT: met efficacy, missed primary SAFETY endpoint (MACE non-inferiority)",
}
RECLASSIFY = {**CONFIRMED_HIDDEN_NEGATIVES, **NUANCED_MIXED_RESULT_NEGATIVES}


def main():
    resolved = pd.read_csv("data/interim/05_filing_search_results.csv", low_memory=False)

    # fold in NCT03990363 from the unresolved pool, now that script 07 found
    # and verified a real date/context for it
    flagged_unresolved = pd.read_csv("data/interim/07_flagged_from_unresolved.csv")
    rescue_row = flagged_unresolved[flagged_unresolved["nct_id"] == "NCT03990363"]
    if not rescue_row.empty:
        idx = resolved[resolved["nct_id"] == "NCT03990363"].index
        resolved.loc[idx, "resolution_method"] = "manual_hidden_negative_scan"
        resolved.loc[idx, "verified_filing_url"] = rescue_row.iloc[0]["url"]
        resolved.loc[idx, "verified_filing_date"] = rescue_row.iloc[0]["file_date"]
        resolved.loc[idx, "verified_context"] = rescue_row.iloc[0]["context"]

    dataset = resolved[resolved["resolution_method"].isin(
        ["edgar_primary", "news_rescue", "manual_hidden_negative_scan"])].copy()

    dataset["ctod_original_outcome_category"] = dataset["outcome_category"]
    dataset["ctod_original_label"] = dataset["labels"]
    dataset["label_correction_reason"] = dataset["nct_id"].map(RECLASSIFY)

    reclass_mask = dataset["nct_id"].isin(RECLASSIFY)
    dataset.loc[reclass_mask, "outcome_category"] = "failure_efficacy_safety"
    dataset.loc[reclass_mask, "labels"] = 0.0

    print(f"Final resolved dataset: {len(dataset)}")
    print(dataset["outcome_category"].value_counts())
    print(f"\nReclassified (label corrected from CTOD's original): {reclass_mask.sum()}")

    dataset.to_csv("data/interim/08_final_candidates.csv", index=False)

if __name__ == "__main__":
    main()
