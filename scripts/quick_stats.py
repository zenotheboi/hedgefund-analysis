"""
============================================================================
 開會快速數據工具 — 改上面的參數,按 F5 / Run,馬上出數字。不用重抓股價。
 (讀已快取的 event windows,秒出結果)
============================================================================
 Manager 可能問的,對應改哪個參數:
   "換個窗口看看"          -> 改 CAR_PRE / CAR_POST
   "排除大藥廠還顯著嗎"     -> EXCLUDE_BIG_PHARMA = False
   "分年份看"              -> BY_YEAR = True
   "只看某幾年"            -> YEAR_MIN / YEAR_MAX
============================================================================
"""

# ============ 參數:開會時改這裡 ============
CAR_PRE  = 2          # 事件前幾個交易日 (T-PRE)
CAR_POST = 2          # 事件後幾個交易日 (T+POST)
EXCLUDE_BIG_PHARMA = False   # True = 排除大藥廠 (看訊號是否被大公司帶動)
BY_YEAR  = False      # True = 拆成每年一列
YEAR_MIN = 2009       # 只看 >= 這年
YEAR_MAX = 2020       # 只看 <= 這年
# ===========================================

import json, sys
import pandas as pd, numpy as np
from scipy import stats

BIG_PHARMA = {'NVO','AZN','ABBV','PFE','AMGN','BMY','VRTX','GILD','JNJ','MRK',
              'LLY','NVS','SNY','BIIB','RHHBY','GSK','TAK','GMAB'}

EVENTS = json.load(open("data/processed/biopharmcatalyst_event_windows.json"))
ORIG = pd.read_csv("data/interim/27_biopharmcatalyst_approved_crl_small_molecule.csv",
                   parse_dates=["Catalyst Date"])

# key -> (ticker, status, year)
meta = {}
for idx, row in ORIG.iterrows():
    key = f"{row['Ticker']}_{row['Catalyst Date'].date()}_{idx}"
    meta[key] = (row["Ticker"], row["Approved or CRL"], row["Catalyst Date"].year)


def car(rows, pre, post):
    return sum(r["abnormal_return"] for r in rows
               if -pre <= r["trading_day_offset"] <= post)


def collect(year_filter=None):
    appr, crl = [], []
    for k, rows in EVENTS.items():
        if k not in meta:
            continue
        tk, st, yr = meta[k]
        if EXCLUDE_BIG_PHARMA and tk in BIG_PHARMA:
            continue
        if not (YEAR_MIN <= yr <= YEAR_MAX):
            continue
        if year_filter is not None and yr != year_filter:
            continue
        (appr if st == "Approved" else crl).append(car(rows, CAR_PRE, CAR_POST))
    return appr, crl


def row_stats(label, appr, crl):
    def med(x): return f"{np.median(x)*100:+.2f}%" if x else "  n/a"
    def p_vs0(x):
        return f"{stats.wilcoxon(x)[1]:.2g}" if len(x) >= 6 else "n/a"
    if len(appr) >= 1 and len(crl) >= 1:
        mw = f"{stats.mannwhitneyu(appr, crl, alternative='two-sided')[1]:.2g}"
    else:
        mw = "n/a"
    print(f"{label:14} | Appr n={len(appr):<3} med={med(appr):<8} vs0={p_vs0(appr):<8}"
          f"| CRL n={len(crl):<3} med={med(crl):<9} vs0={p_vs0(crl):<9}| Appr-vs-CRL p={mw}")


print(f"\n窗口 T-{CAR_PRE}..T+{CAR_POST}  |  排除大藥廠={EXCLUDE_BIG_PHARMA}  |  年份 {YEAR_MIN}-{YEAR_MAX}")
print("-" * 118)
if BY_YEAR:
    for yr in range(YEAR_MIN, YEAR_MAX + 1):
        a, c = collect(year_filter=yr)
        if a or c:
            row_stats(str(yr), a, c)
    print("-" * 118)
a, c = collect()
row_stats("TOTAL", a, c)
print("\n(med=median CAR  vs0=Wilcoxon對零檢定p  Appr-vs-CRL=Mann-Whitney雙樣本p)")
