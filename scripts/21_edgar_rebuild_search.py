"""EDGAR rematch rebuild, stage 2: discovery search with a widen-if-empty
triage. For each trial, try its CT.gov acronym first (most specific), then
each of its intervention_names tokens, querying SEC's full-text search
(efts.sec.gov) restricted to the trial's own ticker CIK.

Window logic: try [primary_completion_date, +270d] first (covers the
'sponsors disclose close to completion' pattern from the recovery-pass
discussion). If that returns zero hits across every query term, widen to
[primary_completion_date - 90d, +450d] and try again -- catches early
interim-analysis disclosures (before completion, e.g. FLOW's stop-early
announcement) and slow/quarterly-buried disclosures (after +270d).

Does NOT read filing text or judge correctness -- that's stage 3, and only
needed for trials that don't get a clean (<=2 hit) result here. This stage
only classifies each trial as clean / unclear / none, so stage 3's expensive
manual reading only has to cover the two harder buckets, not all 260.
"""
import sys
sys.path.insert(0, "src")

import re
import time
import json
import requests
import pandas as pd

HEADERS = {"User-Agent": "research test test@example.com"}


def query_terms(acronym, intervention_names):
    terms = []
    if isinstance(acronym, str) and acronym.strip():
        terms.append(acronym.strip())
    if isinstance(intervention_names, str):
        for p in re.split(r"[;,]", intervention_names):
            p = re.sub(r"\(.*?\)", "", p).strip()
            if not p or p.lower() in {"placebo"} or p.lower().startswith("placebo for"):
                continue
            if len(p) >= 3:
                terms.append(p)
    # dedupe, keep order
    seen = set()
    out = []
    for t in terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out[:4]  # cap to avoid runaway request counts on messy data


def search(query, cik, startdt, enddt):
    params = {
        "q": f'"{query}"',
        # 8-K for US domestic filers, 6-K for foreign private issuers (Novo
        # Nordisk, Novartis, AstraZeneca, Sanofi, Dr Reddy's etc all file 6-K
        # for material announcements, never 8-K -- an 8-K-only search
        # silently misses every one of their disclosures)
        "forms": "8-K,6-K",
        "ciks": f"{int(cik):010d}",
        "dateRange": "custom",
        "startdt": startdt,
        "enddt": enddt,
    }
    try:
        r = requests.get("https://efts.sec.gov/LATEST/search-index", params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        d = r.json()
        hits = [
            {"date": h["_source"]["file_date"], "items": h["_source"].get("items"),
             "form": h["_source"]["form"], "id": h["_id"], "cik": h["_source"]["ciks"][0]}
            for h in d["hits"]["hits"]
        ]
        return hits
    except Exception:
        return []


def shift_date(date_str, days):
    return (pd.Timestamp(date_str) + pd.Timedelta(days=days)).strftime("%Y-%m-%d")


def main():
    combined = pd.read_csv("data/processed/combined_phase_outcome_analysis.csv")
    identity = pd.read_csv("data/interim/17_audit_master.csv")[["nct_id", "intervention_names"]]
    ctgov = pd.read_csv("data/interim/20_ctgov_acronym_dates_all260.csv")

    df = combined.merge(identity, on="nct_id", how="left").merge(ctgov, on="nct_id", how="left")

    with open("data/raw/sec/company_tickers.json") as f:
        tick_map = {v["ticker"]: v["cik_str"] for v in json.load(f).values()}

    results = []
    n = len(df)
    for i, row in df.iterrows():
        nct = row["nct_id"]
        ticker = row["ticker"]
        cik = tick_map.get(ticker)
        pcd = row["primary_completion"]
        if cik is None or pd.isna(pcd):
            results.append({"nct_id": nct, "status": "no_cik_or_date", "n_hits": 0, "terms_tried": [], "hits": []})
            continue

        terms = query_terms(row.get("acronym"), row.get("intervention_names"))
        if not terms:
            results.append({"nct_id": nct, "status": "no_query_terms", "n_hits": 0, "terms_tried": [], "hits": []})
            continue

        all_hits = []
        start1, end1 = pcd, shift_date(pcd, 270)
        for t in terms:
            all_hits.extend(search(t, cik, start1, end1))
            time.sleep(0.15)

        window_used = "default"
        if not all_hits:
            start2, end2 = shift_date(pcd, -90), shift_date(pcd, 450)
            for t in terms:
                all_hits.extend(search(t, cik, start2, end2))
                time.sleep(0.15)
            window_used = "expanded"

        # dedupe hits by id
        seen_ids = set()
        dedup = []
        for h in all_hits:
            if h["id"] not in seen_ids:
                seen_ids.add(h["id"])
                dedup.append(h)

        if len(dedup) == 0:
            status = "none"
        elif len(dedup) <= 2:
            status = "clean"
        else:
            status = "unclear"

        results.append({
            "nct_id": nct, "status": status, "n_hits": len(dedup),
            "window_used": window_used, "terms_tried": terms, "hits": dedup,
        })

        if (i + 1) % 20 == 0:
            print(f"{i+1}/{n}")

    out = pd.DataFrame(results)
    out["hits_json"] = out["hits"].apply(json.dumps)
    out["terms_json"] = out["terms_tried"].apply(json.dumps)
    out[["nct_id", "status", "n_hits", "window_used", "terms_json", "hits_json"]].to_csv(
        "data/interim/21_edgar_rebuild_search_results.csv", index=False
    )

    print("\n" + out["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
