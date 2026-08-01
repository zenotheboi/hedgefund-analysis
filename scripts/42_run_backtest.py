"""Phase 2-4: event-driven portfolio backtest of the perfect-foresight biotech
catalyst strategy, $10M, 2014-2020, small-cap universe only.

Builds a daily equity curve (path-aware marks), computes metrics, and runs the
analyses that actually matter (per the strategy-analyst critique):
  - per-leg / per-category attribution
  - by-regime (sub-period) breakdown
  - borrow-rate x utilization sensitivity surface (drives the lending leg)
  - price-only vs +lending (isolates Stylianos's lending edge)
  - short via borrow vs via puts, and gross vs executability-gated
  - accuracy degradation 100/95/90/80% (the realistic haircut)

Outputs metrics JSON + PNGs for the report.
"""
import sys, json
from dataclasses import replace
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "src")
from hedgefund.backtest import Params, position_pnl

EVENTS = "data/processed/backtest_events.csv"
WINDOWS = "data/processed/backtest_windows.json"

ev = pd.read_csv(EVENTS, parse_dates=["date"])
windows = json.load(open(WINDOWS))
# window keys are "TICKER_YYYY-MM-DD_idx" (idx = script 41's internal row index,
# not preserved in the CSV). Match by (ticker, date), consuming keys in order
# so duplicate (ticker,date) rows align with the CSV's same source ordering.
from collections import defaultdict, deque
key_queue = defaultdict(deque)
for k in sorted(windows, key=lambda s: int(s.rsplit("_", 1)[1])):
    tk, rest = k.split("_", 1)
    dt = rest.rsplit("_", 1)[0]
    key_queue[(tk, dt)].append(k)
ev = ev.reset_index(drop=True)
keys = []
for _, r in ev.iterrows():
    q = key_queue[(r.ticker, str(r.date.date()))]
    keys.append(q.popleft() if q else None)
ev["key"] = keys
ev = ev[ev.key.notna()].copy()

# SMALL-CAP universe only (design decision: the tradeable signal lives here),
# restricted to 2016-2019 where the event sample is dense (2014-15 and 2020
# are too sparse to form a real portfolio -- see the by-year sample chart).
YEAR_MIN, YEAR_MAX = 2016, 2019
sc = ev[ev.tier == "small"].sort_values("date").reset_index(drop=True)
sc = sc[(sc.date.dt.year >= YEAR_MIN) & (sc.date.dt.year <= YEAR_MAX)].reset_index(drop=True)
print(f"small-cap {YEAR_MIN}-{YEAR_MAX} events with windows: {len(sc)} "
      f"({(~sc.success).sum()} failures, {sc.success.sum()} successes)")


def offset_to_date(anchor, off):
    return pd.Timestamp(np.busday_offset(anchor.date(), off, roll="forward"))


