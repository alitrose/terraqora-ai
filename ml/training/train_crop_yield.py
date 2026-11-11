r"""Stage 2 Training, Chronological Benchmarking & Serialization for Crop Yield Prediction.

Usage:
    .\.venv\Scripts\python.exe -m ml.training.train_crop_yield
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
import xgboost as xgb

from ml.preprocessing.crop_yield_features import (
    RAW_FEATURE_COLUMNS,
    clean_crop_yield_dataframe,
)
from ml.preprocessing.crop_yield_model import (
    SegmentedYieldPredictor,
    build_pipeline,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "ml" / "datasets" / "raw" / "crop_yield.csv"
EXPECTED_CSV_SHA256 = "ab9bc356b1f8107d490376cec24450a0e2906322ad25788ab22fb32537ab1f8f"
MODEL_OUT = ROOT / "ml" / "saved_models" / "crop_yield_model.joblib"
METRICS_OUT = ROOT / "ml" / "evaluation" / "crop_yield_metrics.json"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "count": int(len(y_true)),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(root_mean_squared_error(y_true, y_pred)), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def evaluate_predictions(df: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Compute overall + unit-segmented metrics (Non-Coconut tonnes/ha vs Coconut nuts/ha)."""
    is_coconut = (df["Crop"].astype(str).str.strip() == "Coconut").to_numpy()
    non_coco_mask = ~is_coconut

    res: dict[str, Any] = {
        "overall": _regression_metrics(y_true, y_pred),
        "non_coconut_tonnes_per_ha": _regression_metrics(y_true[non_coco_mask], y_pred[non_coco_mask]),
    }
    if np.any(is_coconut):
        res["coconut_nuts_per_ha"] = _regression_metrics(y_true[is_coconut], y_pred[is_coconut])
    return res


def bootstrap_test_ci(
    y_true: np.ndarray, y_pred: np.ndarray, *, n_boot: int = 1000, seed: int = 42
) -> dict[str, dict[str, float]]:
    """Compute 95% bootstrap confidence intervals for MAE, RMSE, and R2."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    maes, rmses, r2s = [], [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_pred[idx]
        maes.append(float(mean_absolute_error(yt, yp)))
        rmses.append(float(root_mean_squared_error(yt, yp)))
        if np.var(yt) > 1e-12:
            r2s.append(float(r2_score(yt, yp)))

    def _ci(vals: list[float]) -> dict[str, float]:
        arr = np.asarray(vals, dtype=np.float64)
        return {
            "mean": round(float(arr.mean()), 4),
            "ci_low_95": round(float(np.quantile(arr, 0.025)), 4),
            "ci_high_95": round(float(np.quantile(arr, 0.975)), 4),
        }

    return {"mae": _ci(maes), "rmse": _ci(rmses), "r2": _ci(r2s)}


def run_error_analysis(test_df: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Perform slice-based residual and extreme-error analysis on held-out test set."""
    analysis_df = test_df.copy()
    analysis_df["actual_yield"] = y_true
    analysis_df["predicted_yield"] = y_pred
    analysis_df["abs_error"] = np.abs(y_true - y_pred)

    non_coco = analysis_df[analysis_df["Crop"] != "Coconut"]

    by_year = {}
    for yr, grp in non_coco.groupby("Crop_Year"):
        by_year[str(int(yr))] = _regression_metrics(
            grp["actual_yield"].to_numpy(), grp["predicted_yield"].to_numpy()
        )

    by_season = {}
    for sea, grp in non_coco.groupby("Season"):
        by_season[str(sea)] = _regression_metrics(
            grp["actual_yield"].to_numpy(), grp["predicted_yield"].to_numpy()
        )

    worst_crops = (
        non_coco.groupby("Crop")
        .agg(
            count=("abs_error", "count"),
            mean_actual=("actual_yield", "mean"),
            mae=("abs_error", "mean"),
            max_error=("abs_error", "max"),
        )
        .sort_values("mae", ascending=False)
        .head(8)
        .round(3)
        .to_dict(orient="index")
    )

    zero_yield_rows = non_coco[non_coco["actual_yield"] == 0]
    unseen_crop_rows = non_coco[non_coco["Crop"] == "Other Summer Pulses"]

    top_outliers = (
        non_coco.nlargest(5, "abs_error")[
            ["Crop", "Crop_Year", "Season", "State", "Area", "actual_yield", "predicted_yield", "abs_error"]
        ]
        .round(3)
        .to_dict(orient="records")
    )

    return {
        "non_coconut_by_year": by_year,
        "non_coconut_by_season": by_season,
        "worst_8_crops_by_mae": worst_crops,
        "zero_yield_test_rows": {
            "count": int(len(zero_yield_rows)),
            "mae": round(float(zero_yield_rows["abs_error"].mean()), 4) if len(zero_yield_rows) else None,
        },
        "cold_start_unseen_crop_other_summer_pulses": {
            "count": int(len(unseen_crop_rows)),
            "mae": round(float(unseen_crop_rows["abs_error"].mean()), 4) if len(unseen_crop_rows) else None,
        },
        "top_5_largest_non_coconut_residuals": top_outliers,
    }


