"""Find candidate 8-K/6-K filings near a trial's completion date and fetch
their exhibit text for manual/LLM verification (see outcome_category.py's
docstring for why this shouldn't be pure keyword classification).

A hit from find_candidate_filings is NOT proof the filing is actually about
the target trial. Manual review of a 10-trial sample found that for
multi-program sponsors, a keyword match is very often the drug name showing
up in a routine "net product sales" paragraph, or a mention of a *different*
trial of the same drug -- 9 of 10 sample hits were false positives this way.
verify_filing_mentions_trial() is a cheap proximity check to catch this
before a hit is trusted; it is NOT a substitute for actually reading the
final selected candidates by hand.
"""
import re
import time
from datetime import datetime, timedelta

import requests

from hedgefund.sec import HEADERS, fulltext_search

CLINICAL_QUERY_TERMS = [
    "topline results",
    "primary endpoint",
    "met the primary",
    "did not meet",
    "top-line results",
]

STOPWORDS = {
    "a", "an", "the", "of", "in", "with", "to", "for", "and", "or", "study",
    "trial", "phase", "safety", "efficacy", "evaluate", "evaluating",
    "assess", "assessing", "randomized", "double-blind", "open-label",
    "placebo-controlled", "multicenter", "participants", "patients",
    "subjects", "adult", "adults", "vs", "versus", "compared", "dose",
    "ranging", "extension", "long-term", "tolerability", "pharmacokinetics",
    "pharmacodynamics", "prevention", "treatment", "treating", "reduce",
    "reducing", "compare", "comparing", "moderate", "severe", "moderately",
    "severely", "active", "combination", "monotherapy", "multiple",
    "single", "escalation",
    # generic trial-design boilerplate that appears in nearly every title
    "arm", "arms", "prospective", "crossover", "parallel-group",
    "non-randomized", "nonrandomized", "observational", "interventional",
    "blind", "blinded", "controlled", "group", "groups", "receiving",
    "relapsed", "refractory", "first-in-human", "pilot", "exploratory",
    "follow-up", "followup", "period", "arm-", "label", "controlled-trial",
}
MIN_MATCHED_KEYWORDS = 2
# Generic words are frequently short; require at least one matched keyword
# to be long enough to plausibly be a genuinely distinctive term (drug name,
# specific indication) rather than boilerplate that slipped past STOPWORDS.
MIN_DISTINCTIVE_KEYWORD_LENGTH = 7
FINANCIAL_BOILERPLATE = re.compile(r"net (?:product )?sales|revenue|earnings per share|gross margin", re.IGNORECASE)


def _title_keywords(title: str) -> set:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", title or "")
    return {w.lower() for w in words if w.lower() not in STOPWORDS and len(w) > 2}


def verify_filing_mentions_trial(filing_text: str, drug_names: list, title: str,
                                  window_chars: int = 400) -> dict:
    """Check whether a filing plausibly discusses THIS trial specifically,
    not just the drug name in an unrelated (often financial) context.

    Looks for a drug-name mention where the surrounding window also contains
    a distinctive word from the trial's title (e.g. the indication) and is
    NOT dominated by financial-report boilerplate.
    """
    clean = re.sub(r"<[^>]+>", " ", filing_text)
    clean = re.sub(r"\s+", " ", clean)
    lower = clean.lower()
    keywords = _title_keywords(title)

    for name in drug_names:
        name = (name or "").strip()
        if not name:
            continue
        for m in re.finditer(re.escape(name.lower()), lower):
            start, end = max(0, m.start() - window_chars), m.end() + window_chars
            window = clean[start:end]
            window_lower = window.lower()
            if FINANCIAL_BOILERPLATE.search(window_lower):
                continue
            matched_keywords = [k for k in keywords if k in window_lower]
            has_distinctive = any(len(k) >= MIN_DISTINCTIVE_KEYWORD_LENGTH for k in matched_keywords)
            if len(matched_keywords) >= MIN_MATCHED_KEYWORDS and has_distinctive:
                return {"verified": True, "matched_drug": name, "matched_keywords": matched_keywords, "context": window}
    return {"verified": False, "matched_drug": None, "matched_keywords": [], "context": None}


def find_candidate_filings(cik: str, completion_date: str, months_after: int = 12) -> list:
    """Search 8-K and 6-K filings by this CIK in [completion_date, +months_after].

    Returns deduped list of {accession, filename, form, file_date, items, url}.
    """
    start = datetime.strptime(completion_date, "%Y-%m-%d")
    end = start + timedelta(days=30 * months_after)
    date_from, date_to = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    seen = {}
    for form in ("8-K", "6-K"):
        for term in CLINICAL_QUERY_TERMS:
            try:
                hits = fulltext_search(cik, form, date_from, date_to, query=f'"{term}"')
            except requests.HTTPError:
                # e.g. searching 6-K for a domestic filer that's never filed one
                continue
            for h in hits:
                acc, fname = h["_id"].split(":")
                src = h["_source"]
                cik_nodash = str(int(cik))
                acc_nodash = acc.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{cik_nodash}/{acc_nodash}/{fname}"
                seen[h["_id"]] = {
                    "accession": acc,
                    "filename": fname,
                    "form": src["form"],
                    "file_date": src["file_date"],
                    "items": src.get("items", []),
                    "matched_term": term,
                    "url": url,
                }
    return sorted(seen.values(), key=lambda x: x["file_date"])


def find_filings_near_date(cik: str, target_date, window_days: int = 5) -> list:
    """Search 8-K/6-K filings by CIK within +-window_days of a target date,
    with NO keyword requirement. Used only as a rescue when a CTOD news
    headline gives independent evidence that *something* was disclosed
    around this date but the primary keyword search found nothing -- the
    keyword phrasing may just differ from CLINICAL_QUERY_TERMS.
    """
    start = (target_date - timedelta(days=window_days)).strftime("%Y-%m-%d")
    end = (target_date + timedelta(days=window_days)).strftime("%Y-%m-%d")

    seen = {}
    for form in ("8-K", "6-K"):
        try:
            hits = fulltext_search(cik, form, start, end, query="")
        except requests.HTTPError:
            continue
        for h in hits:
            acc, fname = h["_id"].split(":")
            src = h["_source"]
            cik_nodash = str(int(cik))
            acc_nodash = acc.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik_nodash}/{acc_nodash}/{fname}"
            seen[h["_id"]] = {
                "accession": acc,
                "filename": fname,
                "form": src["form"],
                "file_date": src["file_date"],
                "items": src.get("items", []),
                "matched_term": "news_fallback_no_keyword",
                "url": url,
            }
    return sorted(seen.values(), key=lambda x: x["file_date"])


def fetch_filing_text(url: str, timeout: int = 15, sleep: float = 0.2) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    time.sleep(sleep)
    resp.raise_for_status()
    return resp.text
