from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from django.conf import settings

from .preprocessing import prepare_supervised_dataset, time_train_test_split


@dataclass(frozen=True)
class TrainResult:
    best_model_name: str
    metrics: Dict[str, Dict[str, float]]
    model_path: Path
    metadata_path: Path


def _models():
    return {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            random_state=1337,
            max_depth=12,
            min_samples_leaf=2,
            n_jobs=-1,
        ),
    }


def _score_model(y_true, preds) -> Dict[str, float]:
    r2 = float(r2_score(y_true, preds)) if len(y_true) > 1 else 0.0
    return {
        "mae": float(mean_absolute_error(y_true, preds)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, preds))),
        "r2": r2,
    }


def train_and_save(output_dir: Optional[Path] = None) -> TrainResult:
    output_dir = output_dir or Path(settings.BASE_DIR) / "ml" / "models"
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = prepare_supervised_dataset()
    if dataset.X.empty:
        raise RuntimeError(
            "Not enough InventoryHistory data to train. Run `python manage.py seed_demo_data` first."
        )

    # Time-aware split (simple global ordering; fine for demo-sized dataset).
    X_train, X_test, y_train, y_test = time_train_test_split(
        dataset.X,
        dataset.y,
        dataset.observed_at,
        test_ratio=0.2,
    )

    metrics: Dict[str, Dict[str, float]] = {}
    fitted = {}

    for name, model in _models().items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        metrics[name] = _score_model(y_test, preds)
        fitted[name] = model

    best_name = min(metrics.keys(), key=lambda k: (metrics[k]["rmse"], metrics[k]["mae"]))
    best_model = fitted[best_name]

    model_path = output_dir / "stock_demand_model.joblib"
    metadata_path = output_dir / "stock_demand_model.meta.json"

    joblib.dump(
        {
            "model": best_model,
            "feature_columns": dataset.feature_columns,
            "best_model": best_name,
        },
        model_path,
    )
    metadata = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "best_model": best_name,
        "feature_columns": dataset.feature_columns,
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "total_samples": int(len(dataset.X)),
        "history_start": dataset.observed_at.min().date().isoformat(),
        "history_end": dataset.observed_at.max().date().isoformat(),
        "metrics": metrics,
        "notes": (
            "Model predicts next-day inferred demand from InventoryHistory-derived daily stock series. "
            "This is decision-support only; predictions may be inaccurate."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return TrainResult(
        best_model_name=best_name,
        metrics=metrics,
        model_path=model_path,
        metadata_path=metadata_path,
    )
