"""Sanity-check script for the rebuilt price/abnormal-return module (step 5 of
the methodology's concrete build sequence). Runs compute_abnormal_returns on a
few real, known announcement dates and prints the full per-day abnormal-return
series plus CAR, so the plumbing can be checked by eye against known outcomes
(e.g. KOD's 2023-07-24 readout, a known bad day for the company).
"""
import sys
sys.path.insert(0, "src")

import pandas as pd

from hedgefund.prices import compute_abnormal_returns

TEST_CASES = [
    ("KOD", "2023-07-24"),
    ("AMGN", "2020-10-28"),
    ("JAZZ", "2020-11-02"),
]


def main():
    pd.set_option("display.float_format", lambda x: f"{x:.5f}")
    pd.set_option("display.width", 140)

    for ticker, announcement_date in TEST_CASES:
        print("=" * 80)
        print(f"{ticker}  announcement_date={announcement_date}")
        result = compute_abnormal_returns(ticker, announcement_date)
        print(f"anchor_date (T0, first trading day >= announcement): {result['anchor_date']}")
        print(f"benchmark: {result['benchmark']}   alpha={result['alpha']:.6f}   beta={result['beta']:.4f}")
        print(result["event_window"].to_string(index=False))
        print(f"\nCAR (T-30..T+5): {result['car']:.4f}")
        print()


if __name__ == "__main__":
    main()
