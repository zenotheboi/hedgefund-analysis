# Project Status & Handoff Notes

Last updated: 2026-07-15. Read this first in any new session before
touching code. This replaces the previous version of this file, which had
grown into a round-by-round log of a single very long audit session —
that detail still exists in the session transcript and the `data/interim/`
working files if you need it, but this file states where things landed,
not how they got there.

## 2026-07-15 pivot: BioPharmCatalyst data source (active track)

The CTOD/EDGAR pipeline below (everything from "Where things stand right
now" on) was the Day-1 prototype. On 2026-07-15 the user asked to switch to
a second, independent data source to sidestep the EDGAR-matching problem
entirely: **BioPharmCatalyst**, scraped by a third party
(`github.com/Tejas1415/Web-Scrape-Stock-Ticker-and-Company-Name-Datasets`,
`BioPharmCatalyst.csv`). This is a *new, parallel* analysis, not a
replacement of the CTOD work yet — both should be kept.

**Why this source is actually a fix, not just a different dataset**: its
`Catalyst Date` is an analyst-curated market-disclosure date, so it removes
the EDGAR trial-to-filing matching problem (the CTOD pipeline's core open
issue, 172 trials still unverified) at the source — no filing search or
scoring needed.

**Coverage caveat, important**: the file only covers **2009-07-05 to
2020-01-14** — NOT the trailing 10 years the user originally asked for. It's
a static scrape, stale by ~6 years. Flag this any time these numbers are
used or presented.

**Pipeline built this session** (`scripts/25`-`28_biopharmcatalyst_*.py`,
reuses `src/hedgefund/pubchem.py` and `src/hedgefund/prices.py` unchanged):
1. `25_biopharmcatalyst_clean.py` — strip whitespace, drop 61 rows where the
   status column contained leaked SVG markup (scraper bug) and 17 exact
   duplicates. 2258 → 2180 rows.
2. `26_biopharmcatalyst_filter_and_pubchem.py` +
   `26b_biopharmcatalyst_pubchem_retry.py` — filter to `Approved`/`CRL` only
   (per user's request, ignoring all other stage values for this first
   pass), then PubChem-verify small-molecule/peptide status (MW ≤ 8000 Da,
   same rule as CTOD). Raw literal drug-name lookup only found 85/462
   unique names; a name-cleaning retry (strip parentheticals, dosage-form
   words, trial-name suffixes, split combo drugs into components) recovered
   182 more → 267/462 (58%) unique small-molecule/peptide names, 363 rows.
3. `27_biopharmcatalyst_merge_pubchem.py` — merges original + retry PubChem
   results into the final filtered set.
4. `28_biopharmcatalyst_pull_prices.py` — prices each event with the same
   estimator as CTOD (`fit_market_model` + `short_window_car`, T-2..T+2 vs
   XBI), but pulls each ticker's full 2008-2020 history once and slices
   per-event windows in memory instead of re-downloading per event (363
   events, 130 tickers). **249/363 (68.6%) priced successfully**; the other
   114 fail because 109 tickers have zero Yahoo Finance history at all
   (delisted/acquired biotechs Yahoo has purged — e.g. ARNA, CLVS, SGEN,
   MYL, AGN, real M&A exits, not a bug) and 5 lack enough pre-event history.

**Result: Approved vs. CRL, n=249, all phases combined** — median CAR
Approved +0.4% (n=209) vs. CRL -11.7% (n=40), Mann-Whitney p=5.4e-8, Welch
t-test p=6.6e-6. Same asymmetry as the CTOD Phase-3 finding (approval is
priced-in/unsurprising, rejection is the real shock) but on a much larger,
directly-sourced sample with no EDGAR dependency.

**Published artifact**: HTML page with CAR strip plot, CAR-vs-time scatter,
filterable 249-row table, and the phase-separation proposal below — ask the
user for the current link if continuing this thread (redeploys to the same
URL via the same file path in `/private/tmp/.../scratchpad/biopharm_car_analysis.html`
if resuming in the same session; otherwise regenerate from
`data/processed/biopharmcatalyst_small_molecule_car.csv`).

**Open problem, same shape as CTOD's EDGAR gap: phase separation.** The raw
file's `Approved or CRL` column is really a 13-value catalyst-type field
(Phase 1 through Phase 3, NDA/BLA Filing, PDUFA, Approved, CRL all mixed
together) — there's no explicit "which phase was this approval decision
based on" link. Approved/CRL rows are already a reasonable proxy for
"Phase 3 pivotal outcome" (FDA approvals are made almost entirely on Phase
3 data), which is why this first pass treats them that way. **Recommended
next step**: link each Approved/CRL row back to the most recent prior
same-ticker/same-drug Phase 1/2/3 row in this same CSV (reusing the
name-cleaning logic from step 2) to get an explicit phase per event, with
openFDA/Drugs@FDA as a spot-check on drug identity (not phase — it doesn't
carry trial phase) and ClinicalTrials.gov as a fallback for unlinked rows.
Beyond that, the 1,547 Phase 1/1b/2/2a/2b/2-3/3 rows have no
success/failure label at all — only free-text `Catalyst Description` — a
keyword classifier on that text (same idea as the EDGAR filing scorer in
the CTOD pipeline) would be needed to price those as events too.

**Live-scrape attempt, 2026-07-15 — blocked, don't retry without a paid login.**
User asked to adapt the original repo's scraper (`BiopharmCatalyst_Download.py`,
which works by manually pasting view-source HTML into a text file) to hit
the live site directly with a date range and real phase data. Investigated
via browser network inspection: the site migrated to a Vue SPA since 2020 —
the static page no longer contains table rows at all (only a ticker
autocomplete list), and the real data now loads from
`GET /api/historical-catalysts-calendar?page=N`. That endpoint returns
HTTP 200 to anonymous requests but with **placeholder content** on every
row (`drug_name: "PLCB"`, `indication: "Placebo"`, `note: "Lorem ipsum..."`)
— real ticker/price/sparkline, fake everything else. This is a paywall,
not a bug; did not attempt to log in or bypass it. **One genuinely useful
thing did come out of this**: `GET /api/stages` is public (just taxonomy
metadata, not gated event data) and returns BioPharmCatalyst's own official
phase hierarchy with a `simplified_stage` field (phase0=Preclinical/IND-
Enabling, phase1=Phase1a/1/1b/1-2, phase2=Phase2a/2/2b, phase3=Phase2-3/3,
phase4=NDA/sNDA/BLA Filing, phase5=PDUFA, phase6=Approved/CRL) — confirms
the phase-separation proposal above is right that Approved/CRL sit one
step past Phase 3 as the terminal regulatory-decision bucket, from an
authoritative source rather than inference.

