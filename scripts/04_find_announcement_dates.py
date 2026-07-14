"""Day-1 pipeline step 4: find and VERIFY the announcement-date filing for
every PubChem-verified small-molecule/peptide trial.

v2: the first version re-ran a blind 10-keyword-search (5 terms x 2 forms)
PER TRIAL, but 342 candidates only span 63 unique companies -- Pfizer alone
has 49 trials. This version fetches each company's full 8-K/6-K filing list
ONCE (via the cheap submissions API, not full-text search) and reuses it
across every trial from that sponsor, then verifies candidate filings by
actually fetching and reading their text (no keyword pre-filter at the
search stage at all -- verification does the real work).

A hit is not proof of anything by itself -- a manual sample found most
keyword hits were false positives (drug name in an unrelated context, e.g.
routine earnings). So every candidate filing is fetched and run through
verify_filing_mentions_trial before being accepted.

Runs across BOTH success and failure_efficacy_safety -- we already found one
CTOD "success" label (VIB7734/daxdilimab) contradicted by real reporting, so
the success bucket needs the same verification pass to find hidden
mislabeled negatives, not just to confirm dates.
"""
import sys
sys.path.insert(0, "src")

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import requests
from tqdm import tqdm

from hedgefund.sec import get_all_filings_in_range, list_accession_documents
from hedgefund.edgar_dates import fetch_filing_text, verify_filing_mentions_trial
from hedgefund.news_fallback import load_news_index, candidate_dates_in_window

# Per-trial resolution is I/O-bound (network wait dominates) and each trial
# is independent once filings_by_cik is built, so this is a safe wall-clock
# speedup -- unlike the earlier attempt to cap/skip filings, which silently
# dropped a real answer (AbbVie/NCT03178487). Kept modest to stay well
# within SEC's fair-access rate guidance.
MAX_WORKERS = 5

FORMS = {"8-K", "6-K"}


def _is_earnings_only(acc):
    """Item 2.02 ("Results of Operations") alone, with no 7.01/8.01, is
    OFTEN a routine earnings release -- but not always (AbbVie's genuine
    NCT03178487 disclosure turned out to be bundled inside a 2.02+9.01
    earnings release). So this is used only to order which filing gets
    checked first for a faster average-case exit, never to skip/cap
    checking a filing outright -- that cost a real true positive once
    already when tried.
    """
    items = set((acc.get("items") or "").split(","))
    return items == {"2.02"} or items == {"2.02", "9.01"}


def verify_candidate_accessions(cik, accessions, names, title):
    """Try every candidate accession's real documents, ordered non-earnings-
    only first for a faster average-case exit. Returns the first verified
    hit, or None -- always checks the full list, never truncates."""
    ranked = sorted(accessions, key=lambda a: (_is_earnings_only(a), a["filingDate"]))
    for acc in ranked:
        try:
            doc_urls = list_accession_documents(cik, acc["accession"])
        except requests.RequestException:
            continue
        for url in doc_urls[:2]:  # exhibits are sorted first; cap fetches per filing
            try:
                text = fetch_filing_text(url)
            except requests.RequestException:
                continue
            v = verify_filing_mentions_trial(text, names, title)
            if v["verified"]:
                return {"url": url, "file_date": acc["filingDate"], "form": acc["form"], **v}
    return None


def main():
    df = pd.read_csv("data/interim/04_pubchem_verified.csv", low_memory=False)
    df = df[df["pubchem_verified_small_molecule_or_peptide"] == True].copy()
    df = df[df["outcome_category"].isin(["success", "failure_efficacy_safety"])]
    print(f"PubChem-verified success/failure candidates: {len(df)}")
    print(f"Unique sponsors (CIKs): {df['cik'].nunique()}")

    news_index = load_news_index("data/raw/ctod/news_lfs.csv")

    # one filing-list fetch per company, covering the union of all its
    # trials' windows, reused across every trial from that sponsor
    filings_by_cik = {}
    for cik_raw, group in df.groupby("cik"):
        cik = str(int(cik_raw)).zfill(10)
        starts = pd.to_datetime(group["completion_date"])
        date_from = starts.min().strftime("%Y-%m-%d")
        date_to = (starts.max() + pd.Timedelta(days=400)).strftime("%Y-%m-%d")
        try:
            filings_by_cik[cik] = get_all_filings_in_range(cik, FORMS, date_from, date_to)
        except requests.RequestException as e:
            filings_by_cik[cik] = []
            print(f"WARN: filing list fetch failed for CIK {cik}: {e}")

    def resolve_trial(row):
        cik = str(int(row["cik"])).zfill(10)
        names = [n.strip() for n in str(row["intervention_names"]).split(";") if n.strip()]
        title = row["official_title"] if pd.notna(row.get("official_title")) else row["brief_title"]

        start = row["completion_date"]
        end = (pd.Timestamp(start) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        candidates = sorted(
            [f for f in filings_by_cik.get(cik, []) if start <= f["filingDate"] <= end],
            key=lambda f: f["filingDate"],
        )

        verified = verify_candidate_accessions(cik, candidates, names, title)
        method = "edgar_primary" if verified else None
        n = len(candidates)

        if not verified:
            news_hits = candidate_dates_in_window(row["nct_id"], news_index, row["completion_date"])
            for nh in news_hits:
                lo = (nh["date"] - timedelta(days=5)).strftime("%Y-%m-%d")
                hi = (nh["date"] + timedelta(days=5)).strftime("%Y-%m-%d")
                rescue_candidates = [f for f in filings_by_cik.get(cik, []) if lo <= f["filingDate"] <= hi]
                verified = verify_candidate_accessions(cik, rescue_candidates, names, title)
                n += len(rescue_candidates)
                if verified:
                    method = "news_rescue"
                    break

        if not verified:
            method = "unresolved_needs_manual_check"

        return row["nct_id"], method, verified, n

    methods, verified_hits, n_seen = {}, {}, {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(resolve_trial, row) for _, row in df.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Verify per trial"):
            nct_id, method, verified, n = fut.result()
            methods[nct_id] = method
            verified_hits[nct_id] = verified
            n_seen[nct_id] = n

    df["resolution_method"] = df["nct_id"].map(methods)
    df["n_filings_checked"] = df["nct_id"].map(n_seen)
    df["verified_filing_url"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("url"))
    df["verified_filing_date"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("file_date"))
    df["verified_context"] = df["nct_id"].map(lambda n: (verified_hits.get(n) or {}).get("context"))

    df.to_csv("data/interim/05_filing_search_results.csv", index=False)
    json.dump(verified_hits, open("data/interim/05_verified_hits.json", "w"), indent=2)

    print(df["resolution_method"].value_counts(dropna=False))
    print()
    print("By outcome_category and resolution_method:")
    print(df.groupby(["outcome_category", "resolution_method"]).size())

if __name__ == "__main__":
    main()