def run(params: Params, events=None, seed=0):
    """Event-driven sim -> (daily_equity Series, attribution dict)."""
    e = sc if events is None else events
    capital = params.capital0
    daily = {}   # date -> pnl realized/marked that accrues; we build cumulative later
    # We mark each position's daily contribution, then sum + add to capital0.
    marks_by_date = {}
    attrib = {"long_price": 0, "long_income": 0, "short_price": 0,
              "short_income": 0, "cost": 0, "n_long": 0, "n_short": 0,
              "n_skipped_capacity": 0, "n_skipped_executable": 0}
    # capacity: track gross exposure over time via a simple concurrent-notional model
    open_positions = []  # (exit_date, notional, ticker)
    rng = np.random.default_rng(seed)

    # non-random executability gate: the un-borrowable shorts are NOT random --
    # they are the smallest-float, most-crowded, biggest-drop names. Proxy
    # "crowdedness" by the size of the drop (car_short) and mark the most
    # extreme (1 - executable_frac) of failures as un-shortable.
    unshortable = set()
    if params.short_gate_mode == "worst_first":
        fails = e[~e.success].sort_values("car_short")  # most negative first
        n_drop = int(round((1 - params.short_executable_frac) * len(fails)))
        unshortable = set(fails.head(n_drop).index)

    for _, r in e.iterrows():
        anchor = r.date
        is_long = bool(r.success)
        entry_off = params.long_entry if is_long else params.short_entry
        exit_off = params.long_exit if is_long else params.short_exit
        entry_date = offset_to_date(anchor, entry_off)
        exit_date = offset_to_date(anchor, exit_off)

        # executability gate on shorts (borrow/option availability)
        if not is_long:
            if params.short_gate_mode == "worst_first":
                blocked = r.name in unshortable
            else:
                blocked = rng.random() > params.short_executable_frac
            if blocked:
                attrib["n_skipped_executable"] += 1
                continue

        # capacity: free up matured positions, check gross exposure at entry
        open_positions = [op for op in open_positions if op[0] > entry_date]
        gross = sum(op[1] for op in open_positions)
        ticker_expo = sum(op[1] for op in open_positions if op[2] == r.ticker)
        target = params.frac_per_position * params.capital0
        # per-ticker cap
        target = min(target, params.per_ticker_cap * params.capital0 - ticker_expo)
        # gross cap
        target = min(target, params.max_gross * params.capital0 - gross)
        if target <= 0:
            attrib["n_skipped_capacity"] += 1
            continue
        notional = target

        pnl = position_pnl(r.to_dict(), windows[r.key], notional, params)
        open_positions.append((exit_date, notional, r.ticker))

        if is_long:
            attrib["long_price"] += pnl["price_pnl"]; attrib["long_income"] += pnl["income_pnl"]
            attrib["n_long"] += 1
        else:
            attrib["short_price"] += pnl["price_pnl"]; attrib["short_income"] += pnl["income_pnl"]
            attrib["n_short"] += 1
        attrib["cost"] += pnl["cost"]

        # spread daily marks onto calendar (incremental daily P&L)
        prev = 0.0
        for off, cum in pnl["marks"]:
            d = offset_to_date(anchor, off)
            marks_by_date[d] = marks_by_date.get(d, 0.0) + (cum - prev)
            prev = cum

    # build daily equity curve
    if not marks_by_date:
        return pd.Series(dtype=float), attrib
    idx = pd.date_range(min(marks_by_date), max(marks_by_date), freq="B")
    daily_pnl = pd.Series({d: marks_by_date.get(d, 0.0) for d in idx})
    equity = params.capital0 + daily_pnl.cumsum()
    return equity, attrib


def metrics(equity):
    if len(equity) < 2:
        return {}
    monthly = equity.resample("ME").last().dropna()
    rets = monthly.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    sharpe = (rets.mean() / rets.std() * np.sqrt(12)) if rets.std() > 0 else np.nan
    downside = rets[rets < 0].std()
    sortino = (rets.mean() / downside * np.sqrt(12)) if downside and downside > 0 else np.nan
    dd = (equity / equity.cummax() - 1).min()
    return {"total_return": total, "cagr": cagr, "sharpe": sharpe,
            "sortino": sortino, "max_drawdown": dd, "final": equity.iloc[-1]}


base = Params()
print("\n=== BASE CASE (100% foresight, borrow-short, lending on) ===")
eq, attr = run(base)
m = metrics(eq)
print({k: round(v, 3) for k, v in m.items()})
print("attribution ($):", {k: round(v) if isinstance(v, float) else v for k, v in attr.items()})

results = {"base": {"metrics": m, "attrib": attr}}

# --- REALISTIC CASE: borrow income time-shape (crash after catalyst) +
#     non-random executability gate (drop the biggest-drop shorts) ---
realistic = replace(base, post_collapse_frac=0.10, short_gate_mode="worst_first")
print("\n=== REALISTIC CASE (borrow crashes post-catalyst; worst shorts un-borrowable) ===")
eq_real, attr_real = run(realistic)
m_real = metrics(eq_real)
print({k: round(v, 3) for k, v in m_real.items()})
print("attribution ($):", {k: round(v) if isinstance(v, float) else v for k, v in attr_real.items()})
results["realistic"] = {"metrics": m_real, "attrib": attr_real}

# --- price-only vs +lending (isolate the lending edge) ---
print("\n=== lending contribution ===")
eq_nolend, _ = run(replace(base, include_lending=False))
results["no_lending"] = {"metrics": metrics(eq_nolend)}
print(f"with lending  final=${m['final']:,.0f}  total={m['total_return']*100:.0f}%")
mnl = metrics(eq_nolend)
print(f"price only    final=${mnl['final']:,.0f}  total={mnl['total_return']*100:.0f}%")

# --- short via puts ---
eq_put, attr_put = run(replace(base, short_mode="put"))
results["short_put"] = {"metrics": metrics(eq_put), "attrib": attr_put}

