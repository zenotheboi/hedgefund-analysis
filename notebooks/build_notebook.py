"""Builds notebooks/methodology_and_analysis.ipynb programmatically.
Run this, then `jupyter nbconvert --to notebook --execute --inplace` it,
whenever the underlying data/methodology changes -- don't hand-edit the
.ipynb, edit this builder instead so the notebook stays reproducible.
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

# ---------------------------------------------------------------------------
md("""# Clinical Trial Outcome → Price Reaction: Methodology & Analysis

Day-1 prototype for the hedge-fund feasibility project (see `/README.md` and the
original methodology brief). This notebook is the durable record of **how the
dataset was built, what was checked, what broke, and what the current
statistical results actually support** — as opposed to the pipeline scripts,
which do the work but don't explain the reasoning or the traps found along
the way.

**2026-07-14 note:** a long audit session this day found and fixed two
significant bugs (the abnormal-return estimator, and the EDGAR filing-match
verification), corrected several mislabeled trial outcomes, and built an
independent baseline model to test whether the verification work actually
matters (it does). This notebook has been regenerated to reflect all of
that. Full session detail beyond what's summarized here lives in
`/STATUS.md` and the `data/interim/` working files.

**Rule for this notebook:** when the pipeline changes, re-run
`build_notebook.py` and re-execute — don't hand-edit the `.ipynb`.
""")

# ---------------------------------------------------------------------------
md("""## 1. Data filtering funnel

Two funnels feed the final dataset: the **primary funnel** (CTOD's
2020-2024-completions dataset) and a **supplementary funnel** (queried
directly from ClinicalTrials.gov, completions 2024-05 onward) added later
specifically to close a negative-case shortage the primary funnel left behind
(see §1b). Both produce the same shape of output -- a trial with a verified
public ticker, a confirmed small-molecule/peptide modality, and a priced
event window -- so they combine into one analysis dataset.

**Important scope note (found 2026-07-14):** the PubChem-verified,
chemically in-scope candidate pool is 628 trials
(`data/interim/04_pubchem_verified.csv`, filtered to
`pubchem_verified_small_molecule_or_peptide == True` -- the file itself is
a candidate pool that was *checked* against PubChem, not a pre-filtered
result, and using it unfiltered was a real bug caught mid-session). Of
those 628, only 252-260 ever made it into the final priced dataset below --
the rest were dropped by the old EDGAR-matching pipeline before ever being
priced. §10-11 investigate whether that drop was justified.""")

code("""import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

pd.set_option('display.width', 120)
pd.set_option('display.max_columns', 20)

raw = pd.read_csv('../data/raw/ctod/human_labels_2020_2024.csv', low_memory=False)
print(f"Raw CTOD dataset: {len(raw)} trials, completions {raw['completion_date'].min()} to {raw['completion_date'].max()}")
""")

md("""### 1a. Primary funnel (CTOD, 2020-2024)""")

code("""primary_funnel = pd.DataFrame([
    {"stage": "1. Raw CTOD trials (all phases, all sponsor types)", "n": 11012,
     "why": "Starting universe -- CTOD's manually-annotated 2020-2024 completion subset"},
    {"stage": "2. Phase 1-3, industry-sponsored", "n": 5222,
     "why": "Scope requires Phase 1-3; industry sponsor is a cheap proxy for 'could plausibly be a public company'"},
    {"stage": "3. Verified public company (SEC ticker + pharma SIC code)", "n": 1839,
     "why": "Need a tradable ticker; SIC-code cross-check catches fuzzy-match false positives (Celgene->Clene, Alexion->Lexicon)"},
    {"stage": "4. Verified small molecule/peptide (PubChem molecular weight)", "n": 628,
     "why": "Mandatory scope filter per the source brief -- CT.gov's own type tag alone isn't reliable (mis-tags biologics as DRUG)"},
    {"stage": "5a. Verified announcement date + priced -- success/failure track", "n": 211,
     "why": "EDGAR filing fetched and read; date/outcome only accepted if text actually confirms this specific trial (see §10 -- this verification step's own reliability was found to be much weaker than assumed)"},
    {"stage": "5b. Verified announcement date + priced -- business-termination track", "n": 38,
     "why": "Same verification, run separately on the business_termination category (see §1c for category definitions)"},
])
primary_funnel
""")

