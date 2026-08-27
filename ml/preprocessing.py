from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd

from inventory.models import InventoryHistory


FEATURE_COLUMNS = [
    "current_stock",
    "stock_change_1d",
    "demand_1d",
    "demand_avg_3d",
    "demand_avg_7d",
    "demand_max_7d",
    "demand_volatility_7d",
    "demand_trend_7d",
    "restock_1d",
    "days_since_restock",
    "day_of_week",
    "is_weekend",
    "pharmacy_id",
    "medicine_id",
]


@dataclass(frozen=True)
class PreparedDataset:
    X: pd.DataFrame
    y: pd.Series
    observed_at: pd.Series
    feature_columns: List[str]


def _daily_timeseries_df() -> pd.DataFrame:
    """
    Returns one row per (pharmacy, medicine, day) with end-of-day stock.
    This gives a consistent daily sampling frequency for ML.
    """
    qs = InventoryHistory.objects.all().values(
        "pharmacy_id", "medicine_id", "quantity", "timestamp"
    )
    df = pd.DataFrame.from_records(list(qs))
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["day"] = df["timestamp"].dt.floor("D")
    df = df.sort_values(["pharmacy_id", "medicine_id", "timestamp"])

    # Take the last recorded stock snapshot per day.
    df = (
        df.groupby(["pharmacy_id", "medicine_id", "day"], as_index=False)
        .agg(quantity=("quantity", "last"))
    )
    df = df.sort_values(["pharmacy_id", "medicine_id", "day"]).reset_index(drop=True)
    return df


def _trend(values: np.ndarray) -> float:
    """Simple slope of a 7-point series (least squares); returns 0 if not enough data."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = values.astype(float)
    x = x - x.mean()
    denom = (x ** 2).sum()
    if denom == 0:
        return 0.0
    return float((x * (y - y.mean())).sum() / denom)


def prepare_supervised_dataset() -> PreparedDataset:
    """
    Build a supervised dataset to predict *next-day demand* per pharmacy+medicine.

    Demand is inferred from decreases in stock between two consecutive days.
    Increases are treated as restocks and do not count as demand.
    """
    df = _daily_timeseries_df()
    if df.empty:
        return PreparedDataset(
            X=pd.DataFrame(columns=FEATURE_COLUMNS),
            y=pd.Series(dtype=float),
            observed_at=pd.Series(dtype="datetime64[ns, UTC]"),
            feature_columns=list(FEATURE_COLUMNS),
        )

    df["prev_qty"] = df.groupby(["pharmacy_id", "medicine_id"])["quantity"].shift(1)
    df["delta"] = (df["prev_qty"] - df["quantity"]).fillna(0)
    df["demand"] = df["delta"].clip(lower=0)
    df["stock_change_1d"] = (df["quantity"] - df["prev_qty"]).fillna(0).astype(float)
    df["restock_1d"] = (df["stock_change_1d"] > 0).astype(int)

    # Rolling features per series.
    grp = df.groupby(["pharmacy_id", "medicine_id"], group_keys=False)
    df["demand_1d"] = df["demand"]
    df["demand_avg_3d"] = (
        grp["demand"].rolling(3, min_periods=1).mean().reset_index(level=[0, 1], drop=True)
    )
    df["demand_avg_7d"] = (
        grp["demand"].rolling(7, min_periods=1).mean().reset_index(level=[0, 1], drop=True)
    )
    df["demand_max_7d"] = (
        grp["demand"].rolling(7, min_periods=1).max().reset_index(level=[0, 1], drop=True)
    )
    df["demand_volatility_7d"] = (
        grp["demand"]
        .rolling(7, min_periods=1)
        .std()
        .reset_index(level=[0, 1], drop=True)
        .fillna(0.0)
    )

    # Trend over last 7 demand points.
    def _trend_apply(s: pd.Series) -> pd.Series:
        out = []
        arr = s.to_numpy(dtype=float)
        for i in range(len(arr)):
            start = max(0, i - 6)
            out.append(_trend(arr[start : i + 1]))
        return pd.Series(out, index=s.index)

    df["demand_trend_7d"] = grp["demand"].apply(_trend_apply)

    df["day_of_week"] = pd.to_datetime(df["day"]).dt.dayofweek.astype(int)
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["current_stock"] = df["quantity"].astype(float)
    df["days_since_restock"] = (
        grp["restock_1d"]
        .apply(lambda s: s.groupby(s.eq(1).cumsum()).cumcount())
        .astype(float)
    )

    # Target: next day's demand
    df["target_next_demand"] = grp["demand"].shift(-1)
    df = df.dropna(subset=["target_next_demand"]).copy()
    df = df.sort_values(["day", "pharmacy_id", "medicine_id"]).reset_index(drop=True)

    X = df[FEATURE_COLUMNS].copy()
    y = df["target_next_demand"].astype(float)
    observed_at = pd.to_datetime(df["day"], utc=True)
    return PreparedDataset(
        X=X,
        y=y,
        observed_at=observed_at,
        feature_columns=list(FEATURE_COLUMNS),
    )


def time_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    observed_at: pd.Series,
    test_ratio: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Time-aware split by date boundary: the most recent N% of unique dates become
    the test set, ensuring no future dates leak into training.
    """
    if X.empty:
        return X, X, y, y

    split_df = X.copy()
    split_df["_target"] = y.to_numpy()
    split_df["_observed_at"] = pd.to_datetime(observed_at, utc=True)
    split_df = split_df.sort_values(["_observed_at", "pharmacy_id", "medicine_id"]).reset_index(drop=True)

    unique_dates = split_df["_observed_at"].dt.normalize().drop_duplicates().sort_values().tolist()
    if len(unique_dates) < 2:
        raise RuntimeError(
            "Not enough distinct history dates to create a time-aware train/test split."
        )

    n_test_dates = max(1, int(round(len(unique_dates) * test_ratio)))
    n_test_dates = min(n_test_dates, len(unique_dates) - 1)
    cutoff_dates = set(unique_dates[-n_test_dates:])

    test_mask = split_df["_observed_at"].dt.normalize().isin(cutoff_dates)
    train_mask = ~test_mask
    if not train_mask.any() or not test_mask.any():
        raise RuntimeError(
            "Unable to create a non-empty time-aware split from InventoryHistory data."
        )

    X_train = split_df.loc[train_mask, FEATURE_COLUMNS].copy()
    y_train = split_df.loc[train_mask, "_target"].astype(float).copy()
    X_test = split_df.loc[test_mask, FEATURE_COLUMNS].copy()
    y_test = split_df.loc[test_mask, "_target"].astype(float).copy()
    return X_train, X_test, y_train, y_test
