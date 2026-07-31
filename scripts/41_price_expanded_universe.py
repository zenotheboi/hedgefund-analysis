"""Phase 0b: price the FULL backtest universe uniformly -- Approved, CRL, and
the parsed Phase 2/3 met/miss events -- with an extended event window
(T-25..T+65) so the 63-day lending hold and the pre-event entry both fit.
Reuses the trimmed market-model fit (script 36) and the small-molecule
PubChem filter (src/hedgefund/pubchem.py).

Outputs:
- data/processed/backtest_events.csv : one row/event (category, anchor, CAR,
  entry/exit returns for each leg, market-cap/borrow tier)
- data/processed/backtest_windows.json : per-event daily window T-25..T+65
  (offset, stock/bench close+return) for the path-aware engine.
"""
import sys, os, time, json
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, "src")
from hedgefund.pubchem import lookup_compound

PHASE_IN = "data/interim/40_phase_outcomes.csv"
APPRCRL_IN = "data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv"
PUBCHEM_CACHE = "data/interim/26_pubchem_cache.csv"
OUT_CSV = "data/processed/backtest_events.csv"
OUT_JSON = "data/processed/backtest_windows.json"

EVENT_PRE, EVENT_POST, EST_WINDOW, TRIM_SIGMA = 25, 65, 120, 3.0
YEAR_MIN, YEAR_MAX = 2014, 2020

BIG_PHARMA = {'NVO','AZN','ABBV','PFE','AMGN','BMY','VRTX','GILD','JNJ','MRK',
              'LLY','NVS','SNY','BIIB','RHHBY','GSK','TAK','GMAB','MRNA','REGN',
              'ALXN','INCY','JAZZ','BMRN'}

# ---- assemble the event list (Phase 2/3 met/miss + Approved/CRL) ----
ph = pd.read_csv(PHASE_IN, parse_dates=["anchor_date"])
ph = ph[(ph.anchor_date.dt.year.between(YEAR_MIN, YEAR_MAX)) &
        ph.phase.isin(["Phase 2", "Phase 3"]) & ph.outcome.isin(["met", "miss"])]
ph = ph.rename(columns={"anchor_date": "date"})
ph["category"] = ph["phase"] + " " + ph["outcome"]
ph["success"] = ph.outcome == "met"

ac = pd.read_csv(APPRCRL_IN, parse_dates=["Catalyst Date"])
ac = ac[ac["Catalyst Date"].dt.year.between(YEAR_MIN, YEAR_MAX)].rename(
    columns={"Ticker": "ticker", "Drug Name": "drug_name", "Catalyst Date": "date",
             "Approved or CRL": "reg"})
ac["phase"] = "Regulatory"
ac["outcome"] = ac.reg.map({"Approved": "met", "CRL": "miss"})
ac["category"] = ac.reg
ac["success"] = ac.reg == "Approved"

events = pd.concat([ph[["ticker", "drug_name", "phase", "outcome", "category", "success", "date"]],
                    ac[["ticker", "drug_name", "phase", "outcome", "category", "success", "date"]]],
                   ignore_index=True)
print(f"raw events 2014-2020: {len(events)}  ({events.category.value_counts().to_dict()})")

# ---- PubChem small-molecule filter (reuse+extend cache) ----
cache = pd.read_csv(PUBCHEM_CACHE) if os.path.exists(PUBCHEM_CACHE) else pd.DataFrame(columns=["drug_name"])
cached = {r["drug_name"]: r for _, r in cache.iterrows()}
rows = list(cache.to_dict("records"))
todo = sorted(set(events.drug_name) - set(cached))
print(f"PubChem: {len(cached)} cached, {len(todo)} new lookups...")
for i, name in enumerate(todo):
    rows.append({"drug_name": name, **lookup_compound(name)})
    if (i + 1) % 50 == 0:
        print(f"  pubchem {i+1}/{len(todo)}")
cache = pd.DataFrame(rows).drop_duplicates("drug_name")
cache.to_csv(PUBCHEM_CACHE, index=False)
# LENIENT filter: drop only PubChem-CONFIRMED non-small-molecules (found in
# PubChem with MW above the small-mol/peptide cutoff = a biologic). Keep
# confirmed small-mols AND unresolved names -- an unindexed development code
# ("LY-xxxx") is almost always a small molecule, not a biologic, so requiring
# a PubChem hit would wrongly discard most Phase 2/3 events.
confirmed_biologic = set(cache[(cache.found == True) &
                               (cache.is_small_molecule_or_peptide == False)].drug_name)