# --- borrow-rate x utilization sensitivity surface ---
print("\n=== borrow-rate x utilization sweep (final $M) ===")
rates = [0.25, 0.50, 1.0, 2.0, 4.0]
utils = [0.2, 0.4, 0.6, 0.8]
surf = np.zeros((len(utils), len(rates)))
for i, u in enumerate(utils):
    for j, rt in enumerate(rates):
        e2, _ = run(replace(base, borrow_rate_annual=rt, utilization=u))
        surf[i, j] = metrics(e2).get("final", np.nan) / 1e6
results["sensitivity"] = {"rates": rates, "utils": utils, "final_Musd": surf.tolist()}
print(pd.DataFrame(surf, index=[f"util={u}" for u in utils],
                   columns=[f"{int(r*100)}%" for r in rates]).round(1).to_string())

# --- accuracy degradation ---
print("\n=== accuracy degradation (flip labels) ===")
deg = {}
for acc in [1.0, 0.95, 0.90, 0.80]:
    finals = []
    for s in range(5):  # average over flip randomizations
        e2 = sc.copy()
        rng = np.random.default_rng(s)
        flip = rng.random(len(e2)) > acc
        e2.loc[flip, "success"] = ~e2.loc[flip, "success"].astype(bool)
        eq2, _ = run(base, events=e2.sort_values("date"), seed=s)
        finals.append(metrics(eq2).get("final", np.nan))
    deg[acc] = float(np.nanmean(finals))
    print(f"accuracy {int(acc*100)}%  ->  avg final ${deg[acc]:,.0f}  ({deg[acc]/base.capital0-1:+.0%})")
results["degradation"] = deg

# --- by sub-period (regime) ---
print("\n=== by regime ===")
regimes = {"2016 (crash)": ("2016-01-01", "2016-12-31"),
           "2017": ("2017-01-01", "2017-12-31"),
           "2018": ("2018-01-01", "2018-12-31"),
           "2019": ("2019-01-01", "2019-12-31")}
reg = {}
for name, (a, b) in regimes.items():
    sub = sc[(sc.date >= a) & (sc.date <= b)]
    if len(sub):
        e2, _ = run(base, events=sub)
        reg[name] = metrics(e2).get("total_return", np.nan)
        print(f"{name:14} total={reg[name]*100:+.0f}%  (n={len(sub)})")
results["regime"] = reg

json.dump(results, open("data/processed/backtest_results.json", "w"), indent=2, default=float)

# --- plots ---
# apples-to-apples price-only baseline uses the SAME (strict) realistic gate,
# so the gap to the realistic line is the lending contribution alone.
eq_real_nolend, _ = run(replace(realistic, include_lending=False))
mrnl = metrics(eq_real_nolend)
results["realistic_no_lending"] = {"metrics": mrnl}
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(eq.index, eq.values / 1e6, color="#2a78d6", lw=1.8, label=f"Naive ceiling (flat borrow, random gate) - ${m['final']/1e6:.0f}M")
ax.plot(eq_real.index, eq_real.values / 1e6, color="#0ca30c", lw=1.8, label=f"Realistic, with lending - ${m_real['final']/1e6:.0f}M")
ax.plot(eq_real_nolend.index, eq_real_nolend.values / 1e6, color="#898781", lw=1.3, ls="--", label=f"Realistic, price only (same strict gate, no lending) - ${mrnl['final']/1e6:.0f}M")
ax.axhline(base.capital0 / 1e6, color="gray", ls=":", lw=0.8)
ax.set_ylabel("Equity ($M)"); ax.set_xlabel("2014-2020")
ax.set_title("Perfect-foresight biotech catalyst strategy - $10M start (small-cap universe)")
ax.legend()
plt.tight_layout(); fig.savefig("reports/backtest_equity.png", dpi=95, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.5, 4.5))
im = ax.imshow(surf, cmap="Blues", aspect="auto")
ax.set_xticks(range(len(rates))); ax.set_xticklabels([f"{int(r*100)}%" for r in rates])
ax.set_yticks(range(len(utils))); ax.set_yticklabels([f"{int(u*100)}%" for u in utils])
ax.set_xlabel("Borrow rate (annualized)"); ax.set_ylabel("Utilization (% of position lent)")
ax.set_title("Final equity ($M) vs lending assumptions")
for i in range(len(utils)):
    for j in range(len(rates)):
        ax.text(j, i, f"{surf[i,j]:.0f}", ha="center", va="center", fontsize=9)
plt.tight_layout(); fig.savefig("reports/backtest_sensitivity.png", dpi=95, bbox_inches="tight"); plt.close(fig)

print("\nwrote data/processed/backtest_results.json + reports/backtest_equity.png + backtest_sensitivity.png")
