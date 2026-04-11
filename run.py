"""
run.py
------
Master pipeline entry point for P3: Nifty Sector Rotation.

Steps:
  1. Fetch 10 Nifty sector indices (cached after first run)
  2. Compute momentum features and monthly signals
  3. Generate rotation weights
  4. Run walk-forward backtest vs Nifty 50 B&H
  5. Print current allocation and metrics, save plots and CSVs

Usage:
    python run.py
    python run.py --no-cache    # force fresh data download
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="P3 Nifty Sector Rotation — full pipeline"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Force re-download of sector prices (ignore disk cache).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    Path("data").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)

    log.info("=" * 58)
    log.info("  P3: Nifty Sector Rotation — Full Pipeline")
    log.info("=" * 58)

    # Step 1 — Data
    log.info("[1/4] Fetching sector data …")
    from data import fetch_sectors
    prices = fetch_sectors(cache=not args.no_cache)
    log.info("      %d days × %d sectors loaded", prices.shape[0], prices.shape[1])

    # Step 2 — Features
    log.info("[2/4] Computing momentum features …")
    from features import build_monthly_signals
    signals = build_monthly_signals(prices)
    log.info(
        "      %d monthly observations across %d sectors",
        len(signals), signals["sector"].nunique(),
    )

    # Step 3 — Strategy signals
    log.info("[3/4] Generating rotation signals …")
    from strategy import generate_signals, get_current_allocation, print_allocation
    weights = generate_signals(signals)
    alloc   = get_current_allocation(signals)
    print_allocation(alloc)

    # Step 4 — Backtest
    log.info("[4/4] Running walk-forward backtest …")
    from backtest import run_backtest, print_metrics, plot_results, plot_sector_weights
    results = run_backtest(prices, weights)
    print_metrics(results)
    plot_results(results)
    plot_sector_weights(results)

    # Persist outputs
    signals.to_csv("data/monthly_signals.csv", index=False)
    weights.to_csv("data/monthly_weights.csv")

    log.info("=" * 58)
    log.info("Pipeline complete. Outputs:")
    log.info("  data/monthly_signals.csv      — sector momentum scores")
    log.info("  data/monthly_weights.csv      — rotation weights by month")
    log.info("  data/backtest_equity.csv      — daily equity curves")
    log.info("  outputs/backtest.png          — equity + drawdown + Sharpe")
    log.info("  outputs/sector_weights.png    — allocation history")
    log.info("=" * 58)


if __name__ == "__main__":
    main()