n0 = len(events)
events = events[~events.drug_name.isin(confirmed_biologic)].copy()
print(f"after dropping confirmed biologics: {len(events)} events (removed {n0-len(events)})")

# ---- download prices once per ticker ----
tickers = sorted(events.ticker.unique())
def dl(t):
    for a in range(3):
        try:
            d = yf.download(t, start="2008-06-01", end="2020-12-31", auto_adjust=True, progress=False)
            if d.empty:
                return None
            c = d["Close"]
            return c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
        except Exception:
            time.sleep(1 + a)
    return None

print(f"downloading XBI + {len(tickers)} tickers...")
bench = dl("XBI")
close = {}
for i, t in enumerate(tickers):
    c = dl(t)
    if c is not None:
        close[t] = c
    if (i + 1) % 40 == 0:
        print(f"  {i+1}/{len(tickers)}")

def fit_trimmed(est):
    x, y = est["br"].values, est["sr"].values
    beta, alpha = np.polyfit(x, y, 1)
    resid = y - (alpha + beta * x)
    keep = np.abs(resid) <= TRIM_SIGMA * resid.std()
    if (~keep).sum() and keep.sum() > EST_WINDOW // 2:
        beta, alpha = np.polyfit(x[keep], y[keep], 1)
    return float(alpha), float(beta)

def cum_ret(series):  # simple cumulative return of a return series
    return float((1 + series).prod() - 1)

results, windows, skipped = [], {}, 0
for idx, r in events.reset_index(drop=True).iterrows():
    tk = r.ticker
    if tk not in close:
        skipped += 1; continue
    px = pd.concat([close[tk], bench], axis=1, join="inner").sort_index()
    px.columns = ["sc", "bc"]
    ret = px.pct_change(); ret.columns = ["sr", "br"]
    d = px.join(ret)
    pos = d.index.searchsorted(pd.Timestamp(r.date))
    lo = pos - (EVENT_PRE + EST_WINDOW)
    if lo < 1 or pos + EVENT_POST >= len(d):
        skipped += 1; continue
    seg = d.iloc[lo:pos + EVENT_POST + 1].copy()
    seg["off"] = np.arange(len(seg)) - (EVENT_PRE + EST_WINDOW)
    est = seg[seg.off < -EVENT_PRE].dropna(subset=["sr", "br"])
    if len(est) < EST_WINDOW // 2:
        skipped += 1; continue
    alpha, beta = fit_trimmed(est)
    ev = seg[seg.off >= -EVENT_PRE].copy()
    ev["ar"] = ev.sr - (alpha + beta * ev.br)

    def between(a, b, col):  # cumulative over [a,b] inclusive offsets
        w = ev[(ev.off >= a) & (ev.off <= b)]
        return cum_ret(w[col]) if len(w) else np.nan

    tier = "large" if tk in BIG_PHARMA else "small"
    results.append({
        "ticker": tk, "drug_name": r.drug_name, "phase": r.phase, "outcome": r.outcome,
        "category": r.category, "success": r.success, "date": str(pd.Timestamp(r.date).date()),
        "tier": tier, "alpha": alpha, "beta": beta,
        "car_short": between(-2, 2, "ar"),          # event reaction (abnormal)
        "ret_long_entry_exit": between(-20, 63, "sr"),   # long+lend leg raw return
        "ar_long_entry_exit": between(-20, 63, "ar"),    # market-adjusted
        "ret_short_entry_exit": between(-10, 5, "sr"),   # short leg raw return
        "ar_short_entry_exit": between(-10, 5, "ar"),
    })
    # daily window for the path-aware engine
    evo = ev.reset_index().rename(columns={ev.index.name or "index": "date"})
    key = f"{tk}_{pd.Timestamp(r.date).date()}_{idx}"
    windows[key] = [{"off": int(o), "sr": (None if pd.isna(s) else round(float(s), 6)),
                     "br": (None if pd.isna(b) else round(float(b), 6)),
                     "ar": (None if pd.isna(a) else round(float(a), 6))}
                    for o, s, b, a in zip(evo.off, evo.sr, evo.br, evo.ar)]

res = pd.DataFrame(results)
res.to_csv(OUT_CSV, index=False)
json.dump(windows, open(OUT_JSON, "w"))

print(f"\npriced {len(res)} / {len(events)} events (skipped {skipped} for no/short history)")
print("\nby category (median CAR_short, n):")
g = res.groupby("category")["car_short"].agg(["count", "median"])
g["median"] = (g["median"] * 100).round(2)
print(g.to_string())
print(f"\nwrote {OUT_CSV} + {OUT_JSON}")