def train_and_benchmark() -> dict[str, Any]:
    actual_hash = _file_sha256(RAW_CSV)
    if actual_hash != EXPECTED_CSV_SHA256:
        raise RuntimeError(f"Dataset checksum mismatch! Expected {EXPECTED_CSV_SHA256}, got {actual_hash}")

    raw_df = pd.read_csv(RAW_CSV)
    # Explicitly drop target-leaking Production before preprocessing
    feature_and_target_df = raw_df.drop(columns=["Production"])
    cleaned_df = clean_crop_yield_dataframe(feature_and_target_df, require_target=True)

    # Strict chronological split
    train_df = cleaned_df[cleaned_df["Crop_Year"] <= 2015].reset_index(drop=True)
    val_df = cleaned_df[(cleaned_df["Crop_Year"] >= 2016) & (cleaned_df["Crop_Year"] <= 2017)].reset_index(drop=True)
    test_df = cleaned_df[cleaned_df["Crop_Year"] >= 2018].reset_index(drop=True)

    X_train, y_train = train_df[RAW_FEATURE_COLUMNS], train_df["Yield"].to_numpy(dtype=np.float64)
    X_val, y_val = val_df[RAW_FEATURE_COLUMNS], val_df["Yield"].to_numpy(dtype=np.float64)
    X_test, y_test = test_df[RAW_FEATURE_COLUMNS], test_df["Yield"].to_numpy(dtype=np.float64)

    candidates: dict[str, Any] = {
        "dummy_median_segmented": SegmentedYieldPredictor(
            standard_estimator=build_pipeline(DummyRegressor(strategy="median"), scale_numeric=False),
            coconut_estimator=build_pipeline(DummyRegressor(strategy="median"), scale_numeric=False),
        ),
        "ridge_unified": build_pipeline(Ridge(alpha=10.0), scale_numeric=True, log_target=False),
        "ridge_segmented": SegmentedYieldPredictor(
            standard_estimator=build_pipeline(Ridge(alpha=10.0), scale_numeric=True, log_target=False),
            coconut_estimator=build_pipeline(Ridge(alpha=5.0), scale_numeric=True, log_target=False),
        ),
        "random_forest_segmented": SegmentedYieldPredictor(
            standard_estimator=build_pipeline(
                RandomForestRegressor(
                    n_estimators=160,
                    max_depth=20,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
                scale_numeric=False,
                log_target=False,
            ),
            coconut_estimator=build_pipeline(
                RandomForestRegressor(
                    n_estimators=120,
                    max_depth=10,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
                scale_numeric=False,
                log_target=False,
            ),
        ),
        "xgboost_unified": build_pipeline(
            xgb.XGBRegressor(
                n_estimators=400,
                max_depth=6,
                learning_rate=0.06,
                subsample=0.85,
                colsample_bytree=0.85,
                reg_lambda=2.0,
                random_state=42,
                n_jobs=-1,
                tree_method="hist",
            ),
            scale_numeric=False,
            log_target=False,
        ),
        "xgboost_segmented_native": SegmentedYieldPredictor(
            standard_estimator=build_pipeline(
                xgb.XGBRegressor(
                    n_estimators=450,
                    max_depth=6,
                    learning_rate=0.05,
                    min_child_weight=3,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_lambda=2.0,
                    random_state=42,
                    n_jobs=-1,
                    tree_method="hist",
                ),
                scale_numeric=False,
                log_target=False,
            ),
            coconut_estimator=build_pipeline(
                xgb.XGBRegressor(
                    n_estimators=180,
                    max_depth=4,
                    learning_rate=0.05,
                    min_child_weight=2,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_lambda=3.0,
                    random_state=42,
                    n_jobs=-1,
                    tree_method="hist",
                ),
                scale_numeric=False,
                log_target=False,
            ),
        ),
        "xgboost_segmented_log1p": SegmentedYieldPredictor(
            standard_estimator=build_pipeline(
                xgb.XGBRegressor(
                    n_estimators=450,
                    max_depth=6,
                    learning_rate=0.05,
                    min_child_weight=3,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_lambda=2.0,
                    random_state=42,
                    n_jobs=-1,
                    tree_method="hist",
                ),
                scale_numeric=False,
                log_target=True,
            ),
            coconut_estimator=build_pipeline(
                xgb.XGBRegressor(
                    n_estimators=180,
                    max_depth=4,
                    learning_rate=0.05,
                    min_child_weight=2,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_lambda=3.0,
                    random_state=42,
                    n_jobs=-1,
                    tree_method="hist",
                ),
                scale_numeric=False,
                log_target=True,
            ),
        ),
    }

    benchmark_results: dict[str, Any] = {}
    fitted_models: dict[str, Any] = {}

    for name, est in candidates.items():
        t0 = time.perf_counter()
        est.fit(X_train, y_train)
        train_sec = round(time.perf_counter() - t0, 3)

        val_pred = np.clip(est.predict(X_val), 0.0, None)
        test_pred = np.clip(est.predict(X_test), 0.0, None)

        val_metrics = evaluate_predictions(val_df, y_val, val_pred)
        test_metrics = evaluate_predictions(test_df, y_test, test_pred)

        # Measure serialized payload size in memory cleanly
        tmp_bytes_path = MODEL_OUT.parent / f"._tmp_{name}.joblib"
        MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(est, tmp_bytes_path, compress=3)
        size_mb = round(tmp_bytes_path.stat().st_size / (1024 * 1024), 3)
        tmp_bytes_path.unlink(missing_ok=True)

        # Measure single-row prediction latency (100 calls warm)
        sample_row = X_test.iloc[[0]]
        t_inf0 = time.perf_counter()
        for _ in range(50):
            _ = est.predict(sample_row)
        latency_ms = round(((time.perf_counter() - t_inf0) / 50.0) * 1000.0, 3)

        benchmark_results[name] = {
            "train_seconds": train_sec,
            "artifact_size_mb": size_mb,
            "single_row_latency_ms": latency_ms,
            "validation_metrics": val_metrics,
            "test_metrics": test_metrics,
        }
        fitted_models[name] = est
        print(
            f"[{name}] Val Non-Coco R2={val_metrics['non_coconut_tonnes_per_ha']['r2']:.4f} "
            f"RMSE={val_metrics['non_coconut_tonnes_per_ha']['rmse']:.4f} | "
            f"Test Non-Coco R2={test_metrics['non_coconut_tonnes_per_ha']['r2']:.4f} "
            f"RMSE={test_metrics['non_coconut_tonnes_per_ha']['rmse']:.4f} MAE={test_metrics['non_coconut_tonnes_per_ha']['mae']:.4f} | "
            f"Size={size_mb} MB"
        )

    # Select winning model strictly by Validation Non-Coconut RMSE (tie-break R2, <15MB preference)
    selectable = {k: v for k, v in benchmark_results.items() if k != "dummy_median_segmented"}
    selected_name = min(
        selectable.keys(),
        key=lambda k: (
            selectable[k]["validation_metrics"]["non_coconut_tonnes_per_ha"]["rmse"],
            selectable[k]["artifact_size_mb"],
        ),
    )
    selected_eval_model = fitted_models[selected_name]

    # Compute held-out Test bootstrap 95% CIs + Error Analysis for winning model
    test_preds_selected = np.clip(selected_eval_model.predict(X_test), 0.0, None)
    non_coco_test_mask = (test_df["Crop"] != "Coconut").to_numpy()
    test_ci_non_coco = bootstrap_test_ci(
        y_test[non_coco_test_mask], test_preds_selected[non_coco_test_mask]
    )
    error_analysis = run_error_analysis(test_df, y_test, test_preds_selected)

    # Fit production artifact with identical locked hyperparameters on full 1997-2020 cleaned dataset
    # so all 55 crops (including post-2016 'Other Summer Pulses') are supported in production.
    # All reported accuracy/R2 metrics remain strictly locked from 1997-2015 -> 2018-2020 out-of-time evaluation.
    production_model = clone(candidates[selected_name])
    production_model.fit(cleaned_df[RAW_FEATURE_COLUMNS], cleaned_df["Yield"].to_numpy(dtype=np.float64))

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(production_model, MODEL_OUT, compress=3)
    final_size_mb = round(MODEL_OUT.stat().st_size / (1024 * 1024), 3)

    ALGO_DISPLAY_NAMES = {
        "random_forest_segmented": "Segmented Random Forest Regressor (Non-Coconut tonnes/ha + Coconut nuts/ha)",
        "xgboost_segmented_native": "Segmented XGBoost Regressor (Native Target)",
        "xgboost_segmented_log1p": "Segmented XGBoost Regressor (log1p Target)",
        "ridge_segmented": "Segmented Ridge Regressor",
    }

    report = {
        "model_version": "phase5-v1.0.0",
        "selected_model_key": selected_name,
        "selected_algorithm": ALGO_DISPLAY_NAMES.get(selected_name, selected_name),
        "dataset": {
            "path": str(RAW_CSV.relative_to(ROOT)),
            "sha256": actual_hash,
            "total_rows": int(len(cleaned_df)),
            "dropped_leakage_columns": ["Production"],
        },
        "split_strategy": {
            "type": "chronological",
            "train_years": "1997-2015",
            "train_rows": int(len(train_df)),
            "val_years": "2016-2017",
            "val_rows": int(len(val_df)),
            "test_years": "2018-2020",
            "test_rows": int(len(test_df)),
            "production_refit": "Refitted locked hyperparameters on all 19,689 rows (1997-2020) after finalizing test metrics",
        },
        "selected_model_artifact": {
            "path": str(MODEL_OUT.relative_to(ROOT)),
            "size_mb": final_size_mb,
            "latency_ms": benchmark_results[selected_name]["single_row_latency_ms"],
        },
        "selected_test_metrics": benchmark_results[selected_name]["test_metrics"],
        "selected_test_bootstrap_95_ci_non_coconut": test_ci_non_coco,
        "error_analysis": error_analysis,
        "benchmarks": benchmark_results,
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSelected model: {selected_name} | Saved: {MODEL_OUT} ({final_size_mb} MB)")
    return report


if __name__ == "__main__":
    train_and_benchmark()
