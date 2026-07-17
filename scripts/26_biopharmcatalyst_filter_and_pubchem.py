"""Filter BioPharmCatalyst to Approved/CRL rows only, then verify each unique
drug name against PubChem to keep small-molecule/peptide compounds only
(reuses src/hedgefund/pubchem.py, same MW<=8000 Da rule as the CTOD pipeline).
"""
import os
import sys
import pandas as pd

sys.path.insert(0, "src")
from hedgefund.pubchem import lookup_compound

IN = "data/interim/25_biopharmcatalyst_clean.csv"
CACHE = "data/interim/26_pubchem_cache.csv"
OUT = "data/interim/26_biopharmcatalyst_approved_crl_small_molecule.csv"

df = pd.read_csv(IN)
ac = df[df["Approved or CRL"].isin(["Approved", "CRL"])].copy()

# Some "drug names" are combos ("EYLEA + nesvacumab") or include a
# parenthetical brand name ("SL-401 (Elzonris)") -- try the raw name first,
# PubChem lookup just won't find combos/codes and we flag those as
# not-found rather than silently guessing.
unique_names = sorted(ac["Drug Name"].dropna().unique())

if os.path.exists(CACHE):
    cache_df = pd.read_csv(CACHE)
    cached = dict(zip(cache_df["drug_name"], cache_df.to_dict("records")))
else:
    cached = {}

rows = []
for i, name in enumerate(unique_names):
    if name in cached:
        rows.append(cached[name])
        continue
    result = lookup_compound(name)
    rows.append({"drug_name": name, **result})
    if (i + 1) % 25 == 0:
        print(f"  pubchem lookup {i+1}/{len(unique_names)}")

cache_df = pd.DataFrame(rows)
cache_df.to_csv(CACHE, index=False)

merged = ac.merge(cache_df, left_on="Drug Name", right_on="drug_name", how="left")
n_found = int(merged["found"].sum())
n_small = int(merged["is_small_molecule_or_peptide"].sum())

small_mol = merged[merged["is_small_molecule_or_peptide"] == True].copy()
small_mol.to_csv(OUT, index=False)

print(f"Approved/CRL rows: {len(ac)}")
print(f"unique drug names: {len(unique_names)}")
print(f"PubChem found: {n_found} / {len(unique_names)}")
print(f"small molecule/peptide rows kept: {len(small_mol)} (status split: "
      f"{small_mol['Approved or CRL'].value_counts().to_dict()})")
print(f"not found in PubChem (likely combos/biologics/codes), sample:")
print(cache_df[cache_df["found"] == False]["drug_name"].head(20).tolist())
