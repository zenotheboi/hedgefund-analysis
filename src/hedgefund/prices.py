"""Abnormal stock returns around a verified clinical-trial announcement date.

CTOD's stock_price module reduces the market reaction to a binary up/down
slope of a 5-day SMA, with no benchmark adjustment -- a bad sector day for
biotech is indistinguishable from a bad trial readout. We rebuild the signal
instead of reusing it: pull the full T-30..T+5 trading-day window (never
collapse it to one number) for both the ticker and XBI (sector benchmark),
fit a simple market-model beta on a pre-event estimation window, and use
that to compute a per-day abnormal return = actual return - benchmark-implied
return. CAR (cumulative abnormal return) is a convenience aggregate on top
of that per-day series, not a replacement for it.
"""
import numpy as np
import pandas as pd
import yfinance as yf

DEFAULT_BENCHMARK = "XBI"
EVENT_WINDOW_PRE = 30   # trading days before the announcement (T-30)
EVENT_WINDOW_POST = 5   # trading days after the announcement (T+5)
ESTIMATION_WINDOW = 120  # trading days used to fit alpha/beta, ending at T-31


def _download_close(ticker: str, start, end) -> pd.Series:
    """Adjusted daily close for one ticker, as a plain (non-MultiIndex) Series."""
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"yfinance returned no data for {ticker} between {start} and {end}")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.name = ticker
    return close


def _trading_day_position(dates: pd.DatetimeIndex, announcement_date) -> int:
    """Index position of the first trading day on or after announcement_date.

    If the announcement lands on a weekend/holiday (or after market close),
    this anchors T0 to the next trading day, which is when the market could
    first react.
    """
    ann = pd.Timestamp(announcement_date)
    pos = dates.searchsorted(ann)
    if pos >= len(dates):
        raise ValueError(f"announcement_date {announcement_date} is after the last available trading day")
    return int(pos)


def fetch_event_data(
    ticker: str,
    announcement_date: str,
    benchmark: str = DEFAULT_BENCHMARK,
    event_window_pre: int = EVENT_WINDOW_PRE,
    event_window_post: int = EVENT_WINDOW_POST,
    estimation_window: int = ESTIMATION_WINDOW,
) -> pd.DataFrame:
    """Aligned daily returns for ticker and benchmark, spanning the estimation
    window plus the full event window. Returns a DataFrame indexed by date
    with columns [stock_close, benchmark_close, stock_return, benchmark_return,
    trading_day_offset], where trading_day_offset=0 marks the announcement's
    anchor trading day (T0).
    """
    ann = pd.Timestamp(announcement_date)
    # Wide calendar buffer so we have enough trading days on both ends even
    # after holidays/weekends are stripped out by yfinance.
    calendar_start = ann - pd.Timedelta(days=int((estimation_window + event_window_pre) * 1.6) + 30)
    calendar_end = ann + pd.Timedelta(days=int(event_window_post * 1.6) + 15)

    stock_close = _download_close(ticker, calendar_start, calendar_end)
    bench_close = _download_close(benchmark, calendar_start, calendar_end)

    prices = pd.concat([stock_close, bench_close], axis=1, join="inner")
    prices.columns = ["stock_close", "benchmark_close"]
    prices = prices.sort_index()

    returns = prices[["stock_close", "benchmark_close"]].pct_change()
    returns.columns = ["stock_return", "benchmark_return"]
    out = prices.join(returns)

    t0_pos = _trading_day_position(out.index, ann)
    out["trading_day_offset"] = np.arange(len(out)) - t0_pos

    lo = t0_pos - (event_window_pre + estimation_window)
    if lo < 0:
        raise ValueError(
            f"Not enough price history before {announcement_date} for {ticker}: "
            f"need {event_window_pre + estimation_window} trading days, only have {t0_pos}. "
            "Widen the download range or reduce estimation_window."
        )
    hi = t0_pos + event_window_post
    if hi >= len(out):
        raise ValueError(
            f"Not enough price history after {announcement_date} for {ticker}: "
            f"need T+{event_window_post}, only have {len(out) - 1 - t0_pos} trading days after T0."
        )

    return out.iloc[lo:hi + 1].copy()


