from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone

from inventory.models import Inventory, InventoryHistory

from .preprocessing import FEATURE_COLUMNS


@dataclass(frozen=True)
class PredictionResult:
    predicted_demand: float
    avg_daily_demand_7d: float
    predicted_remaining_stock: float
    stockout_probability: float  # 0-1
    predicted_stockout_date: Optional[str]
    risk: str  # LOW|MEDIUM|HIGH
    model_info: Dict


def _model_paths() -> Tuple[Path, Path]:
    base = Path(settings.BASE_DIR) / "ml" / "models"
    return base / "stock_demand_model.joblib", base / "stock_demand_model.meta.json"


def _load_model():
    model_path, meta_path = _model_paths()
    if not model_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            "Trained model not found. Run `python manage.py train_stock_model` first."
        )
    payload = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "model" in payload:
        model = payload["model"]
        feature_columns = payload.get("feature_columns", meta.get("feature_columns", FEATURE_COLUMNS))
    else:
        model = payload
        feature_columns = meta.get("feature_columns", FEATURE_COLUMNS)
    return model, meta, feature_columns


def _latest_daily_series(pharmacy_id: int, medicine_id: int, days: int = 14) -> pd.DataFrame:
    now = timezone.now()
    qs = (
        InventoryHistory.objects.filter(
            pharmacy_id=pharmacy_id,
            medicine_id=medicine_id,
            timestamp__gte=now - timedelta(days=days),
        )
        .values("timestamp", "quantity")
        .order_by("timestamp")
    )
    df = pd.DataFrame.from_records(list(qs))
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["day"] = df["timestamp"].dt.floor("D")
    df = df.sort_values("timestamp")
    df = df.groupby("day", as_index=False).agg(quantity=("quantity", "last"))
    df = df.sort_values("day").reset_index(drop=True)
    return df


def _infer_daily_demand(df_daily: pd.DataFrame) -> pd.Series:
    if df_daily.empty:
        return pd.Series(dtype=float)
    prev = df_daily["quantity"].shift(1)
    delta = (prev - df_daily["quantity"]).fillna(0)
    return delta.clip(lower=0).astype(float)


def predict_stock(
    *,
    pharmacy_id: int,
    medicine_id: int,
    horizon_days: int = 7,
) -> PredictionResult:
    model, meta, feature_columns = _load_model()

    inventory = Inventory.objects.filter(pharmacy_id=pharmacy_id, medicine_id=medicine_id).first()
    current_stock = float(inventory.quantity) if inventory else 0.0

    df_daily = _latest_daily_series(pharmacy_id, medicine_id, days=max(14, horizon_days + 7))
    demand = _infer_daily_demand(df_daily)
    avg_7 = float(demand.tail(7).mean()) if len(demand) else 0.0
    demand_1d = float(demand.iloc[-1]) if len(demand) else 0.0
    avg_3 = float(demand.tail(3).mean()) if len(demand) else 0.0
    demand_max_7d = float(demand.tail(7).max()) if len(demand) else 0.0
    demand_volatility_7d = float(demand.tail(7).std()) if len(demand) > 1 else 0.0
    stock_change_1d = (
        float(df_daily["quantity"].iloc[-1] - df_daily["quantity"].iloc[-2])
        if len(df_daily) > 1
        else 0.0
    )
    restock_1d = 1 if stock_change_1d > 0 else 0
    days_since_restock = 0.0
    if len(df_daily) > 1:
        quantities = df_daily["quantity"].astype(float).tolist()
        days_since_restock = 0.0
        for idx in range(len(quantities) - 1, 0, -1):
            if quantities[idx] > quantities[idx - 1]:
                break
            days_since_restock += 1.0

    # Simple trend proxy: last 7 demand points slope.
    if len(demand) >= 2:
        x = np.arange(len(demand.tail(7)), dtype=float)
        y = demand.tail(7).to_numpy(dtype=float)
        x = x - x.mean()
        denom = (x ** 2).sum()
        trend = float((x * (y - y.mean())).sum() / denom) if denom else 0.0
    else:
        trend = 0.0

    day_of_week = int(timezone.now().weekday())

    row = {
        "current_stock": current_stock,
        "stock_change_1d": stock_change_1d,
        "demand_1d": demand_1d,
        "demand_avg_3d": avg_3,
        "demand_avg_7d": avg_7,
        "demand_max_7d": demand_max_7d,
        "demand_volatility_7d": demand_volatility_7d if not np.isnan(demand_volatility_7d) else 0.0,
        "demand_trend_7d": trend,
        "restock_1d": restock_1d,
        "days_since_restock": days_since_restock,
        "day_of_week": day_of_week,
        "is_weekend": 1 if day_of_week in [5, 6] else 0,
        "pharmacy_id": pharmacy_id,
        "medicine_id": medicine_id,
    }
    X = pd.DataFrame([row], columns=feature_columns)
    predicted_next = float(model.predict(X)[0])
    predicted_next = max(0.0, predicted_next)

    predicted_remaining = max(0.0, current_stock - predicted_next)

    # Uncertainty proxy: use MAE of chosen model (from training metrics).
    mae = float(meta.get("metrics", {}).get(meta.get("best_model", ""), {}).get("mae", 5.0))
    sigma = max(1.0, mae * 1.25)

    # Monte Carlo: simulate horizon-days cumulative demand and stock-out probability.
    rng = np.random.default_rng(1337)
    sims = 250
    stockouts = 0
    stockout_day_sum = 0
    for _ in range(sims):
        stock = current_stock
        stockout_day = None
        for day in range(1, horizon_days + 1):
            # Demand >= 0.
            d = float(rng.normal(loc=predicted_next, scale=sigma))
            d = max(0.0, d)
            stock -= d
            if stock <= 0 and stockout_day is None:
                stockout_day = day
                break
        if stockout_day is not None:
            stockouts += 1
            stockout_day_sum += stockout_day

    prob = stockouts / sims if sims else 0.0
    if prob >= 0.7:
        risk = "HIGH"
    elif prob >= 0.35:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    predicted_date = None
    if stockouts:
        avg_day = int(round(stockout_day_sum / stockouts))
        predicted_date = (timezone.now().date() + timedelta(days=avg_day)).isoformat()

    return PredictionResult(
        predicted_demand=round(predicted_next, 2),
        avg_daily_demand_7d=round(avg_7, 2),
        predicted_remaining_stock=round(predicted_remaining, 2),
        stockout_probability=round(prob, 4),
        predicted_stockout_date=predicted_date,
        risk=risk,
        model_info={
            "best_model": meta.get("best_model"),
            "trained_at": meta.get("trained_at"),
            "history_start": meta.get("history_start"),
            "history_end": meta.get("history_end"),
            "metrics": meta.get("metrics", {}),
        },
    )
