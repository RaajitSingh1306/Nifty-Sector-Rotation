"""
strategy.py — Nifty Sector Rotation Strategy

Rules:
  - Universe  : 10 Nifty sector indices
  - Rebalance : Monthly (last trading day of each month)
  - Selection : Top N sectors by composite momentum score
  - Weighting : Equal weight across selected sectors
  - Exit      : Sector drops out of top N → replaced next rebalance
  - Filter    : Skip sector if 21d realised vol > VOL_THRESHOLD (risk filter)

Composite momentum = weighted blend of 1/3/6/12m cross-sectional ranks
  (weights: 10% / 25% / 40% / 25%)
"""

import numpy as np
import pandas as pd

# ── Strategy parameters ────────────────────────────────────────────────────────
TOP_N         = 3       # number of sectors to hold
VOL_THRESHOLD = 0.45    # exclude sectors with annualised vol > 45%
EQUAL_WEIGHT  = True    # True = 1/N, False = momentum-score-weighted


def generate_signals(signals_df: pd.DataFrame,
                     top_n: int = TOP_N,
                     vol_threshold: float = VOL_THRESHOLD) -> pd.DataFrame:
    """
    Takes the monthly signals table from features.build_monthly_signals().
    Returns a wide pivot: index=date, columns=sectors, values=weight (0 or 1/N).

    Logic per month:
      1. Filter out sectors where vol_21d > vol_threshold
      2. Sort remaining by composite score descending
      3. Select top_n
      4. Assign equal weight (1/top_n); rest = 0
    """
    rows = []
    sectors = signals_df["sector"].unique()

    for date, grp in signals_df.groupby("date"):
        # Apply vol filter
        if vol_threshold and "vol_21d" in grp.columns:
            grp = grp[grp["vol_21d"].isna() | (grp["vol_21d"] <= vol_threshold)]

        # Rank and select
        top = grp.nsmallest(top_n, "rank")["sector"].tolist()

        weight = 1 / len(top) if top else 0
        row = {"date": date}
        for s in sectors:
            row[s] = round(weight, 6) if s in top else 0.0
        rows.append(row)

    weights = pd.DataFrame(rows).set_index("date")
    weights.index = pd.to_datetime(weights.index)
    return weights


def get_current_allocation(signals_df: pd.DataFrame,
                           top_n: int = TOP_N,
                           vol_threshold: float = VOL_THRESHOLD) -> dict:
    """
    Returns the current month's sector allocation as a dict.
    """
    latest_date = signals_df["date"].max()
    latest      = signals_df[signals_df["date"] == latest_date].copy()

    if vol_threshold and "vol_21d" in latest.columns:
        excluded = latest[latest["vol_21d"] > vol_threshold]["sector"].tolist()
        latest   = latest[latest["vol_21d"].isna() | (latest["vol_21d"] <= vol_threshold)]
    else:
        excluded = []

    top = latest.nsmallest(top_n, "rank")[
        ["sector", "composite", "mom_1m", "mom_3m", "mom_6m", "rank", "vol_21d"]
    ].to_dict(orient="records")

    return {
        "date":      str(latest_date.date()),
        "top_n":     top_n,
        "selected":  top,
        "excluded_high_vol": excluded,
        "weight_per_sector": round(1 / top_n, 4),
    }


def print_allocation(allocation: dict):
    print(f"\n── Sector Rotation Signal — {allocation['date']} ──────────────────")
    print(f"   Holding top {allocation['top_n']} sectors | Weight per sector: "
          f"{allocation['weight_per_sector']*100:.1f}%")
    if allocation["excluded_high_vol"]:
        print(f"   ⚠  Excluded (high vol): {', '.join(allocation['excluded_high_vol'])}")
    print()
    for s in allocation["selected"]:
        print(f"   #{s['rank']:2d}  {s['sector']:<10}  "
              f"composite={s['composite']:.3f}  "
              f"1m={s.get('mom_1m') or 0:+.3f}  "
              f"3m={s.get('mom_3m') or 0:+.3f}  "
              f"6m={s.get('mom_6m') or 0:+.3f}  "
              f"vol={s.get('vol_21d') or 0:.2f}")
    print("─" * 65)


if __name__ == "__main__":
    from data import fetch_sectors
    from features import build_monthly_signals

    prices  = fetch_sectors()
    signals = build_monthly_signals(prices)
    weights = generate_signals(signals)

    alloc = get_current_allocation(signals)
    print_allocation(alloc)

    print("\nLast 6 months of weights:")
    print(weights.tail(6).to_string())
