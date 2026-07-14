"""Categorize CTOD's binary outcome label into a richer outcome_category.

CTOD hard-codes terminated/withdrawn/suspended trials as label=0 (failure).
But a trial stopped "due to sponsor decision, not for efficacy or safety
reasons" is not a scientific failure -- it's a business/strategic event with
a plausibly different market reaction. Rather than dropping these rows or
silently keeping them lumped in with real failures, tag them so downstream
steps (event-date verification, price-archetype analysis) can treat them as
their own bucket instead of noise inside "failure."
"""
import re

import pandas as pd

BUSINESS_KEYWORDS = re.compile(
    r"business|sponsor decision|sponsor's decision|strategic|funding|"
    r"not related to|not for efficacy|not for safety|financial|portfolio|"
    r"company decision|study terminated by sponsor",
    re.IGNORECASE,
)
# Explicit denial that the stop was efficacy/safety-driven -- must be checked
# BEFORE the plain efficacy/safety keyword match below, since naive keyword
# matching on "efficacy"/"safety" ignores negation (e.g. "not based on any
# new efficacy or safety data" is a business reason, not a failure).
NEGATED_EFFICACY_SAFETY = re.compile(
    r"(not|no|non|neither|unrelated to|independent of|regardless of|without)\b"
    r"(?:[\w'\s]{0,40}?)\b(efficacy|safety|adverse|dsmb)",
    re.IGNORECASE,
)
EFFICACY_SAFETY_KEYWORDS = re.compile(
    r"efficacy|futilit|did not meet|failed to meet|lack of efficacy|"
    r"lack of response|lack of activity|safety concern|adverse event|"
    r"dsmb|data safety monitoring|did not achieve|non-superior|inferiority",
    re.IGNORECASE,
)
LOGISTICS_KEYWORDS = re.compile(
    r"enrollment|enrolment|accrual|not initiated|recruit|slow accrual|"
    r"low enrollment|covid|pandemic",
    re.IGNORECASE,
)

TERMINAL_STATUSES = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}


def classify_outcome_category(overall_status: str, why_stopped, labels: float) -> str:
    """Return one of: success, failure_efficacy_safety, business_termination,
    logistics_termination, ambiguous_termination.

    `labels` is CTOD's original binary label (1=success, 0=failure), preserved
    as a fallback signal but not trusted blindly for terminated/withdrawn rows.
    """
    why = "" if pd.isna(why_stopped) else str(why_stopped)
    status = "" if pd.isna(overall_status) else str(overall_status).upper()

    if status not in TERMINAL_STATUSES:
        return "success" if labels == 1.0 else "failure_efficacy_safety"

    # Order matters: check negation and logistics before the plain
    # efficacy/safety keyword match, since that match can't tell "lack of
    # efficacy" from "lack of enrollment" or "not for efficacy reasons".
    if NEGATED_EFFICACY_SAFETY.search(why):
        return "business_termination"
    if LOGISTICS_KEYWORDS.search(why):
        return "logistics_termination"
    if BUSINESS_KEYWORDS.search(why):
        return "business_termination"
    if EFFICACY_SAFETY_KEYWORDS.search(why):
        return "failure_efficacy_safety"
    return "ambiguous_termination"