md("""### 1b. Why a supplementary funnel was needed

The primary funnel's negative-outcome pool was thin (29 verified failures vs.
182 successes) even before this was pointed out and investigated -- CTOD hard-
codes all TERMINATED/WITHDRAWN/SUSPENDED trials as "failure" regardless of
cause, which inflates the *apparent* negative supply while the *genuine*
efficacy/safety-failure supply is actually small once business/logistics
terminations are correctly excluded (see §3). The supplementary funnel pulls
directly from ClinicalTrials.gov (no CTOD dependency) across four parallel
tracks, each using a different way to find candidates likely to be genuine
negatives:""")

code("""supplementary_funnel = pd.DataFrame([
    {"track": "Terminated/withdrawn/suspended (2024-05 onward)", "starting_pool": 1192,
     "after_triage": 94, "verified_public_co": 38, "verified_modality": 18,
     "final_confirmed_priced": 11,
     "signal_used": "why_stopped text classified as genuine efficacy/safety reason"},
    {"track": "Completed, posted results (2024-05 onward)", "starting_pool": 946,
     "after_triage": 140, "verified_public_co": 36, "verified_modality": "17 (15 new)",
     "final_confirmed_priced": "(merged with row above)",
     "signal_used": "CT.gov's own structured primary-outcome p-value >= 0.05"},
    {"track": "Completed, no posted results (sample batch)", "starting_pool": "300 of 3283",
     "after_triage": "n/a -- no signal available", "verified_public_co": 73, "verified_modality": 22,
     "final_confirmed_priced": 0,
     "signal_used": "none -- every EDGAR hit read manually; all 14 hits were false matches"},
    {"track": "Ambiguous_termination re-read (CTOD-era, 2020-2024)", "starting_pool": 85,
     "after_triage": 21, "verified_public_co": 20, "verified_modality": "(already verified)",
     "final_confirmed_priced": 2,
     "signal_used": "manual reading of why_stopped text the automated classifier scored as ambiguous"},
])
supplementary_funnel
""")

md("""**Net result of the supplementary funnel: 11 net new negatives**,
bringing the total from 29 to 40. The "completed, no posted results" track
is included here specifically as a negative result: it cost real effort
(300 trials pulled, 73 ticker-matched, 22 modality-verified, 14 EDGAR hits
manually read) for zero yield, because without a `why_stopped` reason or a
p-value to pre-filter on, the EDGAR verification heuristic's false-positive
rate is too high on its own -- worth recording so this path isn't retried
the same way. (§10 finds this false-positive-rate problem was much more
pervasive than this one track suggested -- it affected the "successful"
matches too, not just this specific zero-yield search.)""")

md("""### 1c. Final categorization for analysis""")

code("""final = pd.read_csv('../data/processed/combined_phase_outcome_analysis.csv')
flag_table = final[['unstable_estimation','needs_reverification','sign_disagreement','trustworthy']].sum()
flag_table['total_trials'] = len(final)
flag_table
""")

md("""**A trial counts as `trustworthy` only if all three flags below are
clean.** All three were found and refined over the course of the 2026-07-14
session -- full detail in §10-11.

1. `unstable_estimation` -- the pre-event estimation window had an
   outsized (>50%) idiosyncratic price move (e.g. Aclaris/ACRS rallied 6x
   before its readout for unconnected reasons), destabilizing the fitted
   market-model baseline.
2. `needs_reverification` -- the trial-to-SEC-filing match is confirmed
   wrong, confirmed generic (mentions the drug but discloses no specific
   result), or was never individually verified at all. **This is the large
   majority of exclusions and the dataset's core open problem** -- see §10.
3. `sign_disagreement` -- the abnormal (market-adjusted) return and the raw
   stock return disagree on direction. Investigated in §11: about half of
   these cases were a real estimator problem, the other half were the
   market-adjustment correctly netting out a genuine sector-wide move on
   the event days themselves (i.e. not a bug).

Trials that fail a flag are kept in the dataset, never deleted -- excluded
only from summary means/medians below.

Categories not carried into the phase x outcome price analysis:
`logistics_termination` and `ambiguous_termination` (see the pool table in
§1) -- not yet manually re-read at the scale needed to trust them, retained
in the interim data files for future scaling.""")