**Cross-check against free/official sources instead (2026-07-15), in place
of live BioPharmCatalyst access** — `scripts/29_crosscheck_openfda_approvals.py`,
`scripts/30_crosscheck_edgar_crls.py`:
- **Approved events**: openFDA Drugs@FDA (free, public, no login) — for each
  of 286 Approved rows, searched by cleaned drug name and compared the
  closest FDA "AP" (approved) submission date to BioPharmCatalyst's Catalyst
  Date. **215/286 (75%) confirmed within 45 days.** 18 large-delta mismatches
  (years off) are consistent with generic-name search ambiguity (multiple
  manufacturers sharing an ingredient name) rather than BPC date errors —
  worth tightening the query (restrict to `submission_type=ORIG`, or search
  by NDA/BLA application number when known) if this needs to be load-bearing
  later. 53 not found in openFDA at all (mostly combo-drug/company-code
  names, same pattern as the PubChem matching gaps).
- **CRL events**: SEC EDGAR full-text search (reuses `src/hedgefund/sec.py`,
  the CTOD/EDGAR track's own module) for 8-K/6-K filings mentioning
  "Complete Response Letter" within +-30 days of the Catalyst Date, keyed by
  ticker->CIK from `data/raw/sec/company_tickers.json`. **26/40 tickers with
  a matched CIK confirmed (65%)**; the other 37 of 77 CRL rows have no CIK
  match at all because that ticker JSON only lists *currently* SEC-registered
  companies — the same delisted/acquired-ticker gap seen in the yfinance
  pricing step (ARNA, CLVS, SGEN, SPPI, etc.). Fixable with an EDGAR
  company-name search fallback if pursued further; not done this session.
- **Net takeaway**: BioPharmCatalyst's Approved/CRL dates hold up well
  against independent, free, official sources on the events that could be
  matched — this is real support for trusting the static CSV's core numbers,
  not just an assumption. Output files: `data/interim/29_openfda_crosscheck.csv`,
  `data/interim/30_edgar_crl_crosscheck.csv`.

**Key files**: `data/raw/biopharmcatalyst/BioPharmCatalyst.csv` (source),
`data/interim/25_biopharmcatalyst_clean.csv`,
`data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv`,
`data/processed/biopharmcatalyst_small_molecule_car.csv` (final priced
dataset, 249 rows), `data/processed/biopharmcatalyst_event_windows.json`
(full per-day price/return series per event), `data/interim/28_pricing_errors.csv`
(the 114 unpriced events + why).

---

## CTOD/EDGAR pipeline (prior track, still valid, see above for what's new)

## What this project is

Day-1 feasibility prototype for a hedge fund strategy based on predicting
clinical trial outcomes and trading the stock reaction. Scope: small
molecule/peptide drugs only, Phase 1-3, public companies. Original brief:
`/Users/gigi/Downloads/methodology.md` (superseded by this doc).

## Where things stand right now

**260 trials, 83 currently trustworthy.** A trial counts as trustworthy
only if all three quality flags are clean:
- `unstable_estimation` (25 trials) — the pre-event estimation window had
  an outsized (>50%) unrelated price move, making the fitted market-model
  baseline unreliable.
- `needs_reverification` (155 trials) — the trial-to-SEC-filing match is
  either confirmed wrong, confirmed generic (mentions the drug but
  discloses no specific result), or was never individually verified at
  all. This is the large majority of exclusions and the dataset's core
  open problem — see below.
- `sign_disagreement` (23 trials) — the market-adjusted return and the raw
  stock return disagree on direction even after the estimator fix below.

**Current headline finding:** Phase 3 Failure (n=10, median CAR -6.0%) vs.
Phase 3 Success (n=37, median CAR +0.3%), two-sample p=0.0113. Treat this
as a plausible, not confirmed, lead — the p-value moved six times over the
course of today's audit as different data problems were found and fixed
(0.0029 → 0.062 → 0.047 → 0.011 → 0.036 → 0.0113), which means the sample
is still too small and 172 trials are still unverified (see below), so the
precise p-value isn't trustworthy on its own. What has held up under every
version, and is the more precise and defensible claim: **Phase 3 failures
produce a real, detectable negative reaction (p=0.014 one-sample vs. zero);
Phase 3 successes are statistically indistinguishable from zero (p=0.53) —
the market treats a Phase 3 success as expected/unsurprising and a Phase 3
failure as the genuine information event.** That asymmetry, not the
two-sample p-value, is the finding worth remembering.

## Two real bugs fixed today (2026-07-14)

1. **CAR estimator bug.** The abnormal-return calculation summed a fitted
   daily `alpha` over a 36-trading-day window (T-30..T+5). That let
   estimation noise/drift compound over the whole window and often
   swamped the real announcement reaction. Fixed with a short T-2..T+2
   window (`short_window_car()` in `src/hedgefund/prices.py`), which is
   now the primary `car` column (`car_long_window` keeps the old value for
   reference). This is the more methodologically standard choice for
   event studies and is not up for debate — don't revert it.
2. **EDGAR trial-to-filing matching was much less reliable than assumed.**
   The original pipeline matched a trial to an SEC filing by checking
   whether the drug's name appeared near the right date — no check that
   the filing actually discussed *that specific trial's result*, as
   opposed to a different trial for the same drug, or a generic
   multi-program pipeline update. Manual spot-checks this session found
   error rates from ~50% up to ~90% depending on the sample. Full
   findings history is in the transcript; the net effect is captured in
   the `needs_reverification`/`audit_status` columns described below.

## The core open problem: EDGAR matching

A better matching approach was built and partially validated this
session, but is NOT finished:

- **Method**: search SEC's full-text search API (`efts.sec.gov`, free, no
  key) using the trial's ClinicalTrials.gov acronym (when available) or
  its specific development code (not generic drug name — codes are far
  more unique), restricted to the company's own CIK, searching **both**
  `8-K` and `6-K` forms (foreign private issuers like Novo Nordisk,
  Novartis, AstraZeneca, Sanofi file 6-K, not 8-K — missing this was a
  real bug that inflated the "no disclosure found" count early on).
  Window: [primary_completion_date - 180d, +450d] — completion date is a
  *search anchor*, never a pricing anchor (nothing is disclosed to the
  market on the day a trial finishes enrolling; see the transcript for
  the fuller discussion of why `results_first_posted_date` is also not a
  reliable pricing anchor — it's an FDAAA compliance deadline, not a
  market-disclosure date).
