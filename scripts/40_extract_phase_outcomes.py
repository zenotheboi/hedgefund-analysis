"""Phase 0a: extract trial OUTCOME (met / miss / ambiguous) from the
BioPharmCatalyst Catalyst Description text for Phase 1/2/3 rows, so the
failure/success universe can be expanded beyond the 30 regulatory CRLs.

Kept as SEPARATE per-phase categories (Phase 3 miss != Phase 2 miss != CRL),
per the user's instruction -- not mixed into the CRL bucket.

Outcome rules are priority-ordered so "primary endpoint met, key secondary
missed" resolves to MET (the primary endpoint is what determines whether the
drug's pivotal result succeeded; a secondary miss is secondary).
"""
import re
import pandas as pd

IN = "data/interim/25_biopharmcatalyst_clean.csv"
OUT = "data/interim/40_phase_outcomes.csv"

PHASE_LABELS = ["Phase 3", "Phase 2/3", "Phase 2", "Phase 2a", "Phase 2b",
                "Phase 1/2", "Phase 1", "Phase 1b"]

# --- outcome keyword sets, checked in priority order ---
MISS = re.compile(
    r"did not meet|didn't meet|failed to|\bfailed\b|does not meet|not meet|not met|"
    r"endpoints? not met|no survival benefit|no benefit|no significant|did not achieve|"
    r"missed (its |the )?primary|discontinu|terminat(ed|ing) .*efficacy|"
    r"halted .*futility|stopped .*futility|futility|negative (results|data|topline)|"
    r"lack of efficacy",
    re.IGNORECASE)
MET = re.compile(
    r"\bmet\b|met all|met both|met its|met the|met primary|met co-primary|"
    r"meeting (its |the )?primary|achieved|statistically significant|positive (results|data|topline)|"
    r"primary endpoint(s)? (was |were )?met|demonstrated .*benefit|superior to",
    re.IGNORECASE)

DATE_RE = re.compile(r"([A-Z][a-z]+ \d{1,2},? \d{4})")


def normalize_phase(label: str) -> str:
    if label in ("Phase 3", "Phase 2/3"):
        return "Phase 3"
    if label in ("Phase 2", "Phase 2a", "Phase 2b"):
        return "Phase 2"
    return "Phase 1"  # Phase 1, 1b, 1/2 -- rarely tradeable, kept for completeness


def classify(desc: str) -> str:
    d = desc or ""
    # a "primary met" statement overrides a trailing "secondary missed"
    primary_met = re.search(r"primary endpoint(s)?( (was|were))? met|met (its |the |all |both )?"
                            r"(co-)?primary", d, re.IGNORECASE)
    if primary_met and not re.search(r"did not meet (its )?primary|failed", d, re.IGNORECASE):
        return "met"
    if MISS.search(d):
        return "miss"
    if MET.search(d):
        return "met"
    return "ambiguous"


def first_date(desc: str):
    m = DATE_RE.search(desc or "")
    if not m:
        return None
    for fmt in ("%B %d, %Y", "%B %d %Y"):
        try:
            return pd.Timestamp(pd.to_datetime(m.group(1), format=fmt))
        except (ValueError, TypeError):
            continue
    try:
        return pd.Timestamp(pd.to_datetime(m.group(1)))
    except Exception:
        return None


df = pd.read_csv(IN, parse_dates=["Catalyst Date"])
p = df[df["Approved or CRL"].isin(PHASE_LABELS)].copy()
p["desc"] = p["Catalyst Description"].fillna("")
p["phase"] = p["Approved or CRL"].map(normalize_phase)
p["outcome"] = p["desc"].map(classify)
p["desc_date"] = p["desc"].map(first_date)
# pricing anchor = BPC Catalyst Date (validated for the Approved/CRL set);
# desc_date kept for QA / mismatch flagging
p["anchor_date"] = p["Catalyst Date"]
p["date_mismatch_days"] = (p["desc_date"] - p["Catalyst Date"]).dt.days.abs()

p["category"] = p["phase"] + " " + p["outcome"].map({"met": "met", "miss": "miss", "ambiguous": "ambiguous"})

out = p[["Ticker", "Drug Name", "phase", "outcome", "category", "anchor_date",
         "desc_date", "date_mismatch_days", "Catalyst Description"]].rename(
    columns={"Ticker": "ticker", "Drug Name": "drug_name",
             "Catalyst Description": "description"})
out.to_csv(OUT, index=False)

# coverage report
print(f"Phase 1/2/3 rows: {len(p)}")
print("\noutcome x phase:")
print(p.groupby(["phase", "outcome"]).size().unstack(fill_value=0))
print(f"\nembedded date found: {p['desc_date'].notna().sum()}/{len(p)}")
print(f"date mismatch >5d (anchor vs desc): {(p['date_mismatch_days'] > 5).sum()}")
w = p[(p['Catalyst Date'].dt.year >= 2014) & (p['Catalyst Date'].dt.year <= 2020)]
print(f"\n2014-2020 tradeable (met/miss only, Phase 2/3):")
tp = w[(w.phase.isin(['Phase 2', 'Phase 3'])) & (w.outcome.isin(['met', 'miss']))]
print(tp.groupby(["phase", "outcome"]).size().unstack(fill_value=0))
print(f"\nwrote {OUT}")