# ---------------------------------------------------------------------------
md("""## 2. Data sources & scripts
- CTOD dataset (`chufangao/CTO` on Hugging Face) — trial metadata + a
  manually-annotated outcome label subset (2020-2024 completions). CTOD's own
  `news_headlines`/`stock_price` modules were inspected and NOT reused as-is
  — only their *scraped news dates* are reused, as a fallback candidate
  source, never trusted standalone.
- SEC EDGAR (full-text search API `efts.sec.gov`, submissions API, filing
  documents) — the primary source for verified announcement dates. Search
  both `8-K` (US domestic filers) and `6-K` (foreign private issuers --
  Novo Nordisk, Novartis, AstraZeneca, Sanofi all file 6-K, never 8-K;
  missing this was a real bug found and fixed 2026-07-14, see §10).
- ClinicalTrials.gov v2 API — live per-trial intervention data for modality
  classification, plus `primaryCompletionDate`/`resultsFirstPostDate`/
  `acronym` used as search anchors and (separately) as the independent
  baseline model's pricing date (§11).
- PubChem PUG REST API — molecular-weight ground truth for small-molecule/
  peptide verification.
- yfinance — daily price history for event-window abnormal returns.

**Scripts, in pipeline order** (`scripts/`):
`01_build_candidates` (ticker match) → `02_modality_filter` (CT.gov type/name
heuristic) → `03_pubchem_verify` → `04_find_announcement_dates` (EDGAR search
+ text verification, superseded by `22_edgar_rebuild_search_and_score` --
see §10) → `06_scan_hidden_negatives` / `07_scan_unresolved_for_negatives`
(mine the "success" bucket for mislabels) → `08_reclassify_and_assemble` →
`09_pull_prices_and_assemble` → `10_process_business_terminations` →
`15_short_window_car_reanalysis` (CAR estimator fix, §6) →
`20`-`22_edgar_rebuild_*` (EDGAR rematch pipeline, §10) →
`24_baseline_full_pool` (independent baseline, §11).
""")

# ---------------------------------------------------------------------------
md("""## 3. Key methodological decisions and bugs caught

Each of these was a real bug found by testing against known cases, not a
hypothetical concern. Kept here so they aren't silently reintroduced.

| Stage | Decision / bug found | Fix |
|---|---|---|
| Ticker matching | Fuzzy match alone produced false positives: "Celgene" → "Clene Inc." (unrelated), "Vertex Pharmaceuticals" → "Vertex, Inc." (tax software) | Added SIC-code verification + a substring-containment guard requiring the shorter name to actually appear in the longer one (unless score ≥95) |
| Modality filter | ClinicalTrials.gov's own `type` field mis-tags antibody/protein drugs as plain `DRUG` (e.g. KSI-301/tarcocimab tedromer, an antibody-biopolymer conjugate) | Added an INN-suffix biologic detector (`-mab`, `-cept`, etc.) independent of CT.gov's tag, PLUS mandatory PubChem molecular-weight cross-check |
| PubChem verification | Applying it only to the "ambiguous" bucket wasn't enough — of the 784 trials that *looked* fine by CT.gov type, only 417 (53%) actually held up under real PubChem lookup | Ran PubChem verification on BOTH the clear-pass and ambiguous buckets |
| Outcome categorization | CTOD hard-codes all TERMINATED/WITHDRAWN/SUSPENDED trials as "failure" regardless of cause. Naive keyword classification of `why_stopped` also mishandled negation ("not based on any new efficacy or safety data" was matched as a *failure* reason because "efficacy" appeared) | Split into success / failure_efficacy_safety / business_termination / logistics_termination / ambiguous_termination, with a negation-aware regex checked before the plain keyword match |
| EDGAR search (original) | Blind keyword search found "hits" that were false positives at a rate later measured (2026-07-14) at 50-90% depending on the sample — a drug name in a routine earnings release, a generic multi-program pipeline chart, or a mention of a *different specific trial* of the same drug | Rebuilt entirely — see §10. The original description of this fix ("require 2+ distinctive keywords") turned out to be insufficient; the real fix needed a specific trial-acronym/development-code search key plus result-language proximity scoring, not just keyword co-occurrence |
| Hidden negatives (round 1) | CTOD's "success" label undercounts real failures — confirmed by reading actual filing text, not by trusting the label | Found and reclassified 9 confirmed + 3 candidate hidden negatives (§5) |
| Hidden negatives (round 2, 2026-07-14) | Two more found unrelated to the original scan: NCT04329949/CORT's own `why_stopped` text describes an efficacy/futility stop mislabeled as a business termination; NCT03672175/BIIB's labeled "Success" but its actual result (filed under co-developer Sage Therapeutics' CIK, not Biogen's) explicitly states the MOUNTAIN study "did not meet primary endpoint" | Both reclassified to Failure (§5) |
| Price / CAR estimator (2026-07-14) | CAR summed a fitted daily `alpha` over a 36-trading-day window (T-30..T+5) — estimation noise/drift compounds over the whole window and often swamped the real announcement reaction, sometimes producing non-physical CARs (e.g. -101%, +84%) | Short T-2..T+2 window (`short_window_car()`), keeping alpha (still a legitimate part of the stock's normal-behavior baseline) but not extrapolating it over a month. Full mechanism and evidence in §6 |
""")

