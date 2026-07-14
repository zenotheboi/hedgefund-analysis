"""Scan CTOD-labeled 'success' trials whose filing we already verified, for
negative-outcome language the label may have missed. We've already found two
confirmed cases by manual sampling (VIB7734/daxdilimab, BMY olutasidenib)
where CTOD calls it success but the actual filing says the trial failed.
This is a triage pass -- it flags candidates for manual reading, it does not
decide the outcome itself (a flagged hit still needs a human read, and a
non-hit doesn't guarantee the label is right, just that this phrase list
didn't catch anything).
"""
import sys
sys.path.insert(0, "src")

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from tqdm import tqdm

from hedgefund.edgar_dates import fetch_filing_text

NEGATIVE_PHRASES = re.compile(
    r"did not meet|failed to meet|did not achieve|missed the primary|"
    r"did not demonstrate|was not met|did not show|no significant "
    r"difference|not statistically significant|did not reach statistical|"
    r"discontinu(e|ing|ed) (the )?(development|program|study|trial)|"
    r"unsuccessful|did not separate from placebo|failed to separate|"
    r"below the (pre-specified|prespecified) threshold|"
    r"will not (pursue|advance|continue)|does not support further "
    r"development|halted development|comparable to placebo|"
    r"similar to placebo|did not differentiate from placebo|"
    r"non-significant trend|underwhelming|ineffective|no meaningful "
    r"difference|did not translate into|fell short",
    re.IGNORECASE,
)


def scan_one(row):
    try:
        text = fetch_filing_text(row["verified_filing_url"])
    except requests.RequestException:
        return row["nct_id"], None
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    matches = NEGATIVE_PHRASES.findall(clean)
    if not matches:
        return row["nct_id"], None
    # grab context around the first match for manual review
    m = NEGATIVE_PHRASES.search(clean)
    context = clean[max(0, m.start() - 300):m.end() + 300]
    return row["nct_id"], context


def main():
    df = pd.read_csv("data/interim/05_filing_search_results.csv", low_memory=False)
    success = df[(df["outcome_category"] == "success") &
                 (df["resolution_method"] == "edgar_primary")].copy()
    print(f"Scanning {len(success)} resolved 'success' filings for negative-outcome language")

    flagged = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(scan_one, row) for _, row in success.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures)):
            nct_id, context = fut.result()
            if context:
                flagged[nct_id] = context

    print(f"\nFlagged for manual review: {len(flagged)}")
    out = success[success["nct_id"].isin(flagged.keys())][
        ["nct_id", "source", "ticker", "verified_filing_date", "verified_filing_url", "brief_title"]
    ].copy()
    out["negative_phrase_context"] = out["nct_id"].map(flagged)
    out.to_csv("data/interim/06_flagged_hidden_negatives.csv", index=False)
    for _, row in out.iterrows():
        print(row["nct_id"], row["ticker"], row["verified_filing_date"])
        print("  ", row["negative_phrase_context"][:250])

if __name__ == "__main__":
    main()
