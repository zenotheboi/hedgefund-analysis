"""EDGAR rematch rebuild, stage 2 (v2): fixes two problems found by spot-
checking stage 2 v1's output (scripts/21_*):

1. v1 only widened the search window when a trial's narrow window returned
   ZERO hits. A trial with 1-2 hits in the narrow window was called "clean"
   and never checked further -- but those 1-2 hits are often just whichever
   routine quarterly filings happened to fall in that slice, not evidence
   the real disclosure isn't sitting outside the window (before completion,
   e.g. an early-stop announcement, or later). This version always searches
   one single wide window: [primary_completion_date - 180d, +450d].

2. v1 merged hits from multiple query terms (acronym, drug names) into one
   list per trial with no record of which term matched which hit. Verifying
   a hit meant guessing which term it came from. This version tags every
   hit with its source term.

Then, instead of classifying by hit COUNT (proven not to predict quality --
spot checks found ~90% of "clean" i.e. low-hit-count trials were generic
pipeline/earnings mentions, not real disclosures), this version fetches
the actual text for every unique candidate document and scores each
(trial, term, hit) triple by whether real result-disclosure language
("met its primary endpoint", "did not meet", "topline results",
"discontinued", "positive results", "negative results", "failed to meet")
appears within 400 characters of where the term itself appears in the
document. A genuine dedicated press release has these tightly clustered; a
pipeline chart or earnings summary usually doesn't. This is a ranking
signal to prioritize manual reading, not a replacement for it -- spot-check
the top-ranked candidates before trusting them, same as everything else in
this audit.
"""
import sys
sys.path.insert(0, "src")

import re
import time
import json
import requests
import pandas as pd

HEADERS = {"User-Agent": "research test test@example.com"}

RESULT_PHRASES = [
    "met its primary endpoint", "met the primary endpoint", "did not meet",
    "failed to meet", "topline results", "top-line results", "top line results",
    "discontinued", "discontinuation", "positive results", "negative results",
    "statistically significant", "did not achieve", "did not demonstrate",
    "announces positive", "announces topline", "reports topline",
]


def query_terms(acronym, intervention_names):
    terms = []
    if isinstance(acronym, str) and acronym.strip():
        terms.append(acronym.strip())
    if isinstance(intervention_names, str):
        for p in re.split(r"[;,]", intervention_names):
            p = re.sub(r"\(.*?\)", "", p).strip()
            if not p or p.lower() == "placebo" or p.lower().startswith("placebo for"):
                continue
            if len(p) >= 3:
                terms.append(p)
    seen, out = set(), []
    for t in terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out[:4]


def search(query, cik, startdt, enddt):
    params = {
        "q": f'"{query}"', "forms": "8-K,6-K", "ciks": f"{int(cik):010d}",
        "dateRange": "custom", "startdt": startdt, "enddt": enddt,
    }
    try:
        r = requests.get("https://efts.sec.gov/LATEST/search-index", params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        d = r.json()
        return [
            {"date": h["_source"]["file_date"], "form": h["_source"]["form"],
             "items": h["_source"].get("items"), "id": h["_id"]}
            for h in d["hits"]["hits"]
        ]
    except Exception:
        return []


def shift_date(date_str, days):
    return (pd.Timestamp(date_str) + pd.Timedelta(days=days)).strftime("%Y-%m-%d")


def fetch_text(cik, accession, filename):
    adsh_clean = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh_clean}/{filename}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        text = re.sub("<[^>]+>", " ", r.text)
        text = re.sub(r"&#?\w+;", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text
    except Exception:
        return None


def score_term_in_text(term, text):
    """Returns (found, best_score, snippet) for the first/best occurrence of
    term in text, scored by count of result-phrases within 400 chars."""
    idx = text.lower().find(term.lower())
    if idx == -1:
        return False, 0, None
    window = text[max(0, idx - 400):idx + 400].lower()
    score = sum(1 for p in RESULT_PHRASES if p in window)
    snippet = text[max(0, idx - 200):idx + 300]
    return True, score, snippet


def main():
    combined = pd.read_csv("data/processed/combined_phase_outcome_analysis.csv")
    identity = pd.read_csv("data/interim/17_audit_master.csv")[["nct_id", "intervention_names"]]
    ctgov = pd.read_csv("data/interim/20_ctgov_acronym_dates_all260.csv")
    df = combined.merge(identity, on="nct_id", how="left").merge(ctgov, on="nct_id", how="left")

    with open("data/raw/sec/company_tickers.json") as f:
        tick_map = {v["ticker"]: v["cik_str"] for v in json.load(f).values()}

    # --- phase A: search, single wide window, term-tagged hits ---
    print("Phase A: searching...")
    all_candidates = []  # rows of (nct_id, term, cik, hit)
    n = len(df)
    for i, row in df.iterrows():
        nct, ticker = row["nct_id"], row["ticker"]
        cik = tick_map.get(ticker)
        pcd = row["primary_completion"]
        if cik is None or pd.isna(pcd):
            continue
        terms = query_terms(row.get("acronym"), row.get("intervention_names"))
        start, end = shift_date(pcd, -180), shift_date(pcd, 450)
        for t in terms:
            for h in search(t, cik, start, end):
                all_candidates.append({"nct_id": nct, "ticker": ticker, "term": t, "cik": cik, **h})
            time.sleep(0.15)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{n}")

    cand_df = pd.DataFrame(all_candidates)
    cand_df = cand_df.drop_duplicates(subset=["nct_id", "term", "id"])
    print(f"Phase A done: {len(cand_df)} (trial, term, hit) candidates, "
          f"{cand_df['id'].nunique()} unique documents")
    cand_df.to_csv("data/interim/22_edgar_candidates_raw.csv", index=False)

    # --- phase B: fetch unique documents once, score every candidate against them ---
    print("\nPhase B: fetching + scoring...")
    unique_docs = cand_df[["cik", "id"]].drop_duplicates()
    text_cache = {}
    for j, (_, r) in enumerate(unique_docs.iterrows()):
        accession, filename = r["id"].split(":")
        text = fetch_text(r["cik"], accession, filename)
        text_cache[r["id"]] = text
        time.sleep(0.15)
        if (j + 1) % 50 == 0:
            print(f"  fetched {j+1}/{len(unique_docs)}")

    scored = []
    for _, row in cand_df.iterrows():
        text = text_cache.get(row["id"])
        if text is None:
            scored.append({**row, "found_in_text": False, "score": -1, "snippet": None})
            continue
        found, score, snippet = score_term_in_text(row["term"], text)
        scored.append({**row, "found_in_text": found, "score": score, "snippet": snippet})

    scored_df = pd.DataFrame(scored)
    scored_df.to_csv("data/interim/22_edgar_candidates_scored.csv", index=False)

    # best candidate per trial
    valid = scored_df[scored_df["found_in_text"] == True]
    best = valid.sort_values("score", ascending=False).drop_duplicates(subset="nct_id", keep="first")
    print(f"\n{len(best)} of {n} trials have at least one term-confirmed-in-text candidate")
    print("Score distribution of best candidate per trial:")
    print(best["score"].value_counts().sort_index(ascending=False).to_string())
    best.to_csv("data/interim/22_edgar_best_candidate_per_trial.csv", index=False)


if __name__ == "__main__":
    main()