# ---------------------------------------------------------------------------
md("""## 4. Data loading""")

code("""combined = pd.read_csv('../data/processed/combined_phase_outcome_analysis.csv')
print(f"Combined phase/outcome/price dataset: {len(combined)} trials, {combined['trustworthy'].sum()} trustworthy")
""")

# ---------------------------------------------------------------------------
md("""## 5. Hidden negatives found in the "success"/"business termination" buckets

CTOD's own label (or this pipeline's own categorization) said one thing;
the actual disclosed filing text says another. Found by regex-scanning
verified filings for negative-outcome language (round 1), then later by
directly reading `why_stopped` text and cross-checking specific price
outliers against their actual disclosures (round 2, 2026-07-14). In both
rounds, most raw hits were false positives — e.g. a mention of a *different*
trial of the same drug in the same filing — so every hit was manually
cross-checked against the actual trial identity before reclassifying.""")

code("""hidden_negatives = pd.DataFrame([
    {"nct_id": "NCT03745820", "drug_study": "BIIB104, TALLY study (schizophrenia)", "evidence": "did not meet primary/secondary endpoints"},
    {"nct_id": "NCT03931291", "drug_study": "eprenetapopt (APR-246) + azacitidine, TP53-MDS", "evidence": "failed to meet primary endpoint (complete remission)"},
    {"nct_id": "NCT04402866", "drug_study": "nezulcitinib (TD-0903), COVID ALI", "evidence": "did not meet the primary endpoint"},
    {"nct_id": "NCT03750552", "drug_study": "ampreloxetine (TD-9855), nOH", "evidence": "did not meet the primary endpoint"},
    {"nct_id": "NCT04657666", "drug_study": "nabiximols, RELEASE MSS1", "evidence": "text cites the NCT ID by name -- gold-standard certainty"},
    {"nct_id": "NCT05047601", "drug_study": "Paxlovid, EPIC-PEP (post-exposure)", "evidence": "primary endpoint not met"},
    {"nct_id": "NCT04410991", "drug_study": "tolebrutinib, GEMINI 1 (RMS)", "evidence": "did not show significance in primary endpoint"},
    {"nct_id": "NCT04410978", "drug_study": "tolebrutinib, GEMINI 2 (RMS)", "evidence": "did not show significance in primary endpoint"},
    {"nct_id": "NCT03990363", "drug_study": "verinurad, AstraZeneca", "evidence": "explicit program-discontinuation disclosure"},
    {"nct_id": "NCT04329949", "drug_study": "relacorilant + nab-paclitaxel, CORT (pancreatic cancer)", "evidence": "2026-07-14: why_stopped says response rate missed predefined threshold -- was mislabeled Business Termination"},
    {"nct_id": "NCT03672175", "drug_study": "SAGE-217/zuranolone, MOUNTAIN study (MDD)", "evidence": "2026-07-14: filed under co-developer Sage Therapeutics' CIK, not Biogen's -- explicitly 'did not meet primary endpoint'"},
])
print("Confirmed hidden negatives (reclassified to Failure):")
hidden_negatives
""")

md("""Three more (Akebia's vadadustat PRO2TECT program: `NCT02892149`,
`NCT02680574`, `NCT02865850`) are a nuanced case — they *met* their efficacy
endpoint but explicitly *missed* the primary safety endpoint (MACE
non-inferiority), which in reality blocked FDA approval in the non-dialysis
population. Reclassified as failures for the same reason: the scientifically
and commercially relevant outcome was negative even though CTOD's binary
label said success.

One caught-and-reverted error, kept here as a reminder that manual review
isn't automatically immune to the same mistake: `NCT03624127` (BMS-986165 /
deucravacitinib, plaque psoriasis) was initially misread as a confirmed
hidden negative based on text that actually belonged to a *different* BMY
drug in the same filing. Excluded from the final dataset entirely (folded
into `needs_reverification`) rather than left on an unverified label.

**2026-07-14 addendum:** the independent baseline model in §11 found 5
*more* mislabeled efficacy failures in the wider 628-trial pool
(NCT03762265/SNY, NCT03459443/LXRX, NCT04492722/AZN, NCT04323124/PFE,
NCT04139317/NVS) — none of these happen to be in the 260-trial priced
dataset, so they don't change the numbers above, but they're strong
evidence this kind of mislabeling is a general, ongoing risk in the source
categorization, not a handful of one-off mistakes already fully found.""")

