"""PubChem cross-reference for small-molecule/peptide verification.

Per the methodology's mandatory filter: when CT.gov's intervention type is
unreliable (mis-tagged biologics, or opaque sponsor codes with no
morphological signal), look the compound up in PubChem directly rather than
guess from the name.
"""
import time
import requests

PUG_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Small molecules are typically <900 Da; small peptides (e.g. semaglutide,
# ~4114 Da) run larger but are still explicitly in scope per the doc. Full
# proteins/antibodies are one to two orders of magnitude larger still, and
# in practice usually aren't indexed as PubChem "compounds" at all.
MAX_SMALL_MOLECULE_OR_PEPTIDE_MW = 8000


def lookup_compound(name: str, timeout: int = 15, sleep: float = 0.25) -> dict:
    """Return {'found': bool, 'cid': int|None, 'mw': float|None, 'is_small_molecule_or_peptide': bool}."""
    url = f"{PUG_BASE}/compound/name/{requests.utils.quote(name)}/property/MolecularWeight/JSON"
    try:
        resp = requests.get(url, timeout=timeout)
        time.sleep(sleep)
        if resp.status_code == 404:
            return {"found": False, "cid": None, "mw": None, "is_small_molecule_or_peptide": False}
        resp.raise_for_status()
        data = resp.json()
        props = data["PropertyTable"]["Properties"][0]
        mw = float(props["MolecularWeight"])
        return {
            "found": True,
            "cid": props["CID"],
            "mw": mw,
            "is_small_molecule_or_peptide": mw <= MAX_SMALL_MOLECULE_OR_PEPTIDE_MW,
        }
    except requests.RequestException as e:
        return {"found": False, "cid": None, "mw": None, "is_small_molecule_or_peptide": False, "error": str(e)}