def fit_market_model(data: pd.DataFrame, event_window_pre: int = EVENT_WINDOW_PRE,
                      estimation_window: int = ESTIMATION_WINDOW) -> tuple:
    """OLS-fit alpha/beta of stock_return ~ alpha + beta * benchmark_return over
    the estimation window, i.e. the `estimation_window` trading days that end
    just before T-30 (so the fit never sees data from inside the event window).
    """
    est = data[(data["trading_day_offset"] < -event_window_pre) &
               (data["trading_day_offset"] >= -event_window_pre - estimation_window)]
    est = est.dropna(subset=["stock_return", "benchmark_return"])
    if len(est) < estimation_window // 2:
        raise ValueError(
            f"Estimation window has only {len(est)} usable days (wanted ~{estimation_window}); "
            "beta estimate would be unreliable."
        )
    beta, alpha = np.polyfit(est["benchmark_return"].values, est["stock_return"].values, 1)
    return float(alpha), float(beta)


def short_window_car(event_window: pd.DataFrame, pre: int = 2, post: int = 2) -> dict:
    """CAR (and matching raw/benchmark cumulative returns) over a narrow
    sub-window [T-pre, T+post] of an already-computed event_window DataFrame
    (as returned in compute_abnormal_returns()['event_window'], or reloaded
    from a cached full_pool_event_windows.json entry).

    Exists because the full T-30..T+5 CAR sums a per-day alpha/beta-implied
    'expected_return' over 36 trading days -- a noisy daily alpha estimated
    on the pre-event estimation window compounds linearly with window length,
    so long-window CAR can be dominated by extrapolated drift rather than the
    actual announcement reaction (see STATUS.md, sign_disagreement analysis).
    Standard event-study practice (MacKinlay 1997) keeps windows short for
    exactly this reason. This keeps alpha (it's still a legitimate part of
    the stock's normal-behavior baseline) but stops asking it to explain
    price action from days the event couldn't plausibly have caused.
    """
    w = event_window[(event_window["trading_day_offset"] >= -pre) &
                      (event_window["trading_day_offset"] <= post)]
    raw = float((1 + w["stock_return"]).prod() - 1)
    benchmark = float((1 + w["benchmark_return"]).prod() - 1)
    car = float(w["abnormal_return"].sum())
    return {"pre": pre, "post": post, "raw_return": raw, "benchmark_return": benchmark, "car": car}


def compute_abnormal_returns(
    ticker: str,
    announcement_date: str,
    benchmark: str = DEFAULT_BENCHMARK,
    event_window_pre: int = EVENT_WINDOW_PRE,
    event_window_post: int = EVENT_WINDOW_POST,
    estimation_window: int = ESTIMATION_WINDOW,
) -> dict:
    """Per-day abnormal returns (market-model residuals vs. benchmark) over the
    full T-{event_window_pre}..T+{event_window_post} trading-day window around
    announcement_date, plus the cumulative abnormal return (CAR) as a
    convenience aggregate. Never collapses the window to a single number --
    'event_window' below is the full per-day series; 'car' is derived from it.

    Returns dict with:
      ticker, benchmark, announcement_date, anchor_date (actual trading day
      used as T0), alpha, beta (fit on the pre-event estimation window),
      event_window (DataFrame, one row per trading day, columns:
        trading_day_offset, date, stock_close, benchmark_close, stock_return,
        benchmark_return, expected_return, abnormal_return),
      car (float, sum of abnormal_return over the event window).
    """
    data = fetch_event_data(ticker, announcement_date, benchmark,
                             event_window_pre, event_window_post, estimation_window)
    alpha, beta = fit_market_model(data, event_window_pre, estimation_window)

    event = data[(data["trading_day_offset"] >= -event_window_pre) &
                 (data["trading_day_offset"] <= event_window_post)].copy()
    event["expected_return"] = alpha + beta * event["benchmark_return"]
    event["abnormal_return"] = event["stock_return"] - event["expected_return"]

    anchor_date = event.index[event["trading_day_offset"] == 0][0]

    event_out = event.reset_index().rename(columns={event.index.name or "index": "date"})
    event_out = event_out[["date", "trading_day_offset", "stock_close", "benchmark_close",
                            "stock_return", "benchmark_return", "expected_return", "abnormal_return"]]

    car = float(event["abnormal_return"].sum())

    return {
        "ticker": ticker,
        "benchmark": benchmark,
        "announcement_date": str(pd.Timestamp(announcement_date).date()),
        "anchor_date": str(pd.Timestamp(anchor_date).date()),
        "alpha": alpha,
        "beta": beta,
        "event_window": event_out,
        "car": car,
    }