# ---------------------------------------------------------------------------
md("""## 6. Price / abnormal-return methodology (CORRECTED 2026-07-14)

For each verified announcement date:

1. Pull daily closes for the ticker and **XBI** (biotech sector ETF)
   spanning an **estimation window** (120 trading days, ending at T-31)
   plus the **event window**.
2. Fit `stock_return ~ alpha + beta * XBI_return` via OLS on the estimation
   window only (never touching the event window -- avoids look-ahead bias).
3. `abnormal_return_t = actual_stock_return_t - (alpha + beta * XBI_return_t)`
   for every day in the event window.
4. `CAR = sum(abnormal_return)` over the event window.

### The bug, and why it mattered

The event window was originally **T-30..T+5** (36 trading days). Each
day's `alpha` is a *constant* — summing it over 36 days means any
estimation error or real secular trend in that constant compounds
linearly with window length. In practice this meant the "expected return"
baseline for many trials was comparable to, or larger than, the entire
actual price move — swamping the genuine announcement reaction rather
than isolating it. Two trials in the original dataset had non-physical
resulting CARs (RLMD: -101%; KPTI: +84%), which should have been a red
flag on its own.

**Fix:** shrink the event window to **T-2..T+2** (`short_window_car()` in
`src/hedgefund/prices.py`). This keeps alpha — it's still a legitimate
part of a stock's normal-behavior baseline, e.g. a persistent
cash-runway narrative — it just stops asking a month-old drift estimate
to explain price action from days the event couldn't plausibly have
caused. This is also the more standard choice in the event-study
literature (MacKinlay 1997): CAR variance and bias grow with window
length, which is why practice generally keeps windows short.

### Evidence this was a real bug, not a stylistic preference

Comparing short-window raw return to short-window abnormal return (i.e.
"does the market-adjustment even get the *direction* of the actual
announcement-week move right") agreed in sign 17 of 18 checked cases — the
one disagreement had a near-zero raw move (noise either way). The
long-window CAR, by contrast, disagreed with the actual announcement
reaction on 25 of 260 trials before the fix. An independent baseline model
built later in the session (§11) provides a second, more direct piece of
evidence: the same trials/labels, differing only in which date is used to
price the reaction, go from p=0.61 (no effect) to p=0.011 (real effect) —
the estimator and date precision are not cosmetic details.

`unstable_estimation` flags any trial where the estimation-window total
return exceeds +/-50% -- this remains a real, separate risk (a volatile
pre-event window distorts alpha/beta even under a short event window) and
is excluded from summary statistics below, though kept in the dataset.""")

code("""print("Flagged (unstable market-model fit):", combined['unstable_estimation'].sum(),
      "of", len(combined), f"({combined['unstable_estimation'].mean()*100:.0f}%)")
combined[combined['unstable_estimation']][['nct_id','ticker','phase_clean','category_clean','car','estimation_window_return']] \\
    .sort_values('estimation_window_return', key=abs, ascending=False).head(10)
""")

# ---------------------------------------------------------------------------
md("""## 7. Data summary: CAR by phase x outcome (trustworthy subset)""")

code("""clean = combined[combined['trustworthy']].copy()

summary = clean.groupby(['phase_clean','category_clean'])['car'].agg(['count','mean','median','std']).round(4)
summary
""")

# ---------------------------------------------------------------------------
md("""## 8. Statistical significance

**What a p-value answers here:** not "how big is the price move" (that's the
CAR% itself) -- it answers "if trial outcome truly had no effect on price,
how often would random luck alone produce a gap this large, given the noise
in stock returns and how few trials we have in each group?" A small p-value
means the observed gap is unlikely to be a fluke of which companies happened
to land in the sample.

CAR is heavily non-normal (checked below), so **Mann-Whitney U** is the
primary test for two-sample comparisons; **Wilcoxon signed-rank** is used
for one-sample (vs. zero) comparisons.""")

code("""stat, p = stats.shapiro(clean['car'])
print(f"Shapiro-Wilk normality test: p = {p:.2e}  (p<0.05 => NOT normal)")
print(f"skewness = {clean['car'].skew():.2f}, kurtosis = {clean['car'].kurtosis():.2f}")
""")

md("### 8a. Per-phase: Success vs Failure, plus win rate")

