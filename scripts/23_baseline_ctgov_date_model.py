"""Baseline model: price stock reaction using ONLY the trial's own
ClinicalTrials.gov data -- no SEC filing search, no EDGAR verification.

This is deliberately a separate, simpler model from the EDGAR-matched
pipeline (scripts 13-22), built to answer a direct question: how much of
the headline result depends on the expensive filing-verification work,
versus what a much cheaper, fully-mechanical baseline would already show?

Ground truth label: category_clean (Success/Failure/Business Termination),
using the session's corrected labels (CORT reclassified to Failure).

Pricing date: results_first_posted_date, NOT primary_completion_date.
Rationale (from the session discussion this baseline was requested to
settle): completion date is a clinical/operational milestone with no
public disclosure attached -- pricing around it would mostly measure
noise. results_first_posted_date is a genuine, discrete, publicly visible
event on a registry that specialized biotech investors do monitor
directly, even though it is NOT necessarily the same date as any company
press release (structured CT.gov results often post well after a
company's own topline announcement). This baseline is explicitly testing
the "market reacts to the registry update itself" hypothesis, not
"market reacts to a press release" -- that's a different, weaker, but
much cheaper and fully-mechanical claim than the EDGAR-matched pipeline
tests, and worth measuring on its own terms for comparison.
"""
import sys
sys.path.insert(0, "src")

import time
import pandas as pd
from hedgefund.prices import compute_abnormal_returns, short_window_car

combined = pd.read_csv("data/processed/combined_phase_outcome_analysis.csv")
ctgov = pd.read_csv("data/interim/20_ctgov_acronym_dates_all260.csv")

df = combined[["nct_id", "ticker", "phase_clean", "category_clean"]].merge(
    ctgov[["nct_id", "results_posted"]], on="nct_id", how="left"
)
df = df.dropna(subset=["results_posted"])
print(f"{len(df)} of {len(combined)} trials have a results_first_posted_date")

rows = []
errors = []
for i, row in df.iterrows():
    try:
        result = compute_abnormal_returns(row["ticker"], row["results_posted"])
        short = short_window_car(result["event_window"], pre=2, post=2)
        rows.append({
            "nct_id": row["nct_id"], "ticker": row["ticker"],
            "phase_clean": row["phase_clean"], "category_clean": row["category_clean"],
            "results_posted": row["results_posted"],
            "baseline_car": short["car"], "baseline_raw": short["raw_return"],
        })
    except Exception as e:
        errors.append({"nct_id": row["nct_id"], "ticker": row["ticker"], "error": str(e)})
    if (i + 1) % 25 == 0:
        print(f"{i+1}/{len(df)}")
    time.sleep(0.05)

out = pd.DataFrame(rows)
out.to_csv("data/processed/baseline_ctgov_date_model.csv", index=False)
print(f"\nPriced {len(out)} of {len(df)} trials, {len(errors)} errors (usually insufficient price history)")
if errors:
    pd.DataFrame(errors).to_csv("data/interim/23_baseline_pricing_errors.csv", index=False)