- **Scoring**: each candidate document is scored by whether real
  result-language ("met its primary endpoint," "topline results,"
  "discontinued," etc.) appears within 400 characters of where the
  search term actually appears in the text — not just whether the term
  is present. Validated on both ends: 6/6 zero-score spot-checks were
  confirmed generic, most high-score (3-4) spot-checks were genuine
  dedicated disclosures. One important residual failure mode even at
  high scores: a genuine disclosure can still be for the *wrong specific
  trial* of the same drug (e.g. TNX-102 SL's PREVAIL/Long-COVID trial
  surfacing when the trial in question was actually a PTSD study) — the
  scorer ranks candidates, it doesn't replace reading the top one.
- **State**: 249 of 260 trials have at least one term-confirmed-in-text
  candidate. Score distribution: 2 score 4, 17 score 3, 52 score 2, 103
  score 1, 75 score 0. The 75 zero-score trials are now folded into
  `needs_reverification` (confirmed generic on spot-check). **The 172
  trials with score 1-2 are unverified** — this is the actual remaining
  work, not a small tail. Working files: `data/interim/22_edgar_candidates_scored.csv`
  (every candidate, all scores) and `22_edgar_best_candidate_per_trial.csv`
  (best candidate per trial).

**Recommended next step, when picked back up:** work top-down by score
(3s next, then 2s, then 1s) rather than trying to clear the whole 172 at
once — the higher scores are cheaper to confirm (usually just checking
"is this the right specific trial," not "is this a real disclosure at
all") and will do the most to move `trustworthy` n back up.

## Baseline comparison: is the EDGAR-verification work worth its cost?

**`scripts/23_baseline_ctgov_date_model.py` / `baseline_ctgov_date_model.csv`
are DEPRECATED — do not use.** That first attempt only priced trials
already present in the 260-trial `combined_phase_outcome_analysis.csv`,
which itself only contains trials that survived the old EDGAR-matching
pipeline. So despite changing the pricing *date* to remove EDGAR
dependency, it silently kept the EDGAR-selected *sample* — not actually
independent of the thing it was trying to test against. Caught by the
user, not found proactively.

**The real baseline: `scripts/24_baseline_full_pool.py` /
`data/processed/baseline_full_pool_model.csv`.** Starts from
`04_pubchem_verified.csv` filtered correctly this time to
`pubchem_verified_small_molecule_or_peptide == True` (628 of 1839 rows —
the file is a candidate pool that was *checked* against PubChem, not a
pre-filtered result; using it unfiltered was a second bug, also caught by
the user, not found proactively). Of those 628, 362 have a
`results_first_posted_date` and a clear (non-ambiguous) outcome label.
This sample is genuinely prior to any EDGAR search — it's not filtered by
whether the old matching pipeline happened to find a filing for a trial,
only by chemistry and data availability.

Result, all phases (n=361 priced): no Failure-vs-Success comparison
reaches significance anywhere — Phase 3 n=10 vs 139, median CAR 0.1% vs
0.0%, p=0.61; Phase 2 n=4 vs 96, p=0.49. Compare to the EDGAR-verified
subset (n=83): Phase 3 n=10 vs 37, median CAR -6.0% vs +0.3%, **p=0.011**
— the only significant comparison in either table, on ~14x less Phase 3
data than the properly-scoped baseline. **Conclusion, now on a properly
independent sample: the EDGAR-verification work is not overkill.** A
correctly-scoped, much larger, selection-bias-free baseline still fails
to find the effect the verified subset finds — this isn't an artifact of
which trials got matched, the date/verification itself is where the
signal lives.

**Business Termination in the baseline needed the same why_stopped split
as the original 260-trial dataset got, and hadn't received it.** Read all
81 priced Business Termination trials' `why_stopped` text (same method as
the original 38 -- see below). Found: 61 genuine business/strategic, 9
enrollment/feasibility failures (operational, not strategic), 6 efficacy
or tolerability failures that were mislabeled as terminations (should be
Failure -- includes the already-fixed CORT case plus 5 more found here:
NCT03762265/SNY, NCT03459443/LXRX, NCT04492722/AZN, NCT04323124/PFE,
NCT04139317/NVS), 2 possibly-positive early stops (met an efficacy goal
early, not a failure at all), 1 regulatory clinical-hold case, 2 ambiguous
(reference an external analysis not explained in the text itself).
Refined file: `data/processed/baseline_full_pool_model_refined.csv`
(`category_refined` column). After moving the 6 mislabeled efficacy
failures into Failure, Phase 3 Failure grows to n=12, median CAR moves
from a meaningless +0.1% to **-1.7%** -- directionally consistent with
the EDGAR-verified subset's -5.6%, still not significant (p=0.28), but
real evidence that mislabeling was degrading the baseline's signal
independent of the date/verification problem -- both were real, separate
issues, not the same bug wearing two hats. Pure business terminations
(n=61 across phases) skew clearly positive (Phase 3: 75% positive, +1.7%
median) -- a sensible, distinct signal, not noise, worth treating as its
own category rather than merging into Failure or excluding.

