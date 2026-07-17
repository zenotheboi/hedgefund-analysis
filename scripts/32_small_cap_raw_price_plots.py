"""10 small-cap (non-big-pharma) Approved/CRL events, plotted individually in
RAW dollar price (own axis each), with the catalyst date marked AND other
large daily moves (|return| > BIG_MOVE_PCT) flagged -- those big non-event
moves are proxies for earnings calls / other news (we don't have an exact
earnings-date feed, so a large-move flag is the stand-in). A second figure
shows the same 10 indexed to 100 at the event for cross-company comparison.
Both saved as PNG for embedding in the HTML report.
"""
import sys
import base64
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf

OUT_RAW = "reports/small_cap_raw.png"
OUT_IDX = "reports/small_cap_indexed.png"
BIG_MOVE_PCT = 0.12   # |daily return| above this = flagged as a big non-event move

# (ticker, drug, catalyst_date, status) -- 10 single-asset-ish small caps, mix of both
EVENTS = [
    ("MNKD", "Afrezza",      "2014-06-27", "Approved"),
    ("KPTI", "Selinexor",    "2019-07-03", "Approved"),
    ("COLL", "Xtampza ER",   "2017-11-07", "Approved"),
    ("CORT", "Korlym",       "2012-02-17", "Approved"),
    ("PCRX", "Exparel",      "2018-04-06", "Approved"),
    ("EYPT", "Iluvien",      "2013-10-18", "CRL"),
    ("OCUL", "Dextenza",     "2017-07-11", "CRL"),
    ("HRTX", "Sustol",       "2013-03-28", "CRL"),
    ("LPCN", "Tlando",       "2016-06-29", "CRL"),
    ("TRVN", "Oliceridine",  "2018-11-02", "CRL"),
]


def pull(ticker, event_date):
    ed = pd.Timestamp(event_date)
    px = yf.download(ticker, start=ed - pd.Timedelta(days=370),
                     end=ed + pd.Timedelta(days=370), auto_adjust=True, progress=False)["Close"]
    if isinstance(px, pd.DataFrame):
        px = px.iloc[:, 0]
    px.index = pd.to_datetime(px.index)
    return px


series = []
for tk, drug, date, status in EVENTS:
    px = pull(tk, date)
    series.append((tk, drug, pd.Timestamp(date), status, px))
    print(f"  {tk} {drug}: {len(px)} days")


def big_move_days(px, event_date):
    ret = px.pct_change()
    flags = []
    for dt, r in ret.items():
        if abs(r) > BIG_MOVE_PCT and abs((dt - event_date).days) > 5:
            flags.append((dt, px.loc[dt], r))
    return flags


def draw(indexed: bool, outpath: str):
    fig, axes = plt.subplots(5, 2, figsize=(13, 16))
    for ax, (tk, drug, ed, status, px) in zip(axes.flat, series):
        color = "#0ca30c" if status == "Approved" else "#d03b3b"
        anchor = px.index[px.index.searchsorted(ed)]
        y = px / px.loc[anchor] * 100 if indexed else px
        ax.plot(px.index, y, color=color, linewidth=1.3)
        ax.axvline(ed, color="black", linestyle="--", linewidth=1)
        # flag big non-event moves
        for dt, price, r in big_move_days(px, ed):
            yy = price / px.loc[anchor] * 100 if indexed else price
            ax.plot(dt, yy, "o", color="#e08a00", markersize=5, zorder=5)
        ax.set_title(f"{tk} — {drug} ({status})", fontsize=10)
        ax.tick_params(labelsize=7)
        if indexed:
            ax.axhline(100, color="gray", linestyle=":", linewidth=0.7)
    label = "indexed to 100 at catalyst" if indexed else "raw close ($)"
    fig.suptitle(f"Small-cap single-asset events — {label}\n"
                 f"black dashes = catalyst date · orange dots = other big moves (|daily| > {BIG_MOVE_PCT:.0%}, earnings/news proxy)",
                 fontsize=12, y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(outpath, dpi=90, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {outpath}")


draw(indexed=False, outpath=OUT_RAW)
draw(indexed=True, outpath=OUT_IDX)

# emit base64 so it can be embedded in the self-contained HTML report
for path, name in [(OUT_RAW, "small_cap_raw_b64.txt"), (OUT_IDX, "small_cap_indexed_b64.txt")]:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    with open(f"reports/{name}", "w") as f:
        f.write(b64)
    print(f"wrote reports/{name} ({len(b64)} chars)")
