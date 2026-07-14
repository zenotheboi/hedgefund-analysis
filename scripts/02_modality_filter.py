"""Day-1 pipeline step 2: apply the small-molecule/peptide modality filter
via ClinicalTrials.gov intervention data. This was supposed to run as part
of building the candidate pool but was skipped -- running it now against
data/interim/02_categorized_candidates.csv.
"""
import sys
sys.path.insert(0, "src")

import pandas as pd
from tqdm import tqdm
from hedgefund.ctgov import fetch_and_classify

def main():
    df = pd.read_csv("data/interim/02_categorized_candidates.csv", low_memory=False)
    print(f"Candidates before modality filter: {len(df)}")

    results = []
    for nct_id in tqdm(df["nct_id"], desc="CT.gov modality check"):
        results.append(fetch_and_classify(nct_id))

    mod_df = pd.DataFrame(results)
    out = df.merge(mod_df, on="nct_id", how="left")
    out.to_csv("data/interim/03_modality_checked.csv", index=False)

    print(out["modality"].value_counts(dropna=False))
    print()
    print("By outcome_category among small_molecule_candidate:")
    print(out[out["modality"] == "small_molecule_candidate"]["outcome_category"].value_counts())

if __name__ == "__main__":
    main()
