"""ClinicalTrials.gov v2 API helpers for modality classification."""
import re
import time
import requests

API_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Intervention types that disqualify a trial from the small-molecule/peptide scope.
DISQUALIFYING_TYPES = {
    "BIOLOGICAL", "GENETIC", "DEVICE", "PROCEDURE", "RADIATION",
    "COMBINATION_PRODUCT",
}
# Everything else present alongside DRUG (behavioral, dietary supplement, other)
# is tolerated as a co-intervention, since the trial can still be evaluating a
# small-molecule/peptide drug as the primary intervention.
ALLOWED_WITH_DRUG = {"DRUG", "OTHER", "DIETARY_SUPPLEMENT", "BEHAVIORAL"}

# CT.gov's own intervention "type" field is sponsor-reported and routinely
# mis-tags antibody/protein therapeutics as plain "DRUG" (e.g. KSI-301 /
# tarcocimab tedromer, an antibody biopolymer conjugate, is tagged DRUG).
# INN stem suffixes catch these even when CT.gov's type tag doesn't.
# Note: peptides (e.g. "-tide" as in semaglutide) are explicitly IN SCOPE
# per the methodology, so that stem is deliberately NOT in this list.
BIOLOGIC_INN_SUFFIXES = re.compile(
    r"(mab|cept|nercept|ciclib$|zumab|ximab|umab|omab|"  # antibodies / fusion proteins
    r"feron|kinra|leukin|"  # interferons / interleukins / receptor antagonists
    r"gene|parvovec|vec$|"  # gene therapy
    r"cel$|leucel|"  # cell therapy
    r"ase$|stim$)",  # enzymes / growth factors
    re.IGNORECASE,
)
# Sponsor codes (e.g. "KSI-301", "ABC-1234") carry no morphological signal at
# all -- flag these as needing an actual look-up rather than guessing.
SPONSOR_CODE_PATTERN = re.compile(r"^[A-Z]{2,6}[-\s]?\d{2,6}[A-Za-z]?$")


NON_EXPERIMENTAL_ARM_TYPES = {
    "ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR", "NO_INTERVENTION",
}


def get_intervention_types(nct_id: str, timeout: int = 15) -> dict:
    """Return experimental-arm intervention types/names for one NCT ID.

    Restricted to EXPERIMENTAL (and unlabeled/OTHER) arms so a trial testing a
    small molecule against a biologic active comparator isn't wrongly
    excluded because of the comparator's modality.
    """
    url = f"{API_BASE}/{nct_id}"
    params = {"fields": "NCTId,ArmsInterventionsModule"}
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"types": [], "names": [], "error": str(e)}

    module = data.get("protocolSection", {}).get("armsInterventionsModule", {})
    interventions = module.get("interventions", [])
    arm_groups = module.get("armGroups", [])

    non_experimental_names = set()
    for arm in arm_groups:
        if (arm.get("type") or "").upper() in NON_EXPERIMENTAL_ARM_TYPES:
            for label in arm.get("interventionNames", []):
                # interventionNames look like "Drug: Aflibercept"
                non_experimental_names.add(label.split(":", 1)[-1].strip())

    exp_interventions = [i for i in interventions if i.get("name", "") not in non_experimental_names]
    if not exp_interventions:
        exp_interventions = interventions  # no arm typing available; fall back to all

    types = [i.get("type", "") for i in exp_interventions]
    names = [i.get("name", "") for i in exp_interventions]
    return {"types": types, "names": names, "error": None}


def classify_modality(types: list, names: list = None) -> str:
    """Return 'small_molecule_candidate', 'needs_name_lookup', 'excluded',
    or 'no_drug_intervention'.

    CT.gov's own type tag is necessary but not sufficient -- it catches
    explicit BIOLOGICAL/GENETIC/DEVICE tags, but sponsors routinely mis-tag
    antibody/protein drugs as plain "DRUG". So a DRUG-typed intervention only
    counts as a small_molecule_candidate if its name doesn't also match a
    biologic INN suffix; if the name is an opaque sponsor code with no
    morphological signal either way, it's flagged for manual lookup rather
    than assumed in-scope.
    """
    type_set = set(t.upper() for t in types if t)
    if not type_set:
        return "no_drug_intervention"
    if type_set & DISQUALIFYING_TYPES:
        return "excluded"
    if "DRUG" not in type_set:
        return "no_drug_intervention"

    drug_names = names or []
    if any(BIOLOGIC_INN_SUFFIXES.search(n) for n in drug_names if n):
        return "excluded"
    if any(SPONSOR_CODE_PATTERN.match(n.strip()) for n in drug_names if n):
        return "needs_name_lookup"
    return "small_molecule_candidate"


def fetch_and_classify(nct_id: str, sleep: float = 0.15) -> dict:
    info = get_intervention_types(nct_id)
    time.sleep(sleep)
    modality = classify_modality(info["types"], info["names"]) if info["error"] is None else "api_error"
    return {
        "nct_id": nct_id,
        "intervention_types": ";".join(info["types"]),
        "intervention_names": ";".join(info["names"]),
        "modality": modality,
        "error": info["error"],
    }