code("""for phase in ['Phase 1', 'Phase 2', 'Phase 3']:
    sub = clean[clean['phase_clean'] == phase]
    succ = sub[sub['category_clean'] == 'Success']['car']
    fail = sub[sub['category_clean'] == 'Failure']['car']
    if len(succ) >= 3 and len(fail) >= 3:
        u, p = stats.mannwhitneyu(succ, fail, alternative='two-sided')
        print(f"{phase}: n_success={len(succ)} n_failure={len(fail)} | Mann-Whitney p={p:.4f}")
    else:
        print(f"{phase}: n_success={len(succ)} n_failure={len(fail)} -- too few for a test")

print()
print("Win rate (% of trials with positive CAR), all phase x outcome cells:")
for phase in ['Phase 1', 'Phase 2', 'Phase 3']:
    for cat in ['Success', 'Failure', 'Business Termination']:
        s = clean[(clean['phase_clean']==phase) & (clean['category_clean']==cat)]
        if len(s) == 0:
            continue
        print(f"  {phase} {cat}: n={len(s)}, win rate = {(s['car']>0).mean()*100:.0f}%")
""")

md("""### 8b. Common-language effect size

The p-value answers "how likely is this separation to be a fluke of
sampling." A more directly interpretable companion statistic: **for a
randomly chosen Failure trial and a randomly chosen Success trial, how
often does the Failure trial actually have the lower CAR?** 50% would mean
no separation at all (coin flip); 100% would mean perfect separation.""")

code("""p3 = clean[clean['phase_clean']=='Phase 3']
f_ = p3[p3['category_clean']=='Failure']['car'].values
s_ = p3[p3['category_clean']=='Success']['car'].values
count = sum(1 for f in f_ for s in s_ if f < s)
total = len(f_) * len(s_)
print(f"Phase 3: of {total} possible (Failure, Success) pairs, "
      f"Failure CAR < Success CAR in {count} ({count/total*100:.0f}%)")
""")

md("### 8c. The asymmetry: which side is actually driving the Phase 3 result?")

code("""p3 = clean[clean['phase_clean']=='Phase 3']
fail = p3[p3['category_clean']=='Failure']['car']
succ = p3[p3['category_clean']=='Success']['car']

wf, pf = stats.wilcoxon(fail)
ws, ps = stats.wilcoxon(succ)
print(f"Phase 3 Failure vs zero (one-sample): n={len(fail)}, median={fail.median()*100:.1f}%, p={pf:.4f}")
print(f"Phase 3 Success vs zero (one-sample): n={len(succ)}, median={succ.median()*100:.1f}%, p={ps:.4f}")
""")

md("""**Only Failure is significant on its own.** Success is statistically
indistinguishable from zero. This means the finding is not symmetric --
it's not "successes react positively and failures react negatively." It's
**Phase 3 successes are unremarkable (the market shrugs -- largely already
priced in, since a Phase 3 asset has already cleared Phase 1/2), while
Phase 3 failures produce a real, detectable negative reaction (the
asymmetric, surprising outcome).** The two-sample test's significance is
being driven almost entirely by the Failure side, not by both sides moving
apart symmetrically.""")

md("""### 8d. Caveat: multiple comparisons across the whole session

Over the course of the 2026-07-14 audit, this same Phase 3 comparison was
recomputed under many different corrections and specifications: p=0.0029
(pre-fix, buggy) → 0.062 (CAR window fix) → 0.047 → 0.011 → 0.036 → 0.0113
(current) as EDGAR-matching and label corrections were found and applied,
plus a separate window-width sensitivity sweep (T-1..T+1 through T-5..T+5)
that on its own ranged p=0.05-0.15. That's meaningful researcher-degrees-
of-freedom before landing on any single number. A simple Bonferroni
correction across even 5-6 of these specifications (0.011 x 6 ≈ 0.07)
does not survive. **Treat the specific p-value as fragile; treat the
consistent direction and the Failure-vs-zero asymmetry (§8b) as the more
defensible claims.**""")

# ---------------------------------------------------------------------------
md("""## 9. Pooled across all 3 phases""")

code("""succ = clean[clean['category_clean'] == 'Success']['car']
fail = clean[clean['category_clean'] == 'Failure']['car']
biz = clean[clean['category_clean'] == 'Business Termination']['car']

print(f"Success:  n={len(succ)}, mean={succ.mean()*100:.1f}%, median={succ.median()*100:.1f}%")
print(f"Failure:  n={len(fail)}, mean={fail.mean()*100:.1f}%, median={fail.median()*100:.1f}%")
print(f"Business: n={len(biz)}, mean={biz.mean()*100:.1f}%, median={biz.median()*100:.1f}%")
print()

u, p = stats.mannwhitneyu(succ, fail, alternative='two-sided')
print(f"Success vs Failure (pooled):       p = {p:.5f}")
u, p = stats.mannwhitneyu(succ, biz, alternative='two-sided')
print(f"Success vs Business Term (pooled): p = {p:.5f}")
u, p = stats.mannwhitneyu(fail, biz, alternative='two-sided')
print(f"Failure vs Business Term (pooled): p = {p:.5f}")

h, p = stats.kruskal(succ, fail, biz)
print(f"\\nKruskal-Wallis (all 3 groups at once): H={h:.2f}, p={p:.5f}")
""")

