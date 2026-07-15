"""SEC ticker matching and EDGAR filing lookups."""
import json
import re
import time

import pandas as pd
import requests
from rapidfuzz import fuzz, process

USER_AGENT = "hedgefund-analysis research gigi08180213@gmail.com"
HEADERS = {"User-Agent": USER_AGENT}

SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|plc|"
    r"l\.?p\.?|s\.?a\.?|n\.?v\.?|ag|gmbh|holdings?|group)\b",
    re.IGNORECASE,
)

# SIC codes covering pharma/biotech industries, used to sanity-check fuzzy
# ticker matches against companies that happen to share a name fragment
# (e.g. "Vertex Pharmaceuticals" vs "Vertex, Inc.", a tax-software company).
PHARMA_SIC_CODES = {
    "2833",  # Medicinal Chemicals & Botanical Products
    "2834",  # Pharmaceutical Preparations
    "2835",  # In Vitro & In Vivo Diagnostic Substances
    "2836",  # Biological Products (No Diagnostic Substances)
    "8731",  # Services-Commercial Physical & Biological Research
}
PUNCT_PATTERN = re.compile(r"[.,'&/\-]")


def normalize_name(name: str) -> str:
    name = name.lower()
    name = PUNCT_PATTERN.sub("", name)
    name = SUFFIX_PATTERN.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def load_company_tickers(path: str) -> pd.DataFrame:
    with open(path) as f:
        raw = json.load(f)
    df = pd.DataFrame.from_dict(raw, orient="index")
    df["cik"] = df["cik_str"].astype(str).str.zfill(10)
    df["norm_title"] = df["title"].apply(normalize_name)
    return df


def match_sponsor_to_ticker(sponsor: str, tickers_df: pd.DataFrame, score_cutoff: int = 82):
    """Best-effort fuzzy match of a sponsor name to a SEC ticker/CIK.

    Returns dict with ticker/cik/title/score, or all-None if no match clears
    score_cutoff. This is a candidate match, not verification -- always
    sanity-check the returned title against the sponsor name before trusting it.
    """
    norm_sponsor = normalize_name(sponsor)
    if not norm_sponsor:
        return {"ticker": None, "cik": None, "title": None, "score": 0}

    result = process.extractOne(
        norm_sponsor, tickers_df["norm_title"], scorer=fuzz.token_sort_ratio,
        score_cutoff=score_cutoff,
    )
    if result is None:
        return {"ticker": None, "cik": None, "title": None, "score": 0}

    _, score, idx = result
    row = tickers_df.loc[idx]

    # token_sort_ratio scores short/generic names as similar even when they
    # aren't the same company (e.g. "celgene" vs "clene" scores 83, "alexion
    # pharmaceuticals" vs "lexicon pharmaceuticals" scores 95.6 -- high enough
    # to have previously bypassed this check via a >=95 escape hatch, which
    # is why that escape hatch was removed: both legitimate high-score cases
    # that motivated it (Novo Nordisk A/S, Bristol-Myers Squibb) already
    # satisfy containment on their own, so the bypass was pure liability.
    # Always require one normalized name to actually contain the other.
    norm_title = row["norm_title"]
    contains = norm_sponsor.replace(" ", "") in norm_title.replace(" ", "") or \
        norm_title.replace(" ", "") in norm_sponsor.replace(" ", "")
    if not contains:
        return {"ticker": None, "cik": None, "title": None, "score": 0}

    return {"ticker": row["ticker"], "cik": row["cik"], "title": row["title"], "score": score}


def get_submissions(cik: str, timeout: int = 15) -> dict:
    """CIK must be zero-padded to 10 digits."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def verify_pharma_sic(cik: str, sleep: float = 0.15) -> dict:
    """Confirm a matched CIK is actually a pharma/biotech filer via its SIC code.

    Guards against fuzzy-match false positives across unrelated industries
    that happen to share a name fragment (e.g. Vertex Pharma vs Vertex Inc).
    """
    try:
        data = get_submissions(cik)
    except requests.RequestException as e:
        return {"sic": None, "sic_description": None, "is_pharma": False, "error": str(e)}
    finally:
        time.sleep(sleep)
    sic = data.get("sic")
    return {
        "sic": sic,
        "sic_description": data.get("sicDescription"),
        "is_pharma": sic in PHARMA_SIC_CODES,
        "error": None,
    }


def get_all_filings_in_range(cik: str, forms: set, date_from: str, date_to: str,
                              sleep: float = 0.15) -> list:
    """All filings of the given form types for a CIK within [date_from, date_to],
    fetched ONCE per company rather than re-searched per trial. The
    submissions API's "recent" list only covers roughly the last ~1000
    filings (e.g. only back to 2021-01 for a high-volume filer like Pfizer),
    so this also pages through the older per-company submission files listed
    under filings.files when the requested range predates "recent".
    """
    data = get_submissions(cik)
    time.sleep(sleep)
    all_entries = []

    def _extract(block):
        n = len(block.get("form", []))
        items_block = block.get("items", [""] * n)
        for i in range(n):
            if block["form"][i] in forms:
                all_entries.append({
                    "accession": block["accessionNumber"][i],
                    "filingDate": block["filingDate"][i],
                    "form": block["form"][i],
                    "primaryDocument": block["primaryDocument"][i],
                    "items": items_block[i] if i < len(items_block) else "",
                })

    _extract(data["filings"]["recent"])
    earliest_recent = min(data["filings"]["recent"]["filingDate"], default=date_to)

    if earliest_recent > date_from:
        for f in data["filings"].get("files", []):
            if f["filingTo"] < date_from or f["filingFrom"] > date_to:
                continue
            url = f"https://data.sec.gov/submissions/{f['name']}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            time.sleep(sleep)
            resp.raise_for_status()
            _extract(resp.json())

    return [e for e in all_entries if date_from <= e["filingDate"] <= date_to]


def list_accession_documents(cik: str, accession: str, sleep: float = 0.1) -> list:
    """Real content documents (htm/html, excluding XBRL scaffolding) for one
    filing accession, via its lightweight index.json -- much cheaper than a
    full-text-search hit and doesn't miss exhibits that aren't primaryDocument.
    """
    cik_nodash = str(int(cik))
    acc_nodash = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_nodash}/{acc_nodash}/index.json"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    time.sleep(sleep)
    resp.raise_for_status()
    items = resp.json().get("directory", {}).get("item", [])
    docs = [i["name"] for i in items if i["name"].lower().endswith((".htm", ".html"))
            and "index" not in i["name"].lower()]
    # exhibits (press releases) are the likely content; prioritize them
    docs.sort(key=lambda n: 0 if "ex99" in n.lower() or "ex-99" in n.lower() else 1)
    return [f"https://www.sec.gov/Archives/edgar/data/{cik_nodash}/{acc_nodash}/{d}" for d in docs]


def fulltext_search(cik: str, forms: str, date_from: str, date_to: str,
                     query: str = "", timeout: int = 15, sleep: float = 0.2) -> list:
    """Query SEC EDGAR full-text search (covers filings from 2001+).

    forms: comma-separated form types, e.g. '8-K,6-K'
    date_from/date_to: 'YYYY-MM-DD'
    """
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": query,
        "forms": forms,
        "dateRange": "custom",
        "startdt": date_from,
        "enddt": date_to,
        "ciks": cik,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    time.sleep(sleep)
    resp.raise_for_status()
    data = resp.json()
    return data.get("hits", {}).get("hits", [])
