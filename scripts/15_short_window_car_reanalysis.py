"""Recompute CAR with a short T-2..T+2 event window (keeping alpha) for the
211 CTOD-era trials that already have cached daily event-window data in
data/processed/full_pool_event_windows.json -- no new network calls needed.

Purpose: the 25-trial sign_disagreement flag was caused by the full T-30..T+5
window's alpha term compounding over 36 days (see STATUS.md and the
short_window_car docstring in src/hedgefund/prices.py). This script checks
whether a short window resolves the sign disagreement for the 211 cached
trials and how it shifts the Phase 3 Failure vs Success headline result.

Does NOT touch the 49 trials from the supplementary funnels (business
terminations, 2024-05+ CT.gov extension) -- those aren't cached and would
need a live yfinance re-fetch, out of scope for this pass.
"""
import sys
sys.path.insert(0, "src")

import json
import pandas as pd
from scipy import stats

from hedgefund.prices import short_window_car

with open("data/processed/full_pool_event_windows.json") as f:
    event_windows = json.load(f)

combined = pd.read_csv("data/processed/combined_phase_outcome_analysis.csv")

rows = []
for nct_id, records in event_windows.items():
    w = pd.DataFrame(records)
    short = short_window_car(w, pre=2, post=2)
    rows.append({"nct_id": nct_id, "short_car": short["car"], "short_raw": short["raw_return"]})

short_df = pd.DataFrame(rows)
merged = combined.merge(short_df, on="nct_id", how="inner")  # inner: only the 211 cached trials

merged["short_sign_disagreement"] = (merged["short_car"] > 0) != (merged["short_raw"] > 0)
# treat near-zero raw moves (<0.5%) as noise, not a real disagreement
merged.loc[merged["short_raw"].abs() < 0.005, "short_sign_disagreement"] = False

print(f"Cached CTOD-era trials with event-window data: {len(merged)}")
print()

was_flagged = merged[merged["sign_disagreement"] == True]
print(f"Previously flagged sign_disagreement (full window), present in this cache: {len(was_flagged)}")
still_flagged = was_flagged[was_flagged["short_sign_disagreement"] == True]
print(f"Still sign-disagreeing under short T-2..T+2 window: {len(still_flagged)}")
if len(still_flagged):
    print(still_flagged[["nct_id", "ticker", "car", "short_car", "short_raw"]].to_string(index=False))
print()

newly_flagged = merged[(merged["sign_disagreement"] == False) & (merged["short_sign_disagreement"] == True)]
print(f"Newly flagged under short window (previously fine): {len(newly_flagged)}")
if len(newly_flagged):
    print(newly_flagged[["nct_id", "ticker", "car", "short_car", "short_raw"]].to_string(index=False))
print()

# Headline result check: Phase 3 Failure vs Success, using short_car in place
# of car, restricted to the same quality gates minus sign_disagreement (which
# short_car is meant to fix) -- still exclude unstable_estimation and
# needs_reverification.
clean = merged[(merged["unstable_estimation"] == False) & (merged["needs_reverification"] == False)]
p3 = clean[clean["phase_clean"] == "Phase 3"]
fail = p3[p3["category_clean"] == "Failure"]["short_car"]
succ = p3[p3["category_clean"] == "Success"]["short_car"]
print(f"Phase 3 Failure n={len(fail)}, Success n={len(succ)} (short-window CAR, sign_disagreement NOT excluded)")
if len(fail) > 1 and len(succ) > 1:
    u, p = stats.mannwhitneyu(fail, succ, alternative="two-sided")
    print(f"Mann-Whitney U p={p:.4f}, Failure median short_car={fail.median():.4f}, Success median={succ.median():.4f}")

# Compare to the original car-based result on the SAME clean subset (before
# excluding sign_disagreement) as a baseline for comparison.
fail_orig = p3[p3["category_clean"] == "Failure"]["car"]
succ_orig = p3[p3["category_clean"] == "Success"]["car"]
u2, p2 = stats.mannwhitneyu(fail_orig, succ_orig, alternative="two-sided")
print(f"\n[baseline, same n, full-window car, sign_disagreement NOT excluded] p={p2:.4f}, "
      f"Failure median={fail_orig.median():.4f}, Success median={succ_orig.median():.4f}")

merged.to_csv("data/interim/15_short_window_car_reanalysis.csv", index=False)
print("\nWrote data/interim/15_short_window_car_reanalysis.csv")
