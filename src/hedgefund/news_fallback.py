"""CTOD scraped-news fallback for announcement dates.

Per the methodology's date-finding order (EDGAR 8-K -> CTOD news dates ->
Form 6-K -> manual check), this is only a rescue path for trials where the
primary EDGAR full-text search returns zero hits. A news date is never
trusted standalone -- it's used to re-run a narrower EDGAR search near that
date, since CTOD's news-trial matching was "tuned for label coverage, not
date precision" (per the doc).
"""
import ast
from datetime import datetime, timedelta

import pandas as pd

NEWS_COLUMNS = [str(i) for i in range(10)]


def _parse_headline_cell(cell) -> dict | None:
    if pd.isna(cell):
        return None
    try:
        return ast.literal_eval(cell)
    except (ValueError, SyntaxError):
        return None


def load_news_index(path: str) -> dict:
    """Return {nct_id: [ {date, title, link, source}, ... ]} sorted by date."""
    df = pd.read_csv(path)
    index = {}
    for _, row in df.iterrows():
        headlines = []
        for col in NEWS_COLUMNS:
            if col not in row:
                continue
            h = _parse_headline_cell(row[col])
            if h and h.get("date"):
                try:
                    parsed_date = datetime.strptime(h["date"], "%b %d, %Y")
                except ValueError:
                    continue
                headlines.append({
                    "date": parsed_date,
                    "title": h.get("title"),
                    "link": h.get("link"),
                    "source": h.get("source"),
                })
        if headlines:
            index[row["nct_id"]] = sorted(headlines, key=lambda h: h["date"])
    return index


def candidate_dates_in_window(nct_id: str, news_index: dict, completion_date: str,
                               months_after: int = 12) -> list:
    """Candidate announcement dates from matched news, within the same window
    used for EDGAR search. Returns the raw headline dicts (with datetime
    'date'), not a single answer -- caller should verify against EDGAR.
    """
    headlines = news_index.get(nct_id, [])
    if not headlines:
        return []
    start = datetime.strptime(completion_date, "%Y-%m-%d")
    end = start + timedelta(days=30 * months_after)
    return [h for h in headlines if start <= h["date"] <= end]
