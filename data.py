"""
data.py
-------
Fetch and cache daily close prices for 10 Nifty sector indices via yfinance.

Sectors: Auto, Bank, IT, Pharma, FMCG, Metal, Energy, Realty, Media, MNC
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECTORS: dict[str, str] = {
    "Auto":    "^CNXAUTO",
    "Bank":    "^CNXBANK",
    "IT":      "^CNXIT",
    "Pharma":  "^CNXPHARMA",
    "FMCG":    "^CNXFMCG",
    "Metal":   "^CNXMETAL",
    "Energy":  "^CNXENERGY",
    "Realty":  "^CNXREALTY",
    "Media":   "^CNXMEDIA",
    "MNC":     "^CNXMNC",
}

START_DATE = "2014-01-01"
DATA_DIR   = Path("data")
CACHE_PATH = DATA_DIR / "sector_prices.csv"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_sectors(
    start: str = START_DATE,
    end: str | None = None,
    cache: bool = True,
) -> pd.DataFrame:
    """
    Return daily close prices for all Nifty sector indices.

    Parameters
    ----------
    start : str
        Start date in YYYY-MM-DD format.
    end : str or None
        End date; defaults to today.
    cache : bool
        Load from disk if cached; set False to force re-download.

    Returns
    -------
    pd.DataFrame
        Wide format: index=Date, columns=sector names, values=Close price.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if cache and CACHE_PATH.exists():
        log.info("Loading cached sector data from %s", CACHE_PATH)
        return pd.read_csv(CACHE_PATH, index_col="Date", parse_dates=True)

    log.info("Downloading Nifty sector indices …")
    frames: dict[str, pd.Series] = {}

    for name, ticker in SECTORS.items():
        try:
            raw = yf.download(ticker, start=start, end=end,
                              auto_adjust=True, progress=False)
            if raw.empty:
                log.warning("%s (%s) — no data returned", name, ticker)
                continue
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            frames[name] = raw["Close"].rename(name)
            log.info("  ✓  %-8s  %d rows", name, len(raw))
        except Exception as exc:  # noqa: BLE001
            log.error("  ✗  %s (%s) — %s", name, ticker, exc)

    df = pd.concat(frames.values(), axis=1).dropna(how="all")
    df.index.name = "Date"
    df.to_csv(CACHE_PATH)
    log.info("Saved %d rows × %d sectors → %s", df.shape[0], df.shape[1], CACHE_PATH)
    return df


def monthly_log_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Month-end log returns computed from daily close prices."""
    monthly = df.resample("ME").last()
    return np.log(monthly / monthly.shift(1)).dropna(how="all")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = fetch_sectors(cache=False)
    print("\nSector price preview:")
    print(df.tail(3).round(1))
    print(f"\nDate range : {df.index[0].date()} → {df.index[-1].date()}")
    print(f"Sectors    : {df.columns.tolist()}")