md("""Pooling across phases dilutes the Phase 3-specific effect rather than
strengthening it -- Phase 1/2 data (where success and failure aren't
distinguishable, see §8a) waters down the one place the effect is
detectable. Phase-level analysis is the more honest read than the pooled
one.""")

# ---------------------------------------------------------------------------
md("""## 10. EDGAR trial-to-filing matching: found to be far less reliable than assumed

This is the largest single finding of the 2026-07-14 session and the
dataset's core open problem.

### What was wrong

The original matching approach checked whether a trial's drug name
appeared near the right date in an SEC filing -- with no check that the
filing actually discussed *that specific trial's result*, as opposed to a
different trial for the same drug, or a generic multi-program pipeline
update. Manual spot-checks this session found:
- A **random** sample of 15 previously-"passed" trials: only 2 held up
  (13%) -- the rest were generic mentions, wrong-drug matches, or
  same-drug-different-trial matches (e.g. NCT02725593, an AstraZeneca
  pediatric dapagliflozin trial, was "verified" by a filing about DAPA-HF,
  an unrelated adult heart-failure trial of the same drug).
- An **outlier-CAR-biased** sample (extreme price moves, hypothesized to
  correlate with bad matches since a wrong match picks up whatever *other*
  major news was in that filing): 8 of 12 confirmed wrong.
- Two duplicate-(ticker, filing-date) trials had **word-for-word identical**
  `verified_context` text to other trials discussing entirely different
  studies -- direct proof the extraction grabbed one arbitrary window of a
  multi-program filing and reused it regardless of relevance.

### The rebuild

A new two-stage pipeline was built and partially validated:
1. **Discovery**: query SEC's free full-text search API (`efts.sec.gov`)
   using the trial's ClinicalTrials.gov acronym when available, else its
   specific development code (e.g. `SPR720`, not the generic drug name,
   which is reused across a company's whole pipeline) -- restricted to the
   company's own CIK, searching **both** `8-K` and `6-K` forms (foreign
   private issuers file 6-K, never 8-K -- missing this was a second real
   bug, inflating "no disclosure found" counts from 13 to 83 before it was
   caught and fixed).
2. **Scoring**: fetch each candidate document and score it by whether real
   result-disclosure language ("met its primary endpoint," "topline
   results," "discontinued") appears within 400 characters of where the
   search term actually occurs -- not just whether the term is present
   anywhere in the document.

Validated on both ends: 6/6 zero-score spot-checks were confirmed generic;
most high-score (3-4) spot-checks were genuine dedicated disclosures. One
important residual failure mode even at high scores: a genuine disclosure
can still be for the *wrong specific trial* of the same drug (e.g.
TNX-102 SL's PREVAIL/Long-COVID trial surfacing when the trial in question
was actually a PTSD study) -- the scorer ranks candidates, it doesn't
replace reading the top one.

### Current state

249 of 260 trials have at least one term-confirmed-in-text candidate.""")

code("""try:
    scored = pd.read_csv('../data/interim/22_edgar_best_candidate_per_trial.csv')
    print(scored['score'].value_counts().sort_index(ascending=False))
except FileNotFoundError:
    print("(run scripts/22_edgar_rebuild_search_and_score.py to regenerate this file)")
""")

md("""The 75 zero-score trials are folded into `needs_reverification`
(confirmed generic on spot-check). **172 trials at scores 1-2 remain
unverified — this is the actual remaining work**, not a small tail.
Recommended approach: work top-down by score, not the full 172 at once —
higher scores are cheaper to confirm (usually "is this the right specific
trial," not "is this a real disclosure at all") and move `trustworthy` n
back up faster.""")

# ---------------------------------------------------------------------------
md("""## 11. Independent baseline: does the EDGAR-verification work actually matter?

Built to test this directly, and to test the labels/dates independent of
the whole EDGAR-matching apparatus. Two mistakes were made building it and
both are recorded here since they're easy to repeat:

1. **First attempt was silently EDGAR-selection-biased.** It only priced
   trials already present in the 260-trial `combined_phase_outcome_analysis.csv`
   — which itself only contains trials that survived the *old* EDGAR
   matching. Changing the pricing date doesn't remove that bias if the
   sample itself was pre-filtered by the thing being tested against.
2. **The PubChem pool file was used unfiltered** — `04_pubchem_verified.csv`
   is a candidate pool that was *checked* against PubChem (1839 rows), not
   a pre-filtered result; only 628 rows actually pass
   (`pubchem_verified_small_molecule_or_peptide == True`).

### Correct version

Starts from the 628-row correctly-filtered pool, independent of any EDGAR
search, priced off `results_first_posted_date` (a genuine, discrete,
publicly visible ClinicalTrials.gov event some specialized investors do
monitor directly — though not necessarily the same date as any company
press release). 361 of 362 eligible trials priced successfully.""")