**This same why_stopped categorization has NOT yet been applied to
`04_pubchem_verified.csv`'s other termination buckets** (`ambiguous_termination`,
`logistics_termination` -- see the negative-case-sourcing item below) --
worth doing before trusting those pools for anything either.

## Other confirmed fixes worth knowing about

- **NCT04329949 (CORT)** was mislabeled "Business Termination" — its own
  `why_stopped` text says the response rate missed a predefined threshold,
  an efficacy stop. Reclassified to Failure.
- **NCT03672175 (BIIB/SAGE-217)** was labeled "Success" but its actual
  disclosed result (found under Sage Therapeutics' CIK, not Biogen's —
  they co-developed the drug) explicitly says the MOUNTAIN study "did not
  meet primary endpoint." **This has NOT yet been applied to the
  dataset** — flag it if you're continuing this work.
- Of the 38 "Business Termination" trials, `why_stopped` text was read for
  all of them: ~34 are genuine business/strategic decisions, 2 are
  recruitment/feasibility failures (not really business decisions), 1 is
  the CORT mislabel above (fixed), 1 (NCT03829657/TBPH) references
  "analysis results in TD-9855-0169" and hasn't been checked further —
  may also be an efficacy-informed decision, not purely strategic.

## Known remaining work, roughly in priority order

