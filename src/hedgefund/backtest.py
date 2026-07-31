"""Perfect-foresight biotech catalyst strategy: position-level P&L.

Two legs, both on SMALL-CAP names only (large-cap failures are non-events and
large-cap successes carry little borrow demand -- confirmed in the priced
universe):

- LONG+LEND (successes: Approved / Phase 2 met / Phase 3 met): enter ~T-20,
  exit ~T+63. P&L = beta-hedged price return + securities-lending income
  (the crowd shorts these, so borrow rates are high and we collect them).
- SHORT (failures: CRL / Phase 2 miss / Phase 3 miss): enter ~T-10, exit ~T+5.
  Modelled two ways: (a) borrow-and-short (pay borrow, recall risk) or
  (b) long put (pay pre-catalyst premium, no borrow/recall). Executability
  gate: only a fraction of small-cap shorts are actually borrowable/optionable.

Beta hedge: per-day return uses (stock_ret - beta * XBI_ret), i.e. the position
is hedged with XBI at its fitted beta -- so P&L is sector-neutral alpha, not
biotech beta, and there is no compounded-alpha bug from summing fitted alpha
over a long hold.
"""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Params:
    # capital / sizing
    capital0: float = 10_000_000
    frac_per_position: float = 0.05      # target notional per position (of capital)
    per_ticker_cap: float = 0.10         # max exposure to one ticker (of capital)
    max_gross: float = 1.5               # max gross exposure (of capital)
    # long+lend leg
    long_entry: int = -20
    long_exit: int = 63
    borrow_rate_annual: float = 1.00     # 100%/yr on small-cap successes (swept)
    utilization: float = 0.40            # share of position actually on loan (swept)
    # borrow-income time-shape: the crowd shorts a name HARD before its catalyst
    # (high borrow rate), then covers once the outcome is known (rate collapses).
    # post_collapse_frac multiplies the rate for days AFTER T0. 1.0 = flat
    # (naive ceiling); ~0.1 = realistic "high-before / crash-after".
    post_collapse_frac: float = 1.00
    # short leg
    short_entry: int = -10
    short_exit: int = 5
    short_mode: str = "borrow"           # "borrow" or "put"
    short_borrow_rate_annual: float = 1.00   # cost we pay to short the failures
    put_premium_frac: float = 0.10       # ATM pre-catalyst put premium (of notional)
    short_executable_frac: float = 0.60  # fraction of small-cap shorts actually doable
    short_gate_mode: str = "random"      # "random" or "worst_first" (drop the
                                         # biggest-drop = hardest-to-borrow shorts)
    # frictions
    impact_bps: float = 80               # round-trip market impact for small caps
    commission_bps: float = 5
    include_lending: bool = True         # toggle to isolate Stylianos's lending edge
    hedge: bool = True                   # XBI beta hedge; False = un-hedged (isolate the hedge)
    trading_days_year: int = 252


def _hedged_path(window, beta):
    """Cumulative beta-hedged return by offset: list of (off, cum_ret)."""
    out, cum = [], 0.0
    for r in window:
        sr, br = r.get("sr"), r.get("br")
        if sr is None or br is None:
            out.append((r["off"], cum))
            continue
        cum += sr - beta * br
        out.append((r["off"], cum))
    return out


def _cum_at(path, off):
    val = 0.0
    for o, c in path:
        if o <= off:
            val = c
        else:
            break
    return val


def position_pnl(event, window, notional, p: Params):
    """Return dict: total, price_pnl, income_pnl, cost, daily (off, pnl) marks, and
    comp_marks = per-band cumulative marks {band: [(off, cum)]} for the stacked
    area (bands: long_price, long_income, short_net, frictions)."""
    beta = event["beta"] if p.hedge else 0.0     # hedge off -> no XBI subtraction
    path = _hedged_path(window, beta)
    is_long = bool(event["success"])
    frict = notional * (p.impact_bps + p.commission_bps) / 1e4

    if is_long:
        entry, exit_ = p.long_entry, p.long_exit
        r_entry, r_exit = _cum_at(path, entry), _cum_at(path, exit_)
        price_pnl = notional * (r_exit - r_entry)
        hold_days = exit_ - entry
        # two-phase lending income: full rate BEFORE the catalyst (T<=0, crowd
        # shorting hard), rate * post_collapse_frac AFTER (T>0, shorts covered).
        pre_days = max(0, min(0, exit_) - entry)     # days in [entry, 0]
        post_days = max(0, exit_ - max(0, entry))    # days in [0, exit]
        rate = p.borrow_rate_annual * p.utilization / p.trading_days_year
        income_pre = notional * rate * pre_days if p.include_lending else 0.0
        income_post = notional * rate * p.post_collapse_frac * post_days if p.include_lending else 0.0
        income_pnl = income_pre + income_post
        total = price_pnl + income_pnl - frict
        marks = []
        m_price, m_income, m_frict = [], [], []
        for o, c in path:
            if entry <= o <= exit_:
                if o <= 0:
                    accr = income_pre * (o - entry) / max(1, pre_days)
                else:
                    accr = income_pre + income_post * o / max(1, post_days)
                marks.append((o, notional * (c - r_entry) + accr - frict))
                m_price.append((o, notional * (c - r_entry)))
                m_income.append((o, accr))
                m_frict.append((o, -frict))
        return {"leg": "long", "total": total, "price_pnl": price_pnl,
                "income_pnl": income_pnl, "cost": frict, "marks": marks,
                "comp_marks": {"long_price": m_price, "long_income": m_income,
                               "frictions": m_frict}}

    # short leg
    entry, exit_ = p.short_entry, p.short_exit
    r_entry, r_exit = _cum_at(path, entry), _cum_at(path, exit_)
    move = r_exit - r_entry                     # (negative for a failure)
    hold_days = exit_ - entry
    if p.short_mode == "put":
        # ATM put: capture the downside move if negative, loss floored at -premium
        premium = notional * p.put_premium_frac
        put_gain = notional * max(0.0, -move)
        price_pnl = put_gain - premium
        total = price_pnl - frict
        marks, m_short, m_frict = [], [], []
        for o, c in path:
            if entry <= o <= exit_:
                mv = c - r_entry
                marks.append((o, notional * max(0.0, -mv) - premium - frict))
                m_short.append((o, notional * max(0.0, -mv) - premium))
                m_frict.append((o, -frict))
        return {"leg": "short_put", "total": total, "price_pnl": price_pnl,
                "income_pnl": 0.0, "cost": premium + frict, "marks": marks,
                "comp_marks": {"short_net": m_short, "frictions": m_frict}}
    # borrow-and-short: gain -move, pay borrow cost
    price_pnl = notional * (-move)
    borrow_cost = notional * p.short_borrow_rate_annual * hold_days / p.trading_days_year
    total = price_pnl - borrow_cost - frict
    marks, m_short, m_frict = [], [], []
    for o, c in path:
        if entry <= o <= exit_:
            bc = borrow_cost * (o - entry) / max(1, hold_days)
            marks.append((o, notional * -(c - r_entry) - bc - frict))
            m_short.append((o, notional * -(c - r_entry) - bc))   # short net of borrow cost
            m_frict.append((o, -frict))
    return {"leg": "short_borrow", "total": total, "price_pnl": price_pnl,
            "income_pnl": -borrow_cost, "cost": borrow_cost + frict, "marks": marks,
            "comp_marks": {"short_net": m_short, "frictions": m_frict}}
