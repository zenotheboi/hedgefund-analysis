"""Merge original + retried PubChem results, produce the final small-molecule/
peptide Approved-or-CRL BioPharmCatalyst dataset.
"""
import pandas as pd

IN = "data/interim/25_biopharmcatalyst_clean.csv"
ORIG_CACHE = "data/interim/26_pubchem_cache.csv"
RETRY_CACHE = "data/interim/26b_pubchem_retry_cache.csv"
OUT = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"

df = pd.read_csv(IN)
ac = df[df["Approved or CRL"].isin(["Approved", "CRL"])].copy()

orig = pd.read_csv(ORIG_CACHE)
retry = pd.read_csv(RETRY_CACHE)

# retry results only cover names orig marked not-found; overlay them
orig_indexed = orig.set_index("drug_name")
retry_indexed = retry.set_index("drug_name")
for name in retry_indexed.index:
    if retry_indexed.loc[name, "found"]:
        orig_indexed.loc[name, "found"] = True
        orig_indexed.loc[name, "cid"] = retry_indexed.loc[name, "cid"]
        orig_indexed.loc[name, "mw"] = retry_indexed.loc[name, "mw"]
        orig_indexed.loc[name, "is_small_molecule_or_peptide"] = retry_indexed.loc[name, "is_small_molecule_or_peptide"]

final_lookup = orig_indexed.reset_index()

merged = ac.merge(final_lookup, left_on="Drug Name", right_on="drug_name", how="left")
small_mol = merged[merged["is_small_molecule_or_peptide"] == True].copy()
small_mol = small_mol.drop(columns=["drug_name"])
small_mol.to_csv(OUT, index=False)

print(f"Approved/CRL rows (all modalities): {len(ac)}")
print(f"unique drug names: {ac['Drug Name'].nunique()}")
print(f"unique small-molecule/peptide names: {final_lookup['is_small_molecule_or_peptide'].sum()}")
print(f"small-molecule/peptide rows kept: {len(small_mol)}")
print(small_mol["Approved or CRL"].value_counts())
print(f"unique tickers: {small_mol['Ticker'].nunique()}")
