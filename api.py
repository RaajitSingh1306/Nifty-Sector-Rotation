"""
api.py
------
FastAPI endpoints for P3: Nifty Sector Rotation.

Endpoints:
    GET /signals/current    — current month sector allocation
    GET /backtest/summary   — CAGR, Sharpe, Max DD vs Nifty 50 B&H

Usage:
    uvicorn api:app --reload
"""
from fastapi import FastAPI, HTTPException
from pathlib import Path
import pandas as pd

app = FastAPI(title="Nifty Sector Rotation API", version="1.0")

WEIGHTS_PATH = Path("data/monthly_weights.csv")
BACKTEST_PATH = Path("data/backtest_summary.csv")


@app.get("/")
def health():
    return {"status": "ok", "service": "nifty-sector-rotation"}


@app.get("/signals/current")
def current_signals():
    if not WEIGHTS_PATH.exists():
        raise HTTPException(503, "Run pipeline first: python run.py")
    weights = pd.read_csv(WEIGHTS_PATH, index_col=0)
    latest = weights.iloc[-1].to_dict()
    return {"month": weights.index[-1], "allocation": latest}


@app.get("/backtest/summary")
def backtest_summary():
    if not BACKTEST_PATH.exists():
        raise HTTPException(503, "Run pipeline first: python run.py")
    summary = pd.read_csv(BACKTEST_PATH, index_col=0)
    return summary.to_dict()
