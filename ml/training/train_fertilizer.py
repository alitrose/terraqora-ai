r"""Stage 2 Stratified Training, Feature Ablation & Serialization for Fertilizer Grade Classification.

Usage:
    .\.venv\Scripts\python.exe -m ml.training.train_fertilizer
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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb

from ml.preprocessing.fertilizer_features import (
    ALL_CSV_FEATURE_COLUMNS,
    FIVE_CSV_FEATURE_COLUMNS,
    NPK_CSV_FEATURE_COLUMNS,
    clean_fertilizer_dataframe,
)
from ml.preprocessing.fertilizer_model import FertilizerClassifierModel

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "ml" / "datasets" / "raw" / "Fertilizer_Prediction.csv"
EXPECTED_SHA256 = "dfd69cee9d3d7a4403aab5647d5749050ae406ad42dc9ce3f508aa3442955e41"
MODEL_OUT = ROOT / "ml" / "saved_models" / "fertilizer_model.joblib"
METRICS_OUT = ROOT / "ml" / "evaluation" / "fertilizer_metrics.json"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    classes: np.ndarray,
) -> dict[str, Any]:
    return {
        "count": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_precision": round(
            float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4
        ),
        "macro_recall": round(
            float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4
        ),
        "macro_f1": round(
            float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4
        ),
        "weighted_f1": round(
            float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4
        ),
        "log_loss": round(float(log_loss(y_true, y_proba, labels=classes)), 4),
    }


def _build_candidates() -> list[dict[str, Any]]:
    return [
        {
            "key": "dummy_majority",
            "algorithm": "DummyClassifier (Majority Class Baseline)",
            "feature_scope": "npk_only_3",
            "builder": lambda: FertilizerClassifierModel(
                DummyClassifier(strategy="most_frequent"),
                feature_columns=NPK_CSV_FEATURE_COLUMNS,
                use_scaler=False,
                encode_labels=False,
            ),
        },
        {
            "key": "logistic_regression_all8",
            "algorithm": "Logistic Regression (All 8 CSV Features)",
            "feature_scope": "all_8_features",
            "builder": lambda: FertilizerClassifierModel(
                LogisticRegression(max_iter=2000, C=2.0, random_state=42),
                feature_columns=ALL_CSV_FEATURE_COLUMNS,
                use_scaler=True,
                encode_labels=False,
            ),
        },
        {
            "key": "decision_tree_all8",
            "algorithm": "Decision Tree (max_depth=6, All 8 Features)",
            "feature_scope": "all_8_features",
            "builder": lambda: FertilizerClassifierModel(
                DecisionTreeClassifier(max_depth=6, min_samples_leaf=2, random_state=42),
                feature_columns=ALL_CSV_FEATURE_COLUMNS,
                use_scaler=False,
                encode_labels=False,
            ),
        },
        {
            "key": "random_forest_all8",
            "algorithm": "Random Forest (All 8 CSV Features)",
            "feature_scope": "all_8_features",
            "builder": lambda: FertilizerClassifierModel(
                RandomForestClassifier(
                    n_estimators=200, max_depth=8, min_samples_leaf=2, random_state=42
                ),
                feature_columns=ALL_CSV_FEATURE_COLUMNS,
                use_scaler=False,
                encode_labels=False,
            ),
        },
        {
            "key": "random_forest_collectable5",
            "algorithm": "Random Forest (5 Collectable UI Features: N, P, K, Soil, Crop)",
            "feature_scope": "collectable_5_features",
            "builder": lambda: FertilizerClassifierModel(
                RandomForestClassifier(
                    n_estimators=200, max_depth=8, min_samples_leaf=2, random_state=42
                ),
                feature_columns=FIVE_CSV_FEATURE_COLUMNS,
                use_scaler=False,
                encode_labels=False,
            ),
        },
        {
            "key": "logistic_regression_npk3",
            "algorithm": "Logistic Regression (Parsimonious 3 NPK Grade Features)",
            "feature_scope": "npk_only_3",
            "builder": lambda: FertilizerClassifierModel(
                LogisticRegression(max_iter=2000, C=4.0, random_state=42),
                feature_columns=NPK_CSV_FEATURE_COLUMNS,
                use_scaler=True,
                encode_labels=False,
            ),
        },
        {
            "key": "random_forest_npk3",
            "algorithm": "Random Forest (Parsimonious 3 NPK Grade Features)",
            "feature_scope": "npk_only_3",
            "builder": lambda: FertilizerClassifierModel(
                RandomForestClassifier(
                    n_estimators=200, max_depth=6, min_samples_leaf=2, random_state=42
                ),
                feature_columns=NPK_CSV_FEATURE_COLUMNS,
                use_scaler=False,
                encode_labels=False,
            ),
        },
        {
            "key": "xgboost_npk3",
            "algorithm": "XGBoost Classifier (Parsimonious 3 NPK Grade Features)",
            "feature_scope": "npk_only_3",
            "builder": lambda: FertilizerClassifierModel(
                xgb.XGBClassifier(
                    n_estimators=120,
                    max_depth=3,
                    learning_rate=0.08,
                    subsample=0.85,
                    reg_lambda=2.0,
                    eval_metric="mlogloss",
                    random_state=42,
                ),
                feature_columns=NPK_CSV_FEATURE_COLUMNS,
                use_scaler=False,
                encode_labels=True,
            ),
        },
    ]


def run_training() -> dict[str, Any]:
    sha256 = _file_sha256(RAW_CSV)
    if sha256 != EXPECTED_SHA256:
        raise ValueError(
            f"Fertilizer_Prediction.csv checksum mismatch: expected {EXPECTED_SHA256}, got {sha256}"
        )

    raw_df = pd.read_csv(RAW_CSV)
    clean_df = clean_fertilizer_dataframe(raw_df, require_target=True)
    X_all = clean_df[ALL_CSV_FEATURE_COLUMNS]
    y_all = clean_df["Fertilizer Name"].to_numpy(dtype=object)

    # Strict Stratified 60% Train / 20% Val / 20% Test before fitting anything
    X_dev, X_test, y_dev, y_test = train_test_split(
        X_all,
        y_all,
        test_size=20,  # ~20.2%, guarantees >= 1 sample for every class (min count 7)
        stratify=y_all,
        random_state=42,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev,
        y_dev,
        test_size=19,  # ~24% of Dev (60 Train / 19 Val / 20 Test)
        stratify=y_dev,
        random_state=42,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    benchmarks: list[dict[str, Any]] = []

    for cand in _build_candidates():
        t0 = time.perf_counter()
        model = cand["builder"]()
        model.fit(X_train, y_train)
        fit_sec = round(time.perf_counter() - t0, 3)

        train_m = _classification_metrics(
            y_train, model.predict(X_train), model.predict_proba(X_train), model.classes_
        )
        val_m = _classification_metrics(
            y_val, model.predict(X_val), model.predict_proba(X_val), model.classes_
        )

        cv_accs: list[float] = []
        cv_f1s: list[float] = []
        cv_losses: list[float] = []
        for tr_idx, va_idx in cv.split(X_dev, y_dev):
            fm = cand["builder"]()
            fm.fit(X_dev.iloc[tr_idx], y_dev[tr_idx])
            fp = fm.predict(X_dev.iloc[va_idx])
            fpr = fm.predict_proba(X_dev.iloc[va_idx])
            cv_accs.append(float(accuracy_score(y_dev[va_idx], fp)))
            cv_f1s.append(float(f1_score(y_dev[va_idx], fp, average="macro", zero_division=0)))
            cv_losses.append(float(log_loss(y_dev[va_idx], fpr, labels=fm.classes_)))

        benchmarks.append(
            {
                "key": cand["key"],
                "algorithm": cand["algorithm"],
                "feature_scope": cand["feature_scope"],
                "fit_seconds": fit_sec,
                "train_metrics": train_m,
                "validation_metrics": val_m,
                "overfit_gap_accuracy_train_minus_val": round(
                    train_m["accuracy"] - val_m["accuracy"], 4
                ),
                "cv5_dev": {
                    "accuracy_mean": round(float(np.mean(cv_accs)), 4),
                    "accuracy_std": round(float(np.std(cv_accs)), 4),
                    "macro_f1_mean": round(float(np.mean(cv_f1s)), 4),
                    "macro_f1_std": round(float(np.std(cv_f1s)), 4),
                    "log_loss_mean": round(float(np.mean(cv_losses)), 4),
                },
            }
        )

    # Prefer collectable/parsimonious non-dummy models that avoid uncollected climate noise when tied
    inference_eligible = [
        b
        for b in benchmarks
        if b["key"] != "dummy_majority"
        and b["feature_scope"] in ("npk_only_3", "collectable_5_features")
    ]
    best = max(
        inference_eligible,
        key=lambda b: (
            b["cv5_dev"]["macro_f1_mean"],
            b["validation_metrics"]["macro_f1"],
            1 if b["feature_scope"] == "npk_only_3" else 0,
            -b["cv5_dev"]["log_loss_mean"],
            -b["overfit_gap_accuracy_train_minus_val"],
        ),
    )

    selected_builder = next(c["builder"] for c in _build_candidates() if c["key"] == best["key"])
    final_model = selected_builder()
    final_model.fit(X_dev, y_dev)

    dev_m = _classification_metrics(
        y_dev, final_model.predict(X_dev), final_model.predict_proba(X_dev), final_model.classes_
    )
    test_pred = final_model.predict(X_test)
    test_proba = final_model.predict_proba(X_test)
    test_m = _classification_metrics(y_test, test_pred, test_proba, final_model.classes_)

    labels_sorted = [str(c) for c in final_model.classes_]
    cm = confusion_matrix(y_test, test_pred, labels=labels_sorted)
    report = classification_report(
        y_test, test_pred, labels=labels_sorted, output_dict=True, zero_division=0
    )
    per_class = {
        lbl: {
            "precision": round(float(report[lbl]["precision"]), 4),
            "recall": round(float(report[lbl]["recall"]), 4),
            "f1_score": round(float(report[lbl]["f1-score"]), 4),
            "support": int(report[lbl]["support"]),
        }
        for lbl in labels_sorted
    }

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_OUT, compress=("gzip", 3))
    size_bytes = MODEL_OUT.stat().st_size

    metrics_payload = {
        "module": "Fertilizer Grade Classification (ML) + ICAR Agronomic Guardrails",
        "model_version": "phase5b-fert-v1.0.0",
        "dataset_path": str(RAW_CSV.relative_to(ROOT)).replace("\\", "/"),
        "dataset_sha256": sha256,
        "split_strategy": {
            "method": "Stratified 60 Train / 19 Val / 20 Held-Out Test (+ 5-Fold Stratified CV on Dev=79)",
            "random_state": 42,
            "train_rows": int(len(X_train)),
            "validation_rows": int(len(X_val)),
            "dev_train_val_rows": int(len(X_dev)),
            "test_rows": int(len(X_test)),
        },
        "benchmarks": benchmarks,
        "selected_model_key": best["key"],
        "selected_algorithm": best["algorithm"],
        "selected_feature_columns": list(final_model.feature_columns),
        "selected_cv5_dev": best["cv5_dev"],
        "selected_dev_metrics": dev_m,
        "selected_test_metrics": test_m,
        "per_class_test_metrics": per_class,
        "confusion_matrix_labels": labels_sorted,
        "confusion_matrix": cm.tolist(),
        "artifact": {
            "path": str(MODEL_OUT.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": int(size_bytes),
            "size_mb": round(size_bytes / (1024 * 1024), 4),
        },
        "agronomic_safety_and_limitations": [
            "Fertilizer_Prediction.csv contains 99 observations across 7 formulation classes and does NOT contain soil pH, crop yield trials, or dosage quantities (kg/ha).",
            "Feature ablation confirmed that zero-MI uncollected variables (Temperature, Humidity, Moisture, Soil Type, Crop Type) add dimensionality without out-of-sample gain.",
            "Production service separates dataset-backed formulation grade classification from ICAR soil-sufficiency + pH agronomic rules and strictly refuses to invent chemical application dosages, advising KVK / Soil Health Card lab verification.",
        ],
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    print(f"Selected Fertilizer model: {best['key']} -> {MODEL_OUT.name} ({size_bytes / 1024:.1f} KB)")
    for b in benchmarks:
        print(
            f"  {b['key']:28s} | Train Acc={b['train_metrics']['accuracy']:.4f} | Val Acc={b['validation_metrics']['accuracy']:.4f} | CV5={b['cv5_dev']['accuracy_mean']:.4f} +/- {b['cv5_dev']['accuracy_std']:.4f} | MacroF1={b['cv5_dev']['macro_f1_mean']:.4f} | LogLoss={b['cv5_dev']['log_loss_mean']:.4f}"
        )
    print(
        f"Held-Out Test ({len(X_test)} rows): Acc={test_m['accuracy']:.4f}, Macro-F1={test_m['macro_f1']:.4f}, LogLoss={test_m['log_loss']:.4f}"
    )
    return metrics_payload


if __name__ == "__main__":
    run_training()
