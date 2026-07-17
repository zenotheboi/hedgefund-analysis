"""Two charts for the report:
1. CAAR path: cumulative average abnormal return by trading-day offset
   (T-30..T+5), Approved vs CRL. Shows WHERE the move happens -- a gradual
   pre-event drift (anticipation/leakage) vs a sharp one-day shock. This is
   the "car + ar together" view: the slope between days IS the daily average
   abnormal return, the height IS the cumulative (CAR).
2. Small-cap indexed prices combined into ONE overlaid axis (was 10 panels).

Both saved as PNG + base64 for the self-contained HTML report.
"""
import json
import base64
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf

EVENTS = json.load(open("data/processed/biopharmcatalyst_event_windows.json"))
ORIG = pd.read_csv("data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv",
                   parse_dates=["Catalyst Date"])
META = {f"{r['Ticker']}_{r['Catalyst Date'].date()}_{i}": r["Approved or CRL"]
        for i, r in ORIG.iterrows()}
GOOD, BAD = "#0ca30c", "#d03b3b"


# ---- 1. CAAR path ----
byoff = {"Approved": defaultdict(list), "CRL": defaultdict(list)}
for k, rows in EVENTS.items():
    st = META.get(k)
    if st is None:
        continue
    for r in rows:
        byoff[st][r["trading_day_offset"]].append(r["abnormal_return"])

offsets = sorted(byoff["Approved"].keys())
caar = {"Approved": [], "CRL": []}
for st in ["Approved", "CRL"]:
    run = 0.0
    for o in offsets:
        run += np.mean(byoff[st][o])
        caar[st].append(run * 100)

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(offsets, caar["Approved"], color=GOOD, linewidth=2.2, marker="o", markersize=3, label="Approved (n=209)")
ax.plot(offsets, caar["CRL"], color=BAD, linewidth=2.2, marker="o", markersize=3, label="CRL (n=40)")
ax.axvline(0, color="black", linestyle="--", linewidth=1)
ax.axhline(0, color="gray", linestyle=":", linewidth=0.8)
ax.axvspan(-2, 2, color="gray", alpha=0.10)
ax.set_xlabel("Trading days from catalyst (T0). Shaded = the T-2..T+2 CAR window.")
ax.set_ylabel("Cumulative avg abnormal return (%)")
ax.set_title("CAAR path: where the move actually happens\n"
             "Approved drifts up gradually BEFORE the event (anticipation/leakage); "
             "CRL is a sharp one-day shock at T0")
ax.legend(loc="center left")
plt.tight_layout()
fig.savefig("reports/caar_path.png", dpi=95, bbox_inches="tight")
plt.close(fig)
print("saved reports/caar_path.png")


# ---- 2. combined indexed small-cap overlay ----
SMALL = [
    ("MNKD", "2014-06-27", "Approved"), ("KPTI", "2019-07-03", "Approved"),
    ("COLL", "2017-11-07", "Approved"), ("CORT", "2012-02-17", "Approved"),
    ("PCRX", "2018-04-06", "Approved"), ("EYPT", "2013-10-18", "CRL"),
    ("OCUL", "2017-07-11", "CRL"), ("HRTX", "2013-03-28", "CRL"),
    ("LPCN", "2016-06-29", "CRL"), ("TRVN", "2018-11-02", "CRL"),
]
fig, ax = plt.subplots(figsize=(11, 6))
for tk, date, status in SMALL:
    ed = pd.Timestamp(date)
    px = yf.download(tk, start=ed - pd.Timedelta(days=370), end=ed + pd.Timedelta(days=370),
                     auto_adjust=True, progress=False)["Close"]
    if isinstance(px, pd.DataFrame):
        px = px.iloc[:, 0]
    px.index = pd.to_datetime(px.index)
    anchor = px.index[px.index.searchsorted(ed)]
    idx = px / px.loc[anchor] * 100
    days = (px.index - anchor).days
    color = GOOD if status == "Approved" else BAD
    ax.plot(days, idx.values, color=color, alpha=0.55, linewidth=1.2)
ax.axvline(0, color="black", linestyle="--", linewidth=1.2, label="Catalyst date")
ax.axhline(100, color="gray", linestyle=":", linewidth=0.8)
ax.set_xlim(-370, 370)
ax.set_ylim(0, 260)
ax.set_xlabel("Calendar days from catalyst")
ax.set_ylabel("Indexed price (catalyst = 100)")
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0], [0], color=GOOD, label="Approved (5)"),
                   Line2D([0], [0], color=BAD, label="CRL (5)"),
                   Line2D([0], [0], color="black", linestyle="--", label="Catalyst date")])
ax.set_title("Small-cap single-asset events, indexed to 100 at catalyst (all 10 on one axis)")
plt.tight_layout()
fig.savefig("reports/small_cap_indexed_combined.png", dpi=95, bbox_inches="tight")
plt.close(fig)
print("saved reports/small_cap_indexed_combined.png")

for path, name in [("reports/caar_path.png", "caar_path_b64.txt"),
                   ("reports/small_cap_indexed_combined.png", "small_cap_indexed_combined_b64.txt")]:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    open(f"reports/{name}", "w").write(b64)
    print(f"wrote reports/{name}")