1. Verify the 172 score-1/2 EDGAR candidates (see above) — the actual
   bottleneck to trusting any headline number.
2. Apply the SAGE-217/MOUNTAIN fix (Success → Failure).
3. Check NCT03829657/TBPH's referenced analysis (TD-9855-0169).
4. The three-tier `audit_status` column (`confirmed_wrong_match` /
   `unconfirmed_recovery_candidate`) from earlier in the session is now
   partially superseded by the score-based approach — worth reconciling
   the two rather than maintaining both.
5. Negative-case count is still short of a ~70-100 target for real
   statistical power even once matching is trustworthy — see the
   unexploited `logistics_termination` (135) and `ambiguous_termination`
   (348) pools in `data/interim/04_pubchem_verified.csv`.
6. Notebook (`notebooks/methodology_and_analysis.ipynb`) was regenerated
   2026-07-14 and is current as of trustworthy n=83 / Phase 3 p=0.0113 —
   re-run `build_notebook.py` + re-execute again once task #10 (the 172
   unverified EDGAR candidates) moves the numbers further. The published
   chart artifact is still stale — not updated today.
7. Remaining steps from the original brief (market-implied probability /
   archetype library, then the three-tier backtest) are unstarted and
   should wait until the dataset itself is trustworthy — no point
   backtesting on data still mid-audit.

