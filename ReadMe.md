# P3 — Nifty Sector Rotation Strategy

Quantitative sector rotation strategy on Indian equity markets. Every month, 10 Nifty sector indices are ranked by a composite momentum score across 4 time horizons. The top 3 sectors are held at equal weight until the next rebalance. A walk-forward backtest measures performance against a Nifty 50 buy-and-hold benchmark.

---

## Architecture

```
data.py       — fetch 10 Nifty sector indices via yfinance (disk-cached)
    ↓
features.py   — momentum scores (1/3/6/12m), cross-sectional rank,
                composite score, realised vol, rolling correlation
    ↓
strategy.py   — monthly rotation signal: top-N selection,
                vol filter, equal-weight allocation
    ↓
backtest.py   — walk-forward backtest vs Nifty 50 B&H
                (1-month lag, 0.1% transaction cost, full metrics)
    ↓
outputs/      — equity curve, drawdown, rolling Sharpe,
                sector allocation history
```

---

## Strategy Logic

| Step | Detail |
|---|---|
| Universe | 10 Nifty sector indices (Auto, Bank, IT, Pharma, FMCG, Metal, Energy, Realty, Media, MNC) |
| Rebalance | Monthly — last trading day of each month |
| Signal | Composite momentum score (see below) |
| Selection | Top 3 sectors by composite score |
| Weighting | Equal weight — 33.3% each |
| Risk filter | Exclude sectors with 21d realised vol > 45% annualised |
| Execution lag | Weights set at month-end apply from the **next** month's first day |
| Transaction cost | 0.1% one-way per position changed |

---

## Composite Momentum Score

Log returns are computed at 4 horizons and **cross-sectionally ranked** (0–1 percentile) before weighting, so each sector's score reflects its relative strength versus the other 9 — not its absolute return.

| Window | Weight | Rationale |
|---|---|---|
| 1 month | 10% | Short-term noise — low weight |
| 3 months | 25% | Recent trend confirmation |
| 6 months | 40% | Core momentum signal |
| 12 months | 25% | Long-term trend direction |

6-month momentum is weighted highest following Jegadeesh & Titman (1993): 1-month signals carry reversal risk; 12-month signals lag too far.

---

## Sector Universe

| Ticker | Sector |
|---|---|
| ^CNXAUTO | Auto |
| ^CNXBANK | Banking |
| ^CNXIT | IT |
| ^CNXPHARMA | Pharma |
| ^CNXFMCG | FMCG |
| ^CNXMETAL | Metals |
| ^CNXENERGY | Energy |
| ^CNXREALTY | Realty |
| ^CNXMEDIA | Media |
| ^CNXMNC | MNC |

---

## Backtest Methodology

- **Data:** Daily OHLCV from Yahoo Finance, 2014–present
- **Signal construction:** Monthly resampled prices → momentum → composite
- **Execution:** 1-month lag (no look-ahead bias)
- **Costs:** 0.1% transaction cost on rebalance days only
- **Benchmark:** Nifty 50 (`^NSEI`) buy-and-hold
- **Risk-free rate:** 6.5% annualised (India 10yr G-Sec)
- **Signal execution**: Sector momentum scores computed at month-end T are applied at the open of month T+1 (1-month execution lag). This prevents look-ahead bias — the model never uses information that would not have been available at decision time.
- **Walk-forward structure**: training window expands, never a rolling window of fixed size, to simulate real deployment where all historical data is available.

### Metrics

| Metric | Description |
|---|---|
| CAGR | Compound annual growth rate |
| Sharpe | Annualised excess return / total vol |
| Sortino | Annualised excess return / downside vol only |
| Max Drawdown | Worst peak-to-trough % over full history |
| Calmar | CAGR / \|Max Drawdown\| |
| Win Rate (monthly) | % of months with positive return |
| Monthly Turnover | Average % of portfolio replaced each month |

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
# Full pipeline — fetch → signals → backtest → plots
python run.py

# Force fresh data download (ignore cache)
python run.py --no-cache

# Individual modules
python data.py       # fetch and cache sector prices
python features.py   # print latest month sector rankings
python strategy.py   # print current allocation
python backtest.py   # run backtest and save plots
```

---

## Outputs

| File | Description |
|---|---|
| `data/sector_prices.csv` | Daily close prices for all 10 sectors (cached) |
| `data/monthly_signals.csv` | Long-format: date × sector × all scores |
| `data/monthly_weights.csv` | Wide-format monthly allocation weights |
| `data/backtest_equity.csv` | Daily equity curves (strategy + benchmark) |
| `outputs/backtest.png` | Equity curve, drawdown, rolling 1yr Sharpe |
| `outputs/sector_weights.png` | Stacked area chart of sector allocation history |

---

## File Structure

```
03_sector_rotation/
├── data.py
├── features.py
├── strategy.py
├── backtest.py
├── run.py
├── requirements.txt
├── LICENSE
├── .gitignore
├── data/          ← generated (git-ignored)
└── outputs/       ← generated (git-ignored)
```

---

## Roadmap — Phase 2

| Module | What it adds |
|---|---|
| `cointegration.py` | Engle-Granger test on sector pairs, spread z-score, OU half-life |
| `timescaledb/` | PostgreSQL + TimescaleDB schema for OHLCV + signals |
| `api/main.py` | FastAPI: `/signals/current`, `/signals/history`, `/backtest/summary` |
| `dashboard.py` | Streamlit: rotation heatmap, allocation chart, equity curve, live signal |

---

## Data Disclaimer

Market data sourced from Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance).
For educational and portfolio demonstration purposes only. Not financial advice.

---
