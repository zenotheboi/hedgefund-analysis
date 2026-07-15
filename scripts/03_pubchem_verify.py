"""Day-1 pipeline step 3: verify modality against PubChem directly, per the
methodology's mandatory small-molecule/peptide filter. CT.gov's intervention
type field alone isn't trustworthy (see ctgov.py docstring), so this cross-
references every candidate's experimental-arm drug name against PubChem.
"""
import sys
sys.path.insert(0, "src")

import pandas as pd
from tqdm import tqdm
from hedgefund.pubchem import lookup_compound

def main():
    df = pd.read_csv("data/interim/03_modality_checked.csv", low_memory=False)
    print(f"Rows before PubChem verification: {len(df)}")
    print(df["modality"].value_counts(dropna=False))

    # CT.gov's own DISQUALIFYING_TYPES already ruled out explicit
    # biological/genetic/device trials ("excluded"/"no_drug_intervention").
    # PubChem-verify anything CT.gov called drug-typed, whether or not the
    # suffix heuristic flagged it -- the doc calls this filter mandatory.
    to_check = df[df["modality"].isin(["small_molecule_candidate", "needs_name_lookup"])].copy()

    unique_names = set()
    for names in to_check["intervention_names"].dropna():
        unique_names.update(n.strip() for n in names.split(";") if n.strip())
    print(f"Unique experimental-arm drug names to verify: {len(unique_names)}")

    pubchem_cache = {}
    for name in tqdm(unique_names, desc="PubChem lookup"):
        pubchem_cache[name] = lookup_compound(name)

    def verify_row(names):
        if pd.isna(names):
            return False
        return any(pubchem_cache.get(n.strip(), {}).get("is_small_molecule_or_peptide", False)
                    for n in names.split(";") if n.strip())

    to_check["pubchem_verified_small_molecule_or_peptide"] = to_check["intervention_names"].apply(verify_row)

    out = df.merge(
        to_check[["nct_id", "pubchem_verified_small_molecule_or_peptide"]], on="nct_id", how="left"
    )
    out["pubchem_verified_small_molecule_or_peptide"] = out["pubchem_verified_small_molecule_or_peptide"].fillna(False)
    out.to_csv("data/interim/04_pubchem_verified.csv", index=False)

    final = out[out["pubchem_verified_small_molecule_or_peptide"]]
    print(f"\nPubChem-verified small molecule/peptide trials: {len(final)}")
    print(final["outcome_category"].value_counts())

if __name__ == "__main__":
    main()
