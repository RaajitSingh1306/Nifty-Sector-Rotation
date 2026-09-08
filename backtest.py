"""
backtest.py — Walk-forward backtest for Nifty Sector Rotation strategy

Method:
  - Monthly rebalance using end-of-month weights (1-month lag for realism)
  - Daily returns interpolated between rebalance dates
  - Benchmark: Nifty 50 (^NSEI) buy-and-hold
  - Transaction cost: 0.1% per rebalance per position change

Metrics reported:
  CAGR, Sharpe, Sortino, Max Drawdown, Calmar,
  Win Rate (monthly), Avg holding period, Turnover
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import yfinance as yf

os.makedirs("outputs", exist_ok=True)

TRANSACTION_COST = 0.001   # 0.1% one-way per position
RISK_FREE_RATE   = 0.065   # annualised
TRADING_DAYS     = 252


# ── Benchmark ─────────────────────────────────────────────────────────────────

def fetch_nifty50(start: str, end: str) -> pd.Series:
    raw = yf.download("^NSEI", start=start, end=end,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw["Close"].rename("Nifty50")


# ── Core backtest ──────────────────────────────────────────────────────────────

def run_backtest(prices: pd.DataFrame,
                 weights: pd.DataFrame,
                 transaction_cost: float = TRANSACTION_COST) -> dict:
    """
    prices  : daily close, wide format (index=Date, cols=sectors)
    weights : monthly end-of-month weights (index=month-end date, cols=sectors)

    Returns dict with equity series, metrics, and trade log.
    """
    # Align sectors
    sectors = [c for c in weights.columns if c in prices.columns]
    prices  = prices[sectors]
    weights = weights[sectors]

    # Daily log returns
    daily_ret = np.log(prices / prices.shift(1)).dropna()

    # Forward-fill monthly weights to daily (1-month lag: weight set at end of
    # month applies from first day of NEXT month)
    w_daily = weights.shift(1).reindex(daily_ret.index, method="ffill").fillna(0)

    # Normalise weights each day to sum to 1 (handles partial data at start)
    row_sums = w_daily.sum(axis=1).replace(0, np.nan)
    w_daily  = w_daily.div(row_sums, axis=0).fillna(0)

    # Strategy daily return (weighted sum of sector log returns)
    strat_daily = (w_daily * daily_ret).sum(axis=1)

    # Transaction costs — applied on rebalance dates (weight changes)
    w_change   = w_daily.diff().abs().sum(axis=1)
    cost_daily = w_change * transaction_cost
    strat_daily = strat_daily - cost_daily

    # Equity curves
    strat_equity = (1 + strat_daily).cumprod()
    strat_equity.name = "Strategy"

    # Benchmark
    bench_raw    = fetch_nifty50(str(daily_ret.index[0].date()),
                                 str(daily_ret.index[-1].date()))
    bench_ret    = np.log(bench_raw / bench_raw.shift(1)).reindex(daily_ret.index).dropna()
    bench_equity = (1 + bench_ret).cumprod()
    bench_equity.name = "Nifty50 B&H"

    # Align
    common       = strat_equity.index.intersection(bench_equity.index)
    strat_equity = strat_equity.loc[common]
    bench_equity = bench_equity.loc[common]
    strat_daily  = strat_daily.loc[common]
    bench_ret    = bench_ret.loc[common]

    metrics_strat = _calc_metrics(strat_daily, "Rotation Strategy")
    metrics_bench = _calc_metrics(bench_ret,   "Nifty 50 B&H")

    # Monthly turnover (avg % of portfolio replaced each month)
    monthly_turnover = w_daily.diff().abs().sum(axis=1).resample("ME").sum().mean()

    return {
        "strat_equity":   strat_equity,
        "bench_equity":   bench_equity,
        "strat_daily":    strat_daily,
        "bench_daily":    bench_ret,
        "weights_daily":  w_daily,
        "metrics_strat":  metrics_strat,
        "metrics_bench":  metrics_bench,
        "monthly_turnover": round(monthly_turnover, 4),
    }



def _calc_metrics(returns: pd.Series, label: str) -> dict:
    returns = returns.dropna()
    total   = (1 + returns).prod() - 1
    years   = len(returns) / TRADING_DAYS
    cagr    = (1 + total) ** (1 / years) - 1

    daily_rf = RISK_FREE_RATE / TRADING_DAYS
    excess   = returns - daily_rf
    sharpe   = excess.mean() / returns.std() * np.sqrt(TRADING_DAYS) if returns.std() > 0 else 0

    downside = returns[returns < daily_rf]
    sortino  = excess.mean() / downside.std() * np.sqrt(TRADING_DAYS) if len(downside) > 0 else 0

    equity   = (1 + returns).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()
    max_dd   = drawdown.min()
    calmar   = cagr / abs(max_dd) if max_dd != 0 else 0

    monthly  = returns.resample("ME").sum()
    win_rate = (monthly > 0).mean()

    return {
        "label":        label,
        "CAGR":         round(cagr * 100, 2),
        "Sharpe":       round(sharpe, 2),
        "Sortino":      round(sortino, 2),
        "Max_DD":       round(max_dd * 100, 2),
        "Calmar":       round(calmar, 2),
        "Win_Rate_Mth": round(win_rate * 100, 1),
        "Total_Return": round(total * 100, 1),
    }


def print_metrics(results: dict):
    print("\n── Backtest Results ──────────────────────────────────────────────")
    headers = ["Metric", "Rotation Strategy", "Nifty 50 B&H"]
    keys    = ["CAGR", "Sharpe", "Sortino", "Max_DD", "Calmar",
               "Win_Rate_Mth", "Total_Return"]
    labels  = ["CAGR (%)", "Sharpe", "Sortino", "Max Drawdown (%)",
               "Calmar", "Win Rate Monthly (%)", "Total Return (%)"]
    ms, mb  = results["metrics_strat"], results["metrics_bench"]
    print(f"  {'Metric':<22} {'Strategy':>16} {'B&H':>12}")
    print("  " + "─" * 52)
    for k, lbl in zip(keys, labels):
        print(f"  {lbl:<22} {ms[k]:>16} {mb[k]:>12}")
    print(f"\n  Monthly Turnover: {results['monthly_turnover']*100:.1f}%")
    print("─" * 57)


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_results(results: dict, save_path: str = "outputs/backtest.png"):
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle("Nifty Sector Rotation Strategy — Backtest", fontsize=14, fontweight="bold")

    se = results["strat_equity"]
    be = results["bench_equity"]
    sd = results["strat_daily"]
    bd = results["bench_daily"]

    # ── Equity curves ─────────────────────────────────────────────────────────
    ax = axes[0]
    ax.plot(se.index, se.values, color="#27ae60", lw=1.4, label="Rotation Strategy")
    ax.plot(be.index, be.values, color="#e74c3c", lw=1.0, ls="--", label="Nifty 50 B&H")
    ax.set_ylabel("Cumulative Return (×)")
    ax.set_title("Equity Curve")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    # ── Drawdown ──────────────────────────────────────────────────────────────
    ax = axes[1]
    strat_dd = (se - se.cummax()) / se.cummax() * 100
    bench_dd = (be - be.cummax()) / be.cummax() * 100
    ax.fill_between(strat_dd.index, strat_dd.values, 0, color="#27ae60", alpha=0.4, label="Strategy DD")
    ax.fill_between(bench_dd.index, bench_dd.values, 0, color="#e74c3c", alpha=0.3, label="B&H DD")
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown Comparison")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    # ── Rolling Sharpe (252d) ─────────────────────────────────────────────────
    ax = axes[2]
    daily_rf      = RISK_FREE_RATE / TRADING_DAYS
    roll_sharpe_s = ((sd - daily_rf).rolling(252).mean() /
                     sd.rolling(252).std() * np.sqrt(252))
    roll_sharpe_b = ((bd - daily_rf).rolling(252).mean() /
                     bd.rolling(252).std() * np.sqrt(252))
    ax.plot(roll_sharpe_s.index, roll_sharpe_s.values, color="#27ae60", lw=0.9, label="Strategy")
    ax.plot(roll_sharpe_b.index, roll_sharpe_b.values, color="#e74c3c", lw=0.9, ls="--", label="B&H")
    ax.axhline(0, color="gray", lw=0.8, ls=":")
    ax.axhline(1, color="gray", lw=0.5, ls="--", alpha=0.5)
    ax.set_ylabel("Rolling Sharpe (1yr)")
    ax.set_title("Rolling 1-Year Sharpe Ratio")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved → {save_path}")


def plot_sector_weights(results: dict, save_path: str = "outputs/sector_weights.png"):
    """Stacked area chart of monthly sector weights over time."""
    w = results["weights_daily"].resample("ME").last()
    w = w.loc[:, (w > 0).any()]          # drop sectors never selected

    colors = ["#3498db","#e74c3c","#2ecc71","#f39c12","#9b59b6",
              "#1abc9c","#e67e22","#e91e63","#00bcd4","#8bc34a"]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.stackplot(w.index, [w[c] * 100 for c in w.columns],
                 labels=w.columns.tolist(),
                 colors=colors[:len(w.columns)], alpha=0.85)
    ax.set_ylabel("Portfolio Weight (%)")
    ax.set_title("Monthly Sector Allocation — Rotation Strategy")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved → {save_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data import fetch_sectors
    from features import build_monthly_signals
    from strategy import generate_signals

    prices  = fetch_sectors()
    signals = build_monthly_signals(prices)
    weights = generate_signals(signals)

    results = run_backtest(prices, weights)
    print_metrics(results)

    # Save summary metrics
    metrics = {
        "CAGR": results["metrics_strat"]["CAGR"],
        "Sharpe": results["metrics_strat"]["Sharpe"],
        "Max_DD": results["metrics_strat"]["Max_DD"],
        "Benchmark_CAGR": results["metrics_bench"]["CAGR"],
        "Benchmark_Sharpe": results["metrics_bench"]["Sharpe"],
    }
    pd.DataFrame([metrics]).to_csv("data/backtest_summary.csv", index=False)
    print("✅ Metrics saved → data/backtest_summary.csv")

    plot_results(results)
    plot_sector_weights(results)

    # Save equity curves
    eq = pd.DataFrame({
        "strat_equity": results["strat_equity"],
        "bench_equity": results["bench_equity"],
        "strat_return": results["strat_daily"],
        "bench_return": results["bench_daily"],
    })
    eq.to_csv("data/backtest_equity.csv")
    print("✅ Equity curves saved → data/backtest_equity.csv")
    
