# Nifty Sector Rotation Strategy — Quantitative Momentum Pipeline

[![FastAPI Serving](https://img.shields.io/badge/FastAPI-REST%20API-009688)](#api-reference)
[![Momentum Strategy](https://img.shields.io/badge/Strategy-Composite%20Momentum%20(1%2F3%2F6%2F12m)-blue)](#composite-momentum-score)
[![Backtest](https://img.shields.io/badge/Backtest-Walk--Forward%20vs%20Nifty%2050-emerald)](#backtest-performance)
[![Risk Filter](https://img.shields.io/badge/Risk%20Gate-21d%20Vol%20%3C%2045%25-orange)](#strategy-rules--execution-mechanics)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An institutional quantitative sector rotation strategy operating on Indian equity markets. Every month, **10 Nifty sector indices** are evaluated across multiple lookback windows and cross-sectionally ranked by a composite momentum score. 

The top 3 qualifying sectors are allocated at equal weight (33.3% each) subject to a realized volatility risk gate. A walk-forward backtest measures strategy performance against the broad market Nifty 50 buy-and-hold benchmark under realistic friction (1-month execution lag and 0.1% transaction costs), served live via a **FastAPI REST service**.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Why Sector Rotation?](#why-sector-rotation)
3. [Strategy Rules & Execution Mechanics](#strategy-rules--execution-mechanics)
4. [Composite Momentum Formulation](#composite-momentum-formulation)
5. [Universe of 10 Nifty Sectors](#universe-of-10-nifty-sectors)
6. [System Architecture](#system-architecture)
7. [Project Directory Layout](#project-directory-layout)
8. [Where & How to Start](#where--how-to-start)
   - [Step 1: Environment Setup](#step-1-environment-setup)
   - [Step 2: Run Master Pipeline](#step-2-run-master-pipeline)
   - [Step 3: Start FastAPI Server](#step-3-start-fastapi-server)
9. [REST API Reference](#rest-api-reference)
10. [Generated Artifacts & Diagnostic Plots](#generated-artifacts--diagnostic-plots)
11. [Connected Portfolio Projects](#connected-portfolio-projects)

---

## What This Project Does

Operating on daily historical and live sector data from Yahoo Finance, this pipeline:

1. **Ingests 10 Nifty Sector Indices**: Auto, Bank, Energy, FMCG, IT, Media, Metal, Pharma, Realty, and MNC indices.
2. **Computes Multi-Horizon Cross-Sectional Momentum**: Measures 1-month, 3-month, 6-month, and 12-month returns and ranks them cross-sectionally between $0.0$ (weakest) and $1.0$ (strongest).
3. **Applies Risk Management Filter**: Calculates 21-day annualized realized volatility; disqualifies any sector exhibiting $\sigma_{\text{realized}} > 45\%$.
4. **Executes Walk-Forward Backtest**: Simulates monthly rebalancing against Nifty 50 buy-and-hold with:
   - 1-month execution lag (weights generated on the last trading day of month $T$ apply over month $T+1$).
   - 0.1% one-way transaction friction per rebalanced weight delta.
5. **Serves Signals via API**: Exposes current portfolio allocations and historical performance via FastAPI endpoints.

---

## Why Sector Rotation?

* **Macro Sector Dispersion**: At any point in the Indian macroeconomic cycle, individual sectors diverge drastically from the index. Metals may surge during commodity expansions while IT consolidates; FMCG outperforms in defensives while Banking leads rate cut rallies.
* **Overcoming Return Random Walks**: While individual daily index returns behave as near-random walks (proven in [Nifty-Time-Series](nifty-time-series.md)), **cross-sectional relative momentum** exhibits statistical persistence over 3-to-12 month horizons.
* **Downside Drawdown Mitigation**: Volatility gates and periodic rotation systematically rotate out of deteriorating sectors, preserving capital during market corrections.

---

## Strategy Rules & Execution Mechanics

| Parameter | Specification | Purpose / Rationale |
|---|---|---|
| **Universe** | 10 Nifty Sector Indices | Comprehensive coverage of the Indian macro economy |
| **Benchmark** | Nifty 50 (`^NSEI`) | Standard equity market benchmark |
| **Rebalance Frequency** | Monthly (last trading day of month) | Low portfolio turnover and manageable execution friction |
| **Selection Rule** | Top 3 qualifying sectors | Concentration without idiosyncratic fragility |
| **Weighting** | Equal weight ($33.3\%$ each) | Mitigates estimation error in parameter-heavy mean-variance optimization |
| **Risk Gate** | Realized Vol ($21\text{d}$) $\le 45\%$ ann. | Prevents holding sectors undergoing high-volatility liquidation cascades |
| **Execution Lag** | 1-month lag | Prevents lookahead bias (month-end signals executed next trading day) |
| **Friction** | 0.1% one-way cost per position change | Realistic modeling of brokerage, STT, and slippage |

---

## Composite Momentum Formulation

Log returns are calculated across four horizons and **cross-sectionally percentile-ranked** ($r_i \in [0, 1]$) across all 10 sectors before applying weights:

$$\text{Composite Score} = 0.10 \times \text{Rank}_{1\text{m}} + 0.25 \times \text{Rank}_{3\text{m}} + 0.40 \times \text{Rank}_{6\text{m}} + 0.25 \times \text{Rank}_{12\text{m}}$$

| Lookback Horizon | Weight | Theoretical & Empirical Rationale |
|---|---|---|
| **1 Month** | 10% | Filter for immediate short-term momentum; kept low due to reversal noise |
| **3 Months** | 25% | Intermediate trend confirmation |
| **6 Months** | 40% | **Core momentum driver** (Jegadeesh & Titman 1993: optimal signal-to-noise horizon) |
| **12 Months** | 25% | Long-term macro business cycle trend |

---

## Universe of 10 Nifty Sectors

| Sector Index | Yahoo Finance Symbol | Underlying Industry Focus |
|---|---|---|
| **Nifty Auto** | `^CNXAUTO` | Passenger vehicles, commercial, 2-wheelers, auto ancillaries |
| **Nifty Bank** | `^NSEBANK` | Private and public sector banking giants |
| **Nifty Energy** | `^CNXENERGY` | Oil & gas, power generation, renewables |
| **Nifty FMCG** | `^CNXFMCG` | Consumer staples, packaged goods, tobacco |
| **Nifty IT** | `^CNXIT` | Software exporters, IT consulting, cloud services |
| **Nifty Media** | `^CNXMEDIA` | Entertainment, broadcasting, print |
| **Nifty Metal** | `^CNXMETAL` | Steel, aluminum, zinc, mining conglomerates |
| **Nifty Pharma** | `^CNXPHARMA` | Formulations, APIs, biotechnology |
| **Nifty Realty** | `^CNXREALTY` | Residential and commercial real estate developers |
| **Nifty MNC** | `^CNXMNC` | Multinational corporations operating in India |

---

## System Architecture

```text
data.py          ──► Fetch 10 Sector Indices + ^NSEI (disk cached in data/)
    │
    ▼
features.py      ──► 1m/3m/6m/12m Returns → Cross-Sectional Ranks → Composite Score
    │
    ▼
strategy.py      ──► Apply 45% Vol Gate → Rank Sectors → Allocate Top 3 (33.3%)
    │
    ▼
backtest.py      ──► Walk-forward backtest vs Nifty 50 (1m lag, 0.1% friction)
    │
    ├─────────────────────────────┐
    ▼                             ▼
outputs/                      api.py (FastAPI REST service)
• equity_curve.png            • GET /signals/current
• drawdown.png                • GET /backtest/summary
• rolling_sharpe.png
• sector_weights.png
```

---

## Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Data Ingestion** | `yfinance` | Direct, zero-cost access to all 10 major NSE sector indices + `^NSEI` benchmark with automatic local pickle caching. |
| **Feature Engineering** | `pandas` + `numpy` | Vectorized cross-sectional rolling return windows and multi-period return calculations. |
| **Cross-Sectional Scoring** | `scipy.stats` | Normalized percentile rank calculation (`percentileofscore`) ensuring scale-free relative strength across sectors. |
| **Backtesting Engine** | Vectorized NumPy / Pandas | Realistic event-driven walk-forward simulation with 1-month lag, cash yield, and transaction friction. |
| **Serving Layer** | `FastAPI` + `uvicorn` | High-throughput asynchronous REST endpoints for automated rebalance signal delivery. |
| **Diagnostic Visualization** | `matplotlib` | Multi-panel equity curves, rolling Sharpe, drawdown, and historical allocation plots. |

---

## Project Directory Layout

```text
Nifty Sector Rotation/
├── data.py             # Data fetching module with disk caching
├── features.py         # Momentum feature engineering & cross-sectional ranking
├── strategy.py         # Portfolio construction, vol filters, and weight generation
├── backtest.py         # Vectorized walk-forward backtesting engine
├── run.py              # Master pipeline CLI orchestrator
├── api.py              # FastAPI service exposing signals & backtest summaries
├── requirements.txt    # Python dependencies (yfinance, pandas, scipy, fastapi, uvicorn)
├── ReadMe.md           # Project documentation
├── data/               # Cached price data and generated CSV files
│   ├── sector_prices.csv
│   ├── monthly_weights.csv
│   └── backtest_summary.csv
└── outputs/            # Diagnostic plots
    ├── equity_curve.png
    ├── drawdown.png
    ├── rolling_sharpe.png
    └── sector_weights.png
```

---

## Where & How to Start

### Step 1: Environment Setup

Navigate to the project directory and configure the virtual environment:

```bash
cd "Nifty Sector Rotation"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run Master Pipeline

Execute the end-to-end quantitative pipeline:

```bash
python run.py
```

*To force a fresh data download from Yahoo Finance ignoring the local disk cache:*

```bash
python run.py --no-cache
```

**Pipeline execution steps performed by `run.py`:**
1. Loads/downloads 10 sector indices from 2014 to present.
2. Computes momentum features and monthly weights.
3. Generates out-of-sample backtest metrics against Nifty 50.
4. Outputs performance tables to the console and writes CSV files to `data/`.
5. Renders high-resolution plots to `outputs/`.

### Step 3: Start FastAPI Server

Launch the REST service:

```bash
uvicorn api:app --reload --port 8000
```

* API Base URL: **`http://localhost:8000`**
* Interactive Swagger Docs: **`http://localhost:8000/docs`**

---

## REST API Reference

| Method | Endpoint | Description | Sample Output |
|---|---|---|---|
| `GET` | `/` | Health check | `{"status": "ok", "service": "nifty-sector-rotation"}` |
| `GET` | `/signals/current` | Active month's sector allocation | `{"month": "2026-03-31", "allocation": {"^CNXIT": 0.333, "^CNXAUTO": 0.333, "^CNXMETAL": 0.333}}` |
| `GET` | `/backtest/summary` | Full backtest KPIs vs benchmark | `{"CAGR": {"Strategy": 0.184, "Nifty50": 0.114}, "Sharpe": {"Strategy": 0.812, "Nifty50": 0.366}}` |

---

## Results

Walk-forward backtest evaluated over 12 years of out-of-sample monthly rebalances (including 1-month implementation lag and 0.10% transaction friction):

| Metric | Cross-Sectional Momentum Strategy | Nifty 50 Buy & Hold Benchmark | Outperformance |
|---|---|---|---|
| **CAGR** | **18.4%** | 11.4% | **+7.0% / year** |
| **Sharpe Ratio (Rf=6.5%)** | **0.812** | 0.366 | **+0.446** |
| **Max Drawdown** | Moderated during tech/pharma rotations | -38.4% (March 2020 COVID shock) | Significant capital preservation |
| **Allocation Frequency** | Top 3 sectors dynamically rotated monthly | Static 100% market beta | Captures sector leadership trends |

*Key Finding*: Holding the top 3 momentum sectors with trailing volatility filter significantly outperforms passive market beta over long horizons because Indian sectors experience persistent multi-quarter business cycle leadership regimes (e.g. IT in 2020–2021, Auto & Metals in 2022–2024).

---

## Generated Artifacts & Diagnostic Plots

Executing `python run.py` produces:

1. **`outputs/equity_curve.png`**: Strategy cumulative wealth growth compared to Nifty 50 buy-and-hold.
2. **`outputs/drawdown.png`**: Underwater equity curves showing duration and depth of drawdowns.
3. **`outputs/rolling_sharpe.png`**: 12-month rolling annualized Sharpe ratio demonstrating consistency across market regimes.
4. **`outputs/sector_weights.png`**: Stacked area allocation history showing dynamic industry rotations over the 12-year horizon.

---

## Connected Portfolio Projects

* **[Nifty Time Series](https://github.com/RaajitSingh1306/Nifty-Time-Series)**: Demonstrates why broad index returns cannot be forecasted with linear models, motivating cross-sectional relative strength.
* **[Finance KPI](https://github.com/RaajitSingh1306/Finance_Kpi)**: Foundational single-asset KPI computation engine.
* **[Volatility Intelligence Platform](https://github.com/RaajitSingh1306/volatility-intelligence-platform)**: Regimes classified by VIP can be plugged directly into this strategy to dynamically alter equity exposure between 100%, 50%, and cash.

---

## Limitations & Roadmap

### Known Limitations
- **Upstream Rate Limiting**: Sequential requests to Yahoo Finance for 10 sector indices plus Nifty 50 can experience network latency or rate limiting during initial cache warm-up.
- **Equal Allocation Assumption**: Selected top 3 sectors receive an equal 33.33% portfolio weight, ignoring risk-parity or inverse-volatility weighting across volatile sectors (e.g. Metal vs FMCG).
- **Fixed Monthly Rebalance**: Allocations adjust only on the final trading day of each month; abrupt intraday or mid-month macro shocks cannot trigger emergency rebalancing.
- **End-of-Day Execution Assumption**: Backtest assumes execution at market close, omitting intraday slippage, bid-ask spread friction, and cash drag during sector ETF reallocation.
- **Heuristic Momentum Weights**: Composite momentum weights (10% 1M, 25% 3M, 40% 6M, 25% 12M) are established from quantitative literature rather than dynamically optimized over Indian market regimes.

### Roadmap
- [ ] **Risk-Parity Weighting**: Add inverse-volatility and hierarchical risk parity (HRP) allocation options across selected sectors.
- [ ] **Dynamic Regime Overlay**: Directly integrate VIP's `/current` regime endpoint to shift into cash or defensive sectors during high-volatility regimes.
- [ ] **Bayesian Weight Optimization**: Calibrate momentum lookback weights using Bayesian optimization with walk-forward cross-validation.
- [ ] **Direct Execution Interface**: Integrate Zerodha Kite Connect / Dhan APIs for automated one-click sector ETF basket execution.

---

## License & Disclaimer

MIT License. Designed for quantitative strategy research. Not investment advice.
