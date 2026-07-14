"""Scan the 117 'success'-labeled trials that never resolved to a verified
filing, checking their raw candidate filings (pre-verification) for negative
outcome language near the drug name. This is a looser net than
verify_filing_mentions_trial -- it doesn't require full trial-identity
confirmation, just drug-name + negative-phrase co-occurrence, because these
trials failed the stricter check and might otherwise never get looked at.
Every hit here still needs a manual title/drug cross-check before counting
it (see session history: several "hits" turned out to be about a different
trial from the same sponsor's pipeline-update paragraph).
"""
import sys
sys.path.insert(0, "src")

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from tqdm import tqdm

from hedgefund.sec import get_all_filings_in_range, list_accession_documents
from hedgefund.edgar_dates import fetch_filing_text

FORMS = {"8-K", "6-K"}

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


def scan_candidate(cik, name, acc_url):
    try:
        text = fetch_filing_text(acc_url)
    except requests.RequestException:
        return None
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    lower = clean.lower()
    name_pos = lower.find(name.lower())
    if name_pos == -1:
        return None
    window = clean[max(0, name_pos - 500):name_pos + 500]
    m = NEGATIVE_PHRASES.search(window)
    if not m:
        return None
    return window


def process_trial(row, filings_by_cik):
    cik = str(int(row["cik"])).zfill(10)
    names = [n.strip() for n in str(row["intervention_names"]).split(";") if n.strip()]
    start, end = row["completion_date"], (pd.Timestamp(row["completion_date"]) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    candidates = [f for f in filings_by_cik.get(cik, []) if start <= f["filingDate"] <= end]

    for acc in candidates:
        try:
            doc_urls = list_accession_documents(cik, acc["accession"])
        except requests.RequestException:
            continue
        for url in doc_urls[:2]:
            for name in names:
                hit = scan_candidate(cik, name, url)
                if hit:
                    return row["nct_id"], acc["filingDate"], url, hit
    return row["nct_id"], None, None, None


def main():
    df = pd.read_csv("data/interim/05_filing_search_results.csv", low_memory=False)
    targets = df[(df["outcome_category"] == "success") &
                 (df["resolution_method"] == "unresolved_needs_manual_check")].copy()
    print(f"Scanning {len(targets)} unresolved 'success' trials")

    filings_by_cik = {}
    for cik_raw, group in targets.groupby("cik"):
        cik = str(int(cik_raw)).zfill(10)
        starts = pd.to_datetime(group["completion_date"])
        date_from = starts.min().strftime("%Y-%m-%d")
        date_to = (starts.max() + pd.Timedelta(days=400)).strftime("%Y-%m-%d")
        try:
            filings_by_cik[cik] = get_all_filings_in_range(cik, FORMS, date_from, date_to)
        except requests.RequestException as e:
            filings_by_cik[cik] = []
            print(f"WARN CIK {cik}: {e}")

    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(process_trial, row, filings_by_cik) for _, row in targets.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures)):
            nct_id, file_date, url, hit = fut.result()
            if hit:
                results[nct_id] = {"file_date": file_date, "url": url, "context": hit}

    print(f"\nFlagged: {len(results)}")
    out_rows = []
    for nct_id, info in results.items():
        row = targets[targets["nct_id"] == nct_id].iloc[0]
        out_rows.append({
            "nct_id": nct_id, "ticker": row["ticker"], "brief_title": row["brief_title"],
            "file_date": info["file_date"], "url": info["url"], "context": info["context"],
        })
    out_df = pd.DataFrame(out_rows)
    out_df.to_csv("data/interim/07_flagged_from_unresolved.csv", index=False)
    for _, row in out_df.iterrows():
        print("="*80)
        print(row["nct_id"], row["ticker"], row["file_date"], "|", str(row["brief_title"])[:90])
        print(" ", row["context"][:500])

if __name__ == "__main__":
    main()
