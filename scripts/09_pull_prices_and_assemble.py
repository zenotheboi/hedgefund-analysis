"""Day-1 pipeline final step: pull T-30..T+5 price data + abnormal returns
(vs XBI) for every resolved, verified candidate, then assemble the Day-1
20/20 pilot dataset plus the full reserve pool for later scaling.
"""
import sys
sys.path.insert(0, "src")

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

from hedgefund.prices import compute_abnormal_returns

MAX_WORKERS = 6


def pull_one(row):
    try:
        r = compute_abnormal_returns(row["ticker"], row["verified_filing_date"])
        return row["nct_id"], r, None
    except Exception as e:
        return row["nct_id"], None, str(e)


def main():
    df = pd.read_csv("data/interim/08_final_candidates.csv", low_memory=False)
    print(f"Pulling price data for {len(df)} candidates")

    results, errors = {}, {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(pull_one, row) for _, row in df.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures)):
            nct_id, r, err = fut.result()
            if r:
                results[nct_id] = r
            else:
                errors[nct_id] = err

    print(f"\nSucceeded: {len(results)}  Failed: {len(errors)}")
    if errors:
        print("Sample errors:")
        for nct_id, err in list(errors.items())[:5]:
            print(" ", nct_id, "->", err)

    df["car"] = df["nct_id"].map(lambda n: results[n]["car"] if n in results else None)
    df["price_beta"] = df["nct_id"].map(lambda n: results[n]["beta"] if n in results else None)
    df["price_anchor_date"] = df["nct_id"].map(lambda n: results[n]["anchor_date"] if n in results else None)
    df["price_pull_error"] = df["nct_id"].map(errors)

    df.to_csv("data/processed/full_pool_with_prices.csv", index=False)

    event_windows = {n: r["event_window"].to_dict(orient="records") for n, r in results.items()}
    json.dump(event_windows, open("data/processed/full_pool_event_windows.json", "w"), default=str)

    priced = df[df["car"].notna()]
    print(f"\nFinal priced pool: {len(priced)}")
    print(priced["outcome_category"].value_counts())

    # Day-1 20/20 pilot: prefer the highest-confidence verifications
    # (explicit NCT ID citation, or manually-confirmed hidden negatives)
    def confidence_rank(row):
        if row["nct_id"] in {"NCT04657666"}:
            return 0  # explicit NCT ID citation in filing text
        if pd.notna(row.get("label_correction_reason")):
            return 1  # manually confirmed via full-text read
        return 2

    priced = priced.copy()
    priced["_rank"] = priced.apply(confidence_rank, axis=1)

    pos = priced[priced["outcome_category"] == "success"].sort_values("_rank").head(20)
    neg = priced[priced["outcome_category"] == "failure_efficacy_safety"].sort_values("_rank").head(20)
    pilot = pd.concat([pos, neg]).drop(columns="_rank")
    pilot.to_csv("data/processed/pilot_20_20.csv", index=False)

    print(f"\nDay-1 pilot: {len(pos)} positive / {len(neg)} negative -> data/processed/pilot_20_20.csv")
    print(f"Full reserve pool: {len(priced)} -> data/processed/full_pool_with_prices.csv")

if __name__ == "__main__":
    main()
