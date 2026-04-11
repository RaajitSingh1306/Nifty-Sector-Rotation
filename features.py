"""
features.py — Momentum scores, volatility, and correlation features
             for Nifty sector rotation strategy

Momentum windows:
  1m  = 1 monthly period
  3m  = 3 monthly periods
  6m  = 6 monthly periods
  12m = 12 monthly periods

Composite momentum = weighted blend of 1/3/6/12m cross-sectional scores,
ranked cross-sectionally each month.
"""

import numpy as np
import pandas as pd

# Momentum weights (must sum to 1)
MOMENTUM_WEIGHTS = {
    "mom_1m":  0.10,
    "mom_3m":  0.25,
    "mom_6m":  0.40,
    "mom_12m": 0.25,
}

# Windows in monthly periods (used on monthly-resampled prices)
MONTHLY_WINDOWS = {"mom_1m": 1, "mom_3m": 3, "mom_6m": 6, "mom_12m": 12}

# Windows in trading days (used on daily prices)
WINDOWS = {"mom_1m": 21, "mom_3m": 63, "mom_6m": 126, "mom_12m": 252}


def compute_momentum(prices: pd.DataFrame) -> dict:
    """Raw log returns over each window (works on daily or monthly prices)."""
    mom = {}
    for label, window in WINDOWS.items():
        mom[label] = np.log(prices / prices.shift(window))
    return mom


def rank_cross_sectional(df: pd.DataFrame) -> pd.DataFrame:
    """Percentile rank across sectors for each date (0=weakest, 1=strongest)."""
    return df.rank(axis=1, pct=True)


def realised_vol(prices: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    log_ret = np.log(prices / prices.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(252)


def rolling_correlation(prices: pd.DataFrame,
                        window: int = 63,
                        date: pd.Timestamp = None) -> pd.DataFrame:
    log_ret = np.log(prices / prices.shift(1)).dropna()
    if date is None:
        date = log_ret.index[-1]
    subset = log_ret.loc[:date].tail(window)
    return subset.corr().round(3)


def build_monthly_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Resample to month-end, compute composite momentum per sector.
    Returns long-format DataFrame:
      date | sector | mom_1m | mom_3m | mom_6m | mom_12m | composite | vol_21d | rank
    """
    monthly = prices.resample("ME").last()
    sectors = monthly.columns.tolist()

    # Monthly log returns at each horizon
    mom_raw = {label: np.log(monthly / monthly.shift(w))
               for label, w in MONTHLY_WINDOWS.items()}

    # Cross-sectional percentile rank per date, then weighted composite
    ranked    = {k: v.rank(axis=1, pct=True) for k, v in mom_raw.items()}
    composite = sum(ranked[k] * w for k, w in MOMENTUM_WEIGHTS.items())

    # Daily vol resampled to month-end
    vol = realised_vol(prices).resample("ME").last()

    rows = []
    for date in composite.index:
        row_comp = composite.loc[date]
        if row_comp.isna().all():
            continue
        for sector in sectors:
            comp_val = row_comp[sector]
            if pd.isna(comp_val):
                continue
            row = {
                "date":      date,
                "sector":    sector,
                "composite": round(float(comp_val), 4),
                "vol_21d":   (round(float(vol.loc[date, sector]), 4)
                              if date in vol.index
                              and sector in vol.columns
                              and not pd.isna(vol.loc[date, sector])
                              else None),
            }
            for label, mdf in mom_raw.items():
                val = mdf.loc[date, sector] if date in mdf.index else np.nan
                row[label] = round(float(val), 4) if not pd.isna(val) else None
            rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["date","sector","composite",
                                     "vol_21d","mom_1m","mom_3m","mom_6m","mom_12m","rank"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["rank"] = (df.groupby("date")["composite"]
                    .rank(ascending=False, method="first")
                    .astype(int))

    return df.sort_values(["date", "rank"]).reset_index(drop=True)


if __name__ == "__main__":
    from data import fetch_sectors
    prices = fetch_sectors()
    signals = build_monthly_signals(prices)
    print("\nLatest month sector rankings:")
    latest = signals[signals["date"] == signals["date"].max()]
    print(latest[["sector", "composite", "mom_1m", "mom_3m", "mom_6m", "rank"]]
          .to_string(index=False))
    print("\nCorrelation matrix (latest 63 days):")
    print(rolling_correlation(prices))