code("""try:
    baseline = pd.read_csv('../data/processed/baseline_full_pool_model_refined.csv')
    rows = []
    for phase in sorted(baseline['phase_clean'].unique()):
        for cat in ['Success','Failure','Business Termination']:
            s = baseline[(baseline['phase_clean']==phase)&(baseline['category_refined']==cat)]
            if len(s)==0: continue
            rows.append({"Phase": phase, "Outcome": cat, "n": len(s),
                         "Median CAR": f"{s['baseline_car'].median()*100:.1f}%",
                         "% Positive": f"{(s['baseline_car']>0).mean()*100:.0f}%"})
    print(pd.DataFrame(rows).to_string(index=False))
except FileNotFoundError:
    print("(run scripts/24_baseline_full_pool.py to regenerate this file)")
""")

md("""### Business Termination needed the same why_stopped scrutiny the
original 38-trial sample got, and hadn't received it

Reading all 81 priced Business Termination trials' `why_stopped` text
(same method as §5): 61 genuine business/strategic, 9 enrollment/
feasibility failures (operational, not strategic), 6 efficacy or
tolerability failures mislabeled as terminations (moved to Failure), 2
possibly-positive early stops (met an efficacy goal early -- excluded, not
a failure), 1 regulatory clinical-hold case, 2 ambiguous. Pure business
terminations skew clearly positive (Phase 3: 75% positive, +1.7% median) —
a sensible, distinct signal (the market reading "portfolio cleanup, no bad
data" as mildly good news), not noise, worth its own category rather than
merging into Failure or excluding.

### The result

No Failure-vs-Success comparison in the baseline reaches significance at
any phase (Phase 3, after the label fixes above: n=12 vs 139, median CAR
-1.7% vs 0.0%, p=0.28) — despite roughly 14x more Phase 3 data than the
EDGAR-verified subset. The EDGAR-verified subset (§8) finds p=0.011 on the
same underlying method, differing only in date precision and match
verification.

**Conclusion: the EDGAR-verification work is not overkill.** Fixing the
mislabeled Business Terminations moved the baseline's signal in the
directionally correct direction (from a meaningless +0.1% to -1.7%),
confirming labels matter — but a correctly-scoped, much larger,
selection-bias-free baseline still fails to reach significance without
also fixing the date/verification problem. Both are real, independent
sources of signal loss, not the same bug wearing two hats.""")

# ---------------------------------------------------------------------------
md("""## 12. Known limitations / open questions

- **172 trials still need individual EDGAR-match verification** (§10) —
  the actual bottleneck to trusting any headline number at full sample
  size.
- **NCT03672175/SAGE-217 fix applied 2026-07-14**; the 5 additional
  mislabeled efficacy failures found in §11 are in the wider 628-pool but
  not the 260-trial priced dataset, so don't change the numbers here --
  worth checking whether any could be recovered into the priced dataset.
- **Sample size.** Several phase x outcome cells have n<15. Most pairwise
  comparisons are underpowered; only Phase 3 currently shows a detectable
  effect, and even that is asymmetric (§8b) and sensitive to which
  correction round you read it from (§8c).
- **Estimation-window instability** — the market-model approach could be
  made more robust (R²-based or alpha-standard-error-based flagging
  instead of a raw cumulative-% threshold) rather than just excluding.
  Proposed, not implemented.
- **`logistics_termination` and `ambiguous_termination` pools have not
  received the same `why_stopped` scrutiny** that `business_termination`
  got in §5/§11 — worth doing before sourcing more negatives from them.
- **The independent baseline (§11) is a reference/comparison tool, not a
  source of headline numbers** — it's useful for testing whether a fix
  matters, not for reporting a result on its own.
- **Not yet scaled past the Day-1 pilot.** Current trustworthy n=83 is
  enough to suggest a plausible, asymmetric Phase 3 effect, not enough to
  confirm it or support the board-level "average fluctuation magnitude"
  question, which needs a bootstrap CI and more verified data.
""")

nb["cells"] = cells
with open("notebooks/methodology_and_analysis.ipynb", "w") as f:
    nbf.write(nb, f)
print(f"Notebook built with {len(cells)} cells")