## Key files

- `data/processed/combined_phase_outcome_analysis.csv` — the analysis
  dataset. `car` = short-window (T-2..T+2) abnormal return, the primary
  metric. `trustworthy` = all three quality flags clean.
- `data/processed/full_pool_event_windows_all260.json` — full daily
  price/benchmark data for all 260 trials; use with `short_window_car()`
  in `src/hedgefund/prices.py` to recompute CAR at any window width
  without re-hitting yfinance.
- `data/interim/22_edgar_candidates_scored.csv`,
  `22_edgar_best_candidate_per_trial.csv` — the EDGAR rematch working
  files described above; start here, don't rebuild from scratch.
- `data/interim/20_ctgov_acronym_dates_all260.csv` — acronym +
  primary_completion_date + results_first_posted_date for all 260 trials
  from the ClinicalTrials.gov API.
- `scripts/22_edgar_rebuild_search_and_score.py` — the current, working
  EDGAR search+score pipeline. Earlier numbered scripts in the 15-21
  range are intermediate/superseded versions kept for auditability, not
  meant to be re-run.
- `data/processed/baseline_full_pool_model.csv`,
  `scripts/24_baseline_full_pool.py` — the correct, EDGAR-independent
  baseline (see comparison section above). n=361, priced off
  `results_first_posted_date` alone, sampled from the PubChem-verified
  pool before any EDGAR search. Useful as a reference/comparison point,
  not as a source of headline numbers — it doesn't find the effect.
  `scripts/23_baseline_ctgov_date_model.py` and its output are
  **deprecated** (sample was silently EDGAR-selection-biased) — don't use.
- `src/hedgefund/` — reusable modules (sec.py, ctgov.py, pubchem.py,
  outcome_category.py, edgar_dates.py, prices.py, news_fallback.py).
- Chart: published artifact (ask the user for the link) — stale, not
  updated with today's work. Separate from the manager one-pager below.
- Manager one-pager: a second, separate published Artifact (custom
  Fraunces/IBM Plex type system, diverging blue/amber CAR chart) that
  summarizes the Phase 3 finding for non-technical presentation. Not the
  same thing as the chart artifact above — ask the user for the link if
  continuing this thread.

## Git / GitHub state (new as of 2026-07-14 — this project was never
## committed before this session)

`/Users/gigi/hedgefund-analysis` is a fork (`zenotheboi/hedgefund-analysis`)
of the original author's repo (`SteliosKyriacou/hedgefund-analysis`). First
commit (`3030f5a`, 42 files) pushed this session — `.gitignore` already
correctly excludes `venv/`, `data/raw/`, `data/interim/`, so only
`data/processed/` and code are tracked; the many `data/interim/*` working
files referenced throughout this doc exist locally but are NOT in git.
Workflow: PR within the fork (`gigi`→`main`) merged by the user, then a PR
opened directly to the upstream author
(`SteliosKyriacou/hedgefund-analysis` PR #1, `zenotheboi:main`→`main`),
titled/framed as "Prototype 1" since the user plans to change the
underlying dataset next iteration — carry that same "this will change"
caveat into any future upstream-facing communication, don't present
current numbers as final there.
