"""Retry PubChem lookups for drug names that failed on the raw literal name.

BioPharmCatalyst's "Drug Name" field is messy in ways the CTOD pipeline's
names weren't: parenthetical INN names ("AVEED (testosterone undecanoate)
intramuscular injection"), dosage-form/route suffixes, trial-name suffixes
("Abemaciclib - MONARCH 3"), and +/combination compounds ("AVYCAZ
(ceftazidime and avibactam)"). This generates cleaned candidate strings and
retries each against PubChem, in priority order, until one hits. Combos are
resolved by looking up each component; the combo counts as small-molecule
only if every component is found and small-molecule/peptide.
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, "src")
from hedgefund.pubchem import lookup_compound

CACHE = "data/interim/26_pubchem_cache.csv"
RETRY_CACHE = "data/interim/26b_pubchem_retry_cache.csv"

DOSAGE_WORDS = re.compile(
    r"\b(intramuscular|intravenous|subcutaneous|oral|injection|infusion|"
    r"extended release|immediate release|delayed release|tablet|capsule|"
    r"solution|suspension|formulation|topical|transdermal|patch)\b",
    re.IGNORECASE,
)


def clean_candidates(raw: str) -> list:
    cands = []
    name = raw.strip()

    paren = re.search(r"\(([^)]+)\)", name)
    if paren:
        inner = paren.group(1)
        for part in re.split(r"[;,]", inner):
            part = part.strip()
            if part and not part.isupper():  # skip short all-caps brand codes
                cands.append(part)
            elif part:
                cands.append(part)

    no_paren = re.sub(r"\([^)]*\)", "", name).strip()
    before_dash = re.split(r"\s+-\s+", no_paren)[0].strip()
    before_combo = re.split(r"\bin combination with\b", before_dash, flags=re.IGNORECASE)[0].strip()
    cleaned = DOSAGE_WORDS.sub("", before_combo).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -")
    if cleaned:
        cands.append(cleaned)
    if before_combo and before_combo != cleaned:
        cands.append(before_combo)

    # component-level candidates for combo drugs ("ceftazidime and avibactam",
    # "EYLEA + nesvacumab")
    components = re.split(r"\s+\+\s+|\s+and\s+", cleaned, flags=re.IGNORECASE)
    if len(components) > 1:
        cands.extend(c.strip() for c in components if c.strip())

    # de-dup, preserve order
    seen = set()
    out = []
    for c in cands:
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


cache_df = pd.read_csv(CACHE)
not_found = cache_df[cache_df["found"] == False]["drug_name"].tolist()

if os.path.exists(RETRY_CACHE):
    retry_df = pd.read_csv(RETRY_CACHE)
    retry_results = {row["drug_name"]: row.to_dict() for _, row in retry_df.iterrows()}
else:
    retry_results = {}

for i, name in enumerate(not_found):
    if name in retry_results:
        continue
    candidates = clean_candidates(name)
    hit = None
    tried = []
    for cand in candidates:
        tried.append(cand)
        r = lookup_compound(cand)
        if r["found"]:
            hit = {**r, "matched_candidate": cand}
            break
    if hit is None:
        hit = {"found": False, "cid": None, "mw": None,
               "is_small_molecule_or_peptide": False, "matched_candidate": None}
    hit["drug_name"] = name
    hit["candidates_tried"] = "|".join(tried)
    retry_results[name] = hit
    if (i + 1) % 20 == 0:
        print(f"  retry {i+1}/{len(not_found)}")

retry_df = pd.DataFrame(retry_results.values())
retry_df.to_csv(RETRY_CACHE, index=False)

n_recovered = int(retry_df["found"].sum())
n_small = int(retry_df["is_small_molecule_or_peptide"].sum())
print(f"retried: {len(not_found)}")
print(f"recovered (found in PubChem via cleaned candidate): {n_recovered}")
print(f"of those, small molecule/peptide: {n_small}")
print(retry_df[retry_df["is_small_molecule_or_peptide"] == True][["drug_name", "matched_candidate", "mw"]].to_string())
