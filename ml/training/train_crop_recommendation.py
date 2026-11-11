r"""Stage 2 Stratified Training, Benchmarking & Serialization for Crop Recommendation.

Usage:
    .\.venv\Scripts\python.exe -m ml.training.train_crop_recommendation
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
    top_k_accuracy_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb

from ml.preprocessing.crop_rec_features import (
    RAW_CROP_REC_FEATURES,
    clean_crop_rec_dataframe,
)
from ml.preprocessing.crop_rec_model import CropRecommendationModel

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "ml" / "datasets" / "raw" / "Crop_recommendation.csv"
EXPECTED_SHA256 = "54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e"
MODEL_OUT = ROOT / "ml" / "saved_models" / "crop_recommendation_model.joblib"
METRICS_OUT = ROOT / "ml" / "evaluation" / "crop_rec_metrics.json"


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
        "top_3_accuracy": round(
            float(top_k_accuracy_score(y_true, y_proba, k=3, labels=classes)), 4
        ),
        "log_loss": round(float(log_loss(y_true, y_proba, labels=classes)), 4),
    }


def _bootstrap_test_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    accs: list[float] = []
    f1s: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_pred[idx]
        accs.append(float(accuracy_score(yt, yp)))
        f1s.append(float(f1_score(yt, yp, average="macro", zero_division=0)))

    def _ci(vals: list[float]) -> dict[str, float]:
        arr = np.asarray(vals, dtype=np.float64)
        return {
            "mean": round(float(arr.mean()), 4),
            "ci_low_95": round(float(np.quantile(arr, 0.025)), 4),
            "ci_high_95": round(float(np.quantile(arr, 0.975)), 4),
        }

    return {"accuracy": _ci(accs), "macro_f1": _ci(f1s)}


def _build_candidates() -> list[dict[str, Any]]:
    return [
        {
            "key": "dummy_majority",
            "algorithm": "DummyClassifier (Majority Class Baseline)",
            "builder": lambda: CropRecommendationModel(
                DummyClassifier(strategy="most_frequent"),
                use_scaler=False,
                include_engineered=False,
                encode_labels=False,
            ),
        },
        {
            "key": "logistic_regression_scaled",
            "algorithm": "Logistic Regression (StandardScaler + Ratios)",
            "builder": lambda: CropRecommendationModel(
                LogisticRegression(max_iter=2000, C=2.0, random_state=42),
                use_scaler=True,
                include_engineered=True,
                encode_labels=False,
            ),
        },
        {
            "key": "gaussian_nb_raw",
            "algorithm": "Gaussian Naive Bayes (7 Raw Features)",
            "builder": lambda: CropRecommendationModel(
                GaussianNB(),
                use_scaler=False,
                include_engineered=False,
                encode_labels=False,
            ),
        },
        {
            "key": "decision_tree_reg",
            "algorithm": "Decision Tree Classifier (max_depth=10, min_samples_leaf=3)",
            "builder": lambda: CropRecommendationModel(
                DecisionTreeClassifier(
                    max_depth=10, min_samples_leaf=3, random_state=42
                ),
                use_scaler=False,
                include_engineered=True,
                encode_labels=False,
            ),
        },
        {
            "key": "random_forest_raw",
            "algorithm": "Random Forest Classifier (7 Raw Features)",
            "builder": lambda: CropRecommendationModel(
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=14,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
                use_scaler=False,
                include_engineered=False,
                encode_labels=False,
            ),
        },
        {
            "key": "random_forest_engineered",
            "algorithm": "Random Forest Classifier (Raw + Agronomic NPK/Moisture Ratios)",
            "builder": lambda: CropRecommendationModel(
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=14,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
                use_scaler=False,
                include_engineered=True,
                encode_labels=False,
            ),
        },
        {
            "key": "xgboost_classifier",
            "algorithm": "XGBoost Multiclass Classifier (Regularized)",
            "builder": lambda: CropRecommendationModel(
                xgb.XGBClassifier(
                    n_estimators=220,
                    max_depth=4,
                    learning_rate=0.07,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_lambda=2.0,
                    eval_metric="mlogloss",
                    random_state=42,
                    n_jobs=-1,
                ),
                use_scaler=False,
                include_engineered=True,
                encode_labels=True,
            ),
        },
    ]


def run_training() -> dict[str, Any]:
    sha256 = _file_sha256(RAW_CSV)
    if sha256 != EXPECTED_SHA256:
        raise ValueError(
            f"Crop_recommendation.csv checksum mismatch: expected {EXPECTED_SHA256}, got {sha256}"
        )

    raw_df = pd.read_csv(RAW_CSV)
    clean_df = clean_crop_rec_dataframe(raw_df, require_target=True)
    X_all = clean_df[RAW_CROP_REC_FEATURES]
    y_all = clean_df["label"].to_numpy(dtype=object)

    # Strict Stratified 60% Train / 20% Validation / 20% Held-Out Test BEFORE fitting anything
    X_dev, X_test, y_dev, y_test = train_test_split(
        X_all,
        y_all,
        test_size=0.20,
        stratify=y_all,
        random_state=42,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_dev,
        y_dev,
        test_size=0.25,  # 0.25 * 0.80 = 0.20 of full dataset
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

        train_pred = model.predict(X_train)
        train_proba = model.predict_proba(X_train)
        val_pred = model.predict(X_val)
        val_proba = model.predict_proba(X_val)

        train_m = _classification_metrics(y_train, train_pred, train_proba, model.classes_)
        val_m = _classification_metrics(y_val, val_pred, val_proba, model.classes_)

        # 5-fold stratified CV strictly inside Dev (Train + Val, never touching Test)
        cv_accs: list[float] = []
        cv_f1s: list[float] = []
        cv_losses: list[float] = []
        for tr_idx, va_idx in cv.split(X_dev, y_dev):
            fold_model = cand["builder"]()
            fold_model.fit(X_dev.iloc[tr_idx], y_dev[tr_idx])
            fp = fold_model.predict(X_dev.iloc[va_idx])
            fpr = fold_model.predict_proba(X_dev.iloc[va_idx])
            cv_accs.append(float(accuracy_score(y_dev[va_idx], fp)))
            cv_f1s.append(float(f1_score(y_dev[va_idx], fp, average="macro", zero_division=0)))
            cv_losses.append(float(log_loss(y_dev[va_idx], fpr, labels=fold_model.classes_)))

        benchmarks.append(
            {
                "key": cand["key"],
                "algorithm": cand["algorithm"],
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

    # Select best candidate strictly by Validation + 5-Fold CV macro_f1 then lowest log_loss
    non_dummy = [b for b in benchmarks if b["key"] != "dummy_majority"]
    best = max(
        non_dummy,
        key=lambda b: (
            b["cv5_dev"]["macro_f1_mean"],
            b["validation_metrics"]["macro_f1"],
            -b["cv5_dev"]["log_loss_mean"],
            -b["overfit_gap_accuracy_train_minus_val"],
        ),
    )

    selected_builder = next(c["builder"] for c in _build_candidates() if c["key"] == best["key"])
    final_model = selected_builder()
    final_model.fit(X_dev, y_dev)

    # Evaluate once on untouched Held-Out Test (440 rows = 20/crop)
    dev_pred = final_model.predict(X_dev)
    dev_proba = final_model.predict_proba(X_dev)
    test_pred = final_model.predict(X_test)
    test_proba = final_model.predict_proba(X_test)

    dev_metrics = _classification_metrics(y_dev, dev_pred, dev_proba, final_model.classes_)
    test_metrics = _classification_metrics(y_test, test_pred, test_proba, final_model.classes_)
    test_ci = _bootstrap_test_ci(y_test, test_pred, n_boot=1000, seed=42)

    labels_sorted = [str(c) for c in final_model.classes_]
    cm = confusion_matrix(y_test, test_pred, labels=labels_sorted)
    per_class_report = classification_report(
        y_test,
        test_pred,
        labels=labels_sorted,
        output_dict=True,
        zero_division=0,
    )
    per_class_clean = {
        crop: {
            "precision": round(float(per_class_report[crop]["precision"]), 4),
            "recall": round(float(per_class_report[crop]["recall"]), 4),
            "f1_score": round(float(per_class_report[crop]["f1-score"]), 4),
            "support": int(per_class_report[crop]["support"]),
        }
        for crop in labels_sorted
    }

    misclassified_cases = []
    for pos in np.where(y_test != test_pred)[0]:
        row_x = X_test.iloc[int(pos)]
        top2_idx = np.argsort(test_proba[int(pos)])[::-1][:2]
        misclassified_cases.append(
            {
                "actual": str(y_test[int(pos)]),
                "predicted": str(test_pred[int(pos)]),
                "top2": [
                    {
                        "crop": str(final_model.classes_[i]),
                        "prob": round(float(test_proba[int(pos), i]), 4),
                    }
                    for i in top2_idx
                ],
                "features": {col: round(float(row_x[col]), 2) for col in RAW_CROP_REC_FEATURES},
            }
        )

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_OUT, compress=("gzip", 3))
    size_bytes = MODEL_OUT.stat().st_size

    metrics_payload = {
        "module": "Crop Recommendation (22 Crops)",
        "model_version": "phase5b-crop-v1.0.0",
        "dataset_path": str(RAW_CSV.relative_to(ROOT)).replace("\\", "/"),
        "dataset_sha256": sha256,
        "split_strategy": {
            "method": "Stratified 60% Train / 20% Validation / 20% Held-Out Test (+ 5-Fold Stratified CV on Train+Val)",
            "random_state": 42,
            "train_rows": int(len(X_train)),
            "validation_rows": int(len(X_val)),
            "dev_train_val_rows": int(len(X_dev)),
            "test_rows": int(len(X_test)),
            "samples_per_crop_in_test": 20,
        },
        "benchmarks": benchmarks,
        "selected_model_key": best["key"],
        "selected_algorithm": best["algorithm"],
        "selected_cv5_dev": best["cv5_dev"],
        "selected_dev_metrics": dev_metrics,
        "selected_test_metrics": test_metrics,
        "selected_test_overfit_gap_dev_minus_test_acc": round(
            dev_metrics["accuracy"] - test_metrics["accuracy"], 4
        ),
        "selected_test_bootstrap_95_ci": test_ci,
        "per_class_test_metrics": per_class_clean,
        "confusion_matrix_labels": labels_sorted,
        "confusion_matrix": cm.tolist(),
        "test_misclassifications": misclassified_cases,
        "artifact": {
            "path": str(MODEL_OUT.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": int(size_bytes),
            "size_mb": round(size_bytes / (1024 * 1024), 4),
        },
        "limitations": [
            "Crop_recommendation.csv covers 22 benchmark crops (100 samples each) and does not contain Season, State/Region, soil texture, or market economics.",
            "Synthetic-benchmark origin means natural intra-class boundary overlap occurs primarily between high-moisture monsoon crops (rice/jute) and dryland pulses (blackgram/lentil/mothbeans).",
            "Season and Region fields in UI are recorded for farmer context and agronomic commentary only; classification probabilities are computed strictly from the 7 validated soil and climate features.",
        ],
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    print(f"Selected Crop Recommendation model: {best['key']} -> {MODEL_OUT.name} ({size_bytes / 1024:.1f} KB)")
    for b in benchmarks:
        print(
            f"  {b['key']:28s} | Train Acc={b['train_metrics']['accuracy']:.4f} | Val Acc={b['validation_metrics']['accuracy']:.4f} | CV5={b['cv5_dev']['accuracy_mean']:.4f} +/- {b['cv5_dev']['accuracy_std']:.4f} | LogLoss={b['cv5_dev']['log_loss_mean']:.4f}"
        )
    print(
        f"Held-Out Test ({len(X_test)} rows): Acc={test_metrics['accuracy']:.4f}, Macro-F1={test_metrics['macro_f1']:.4f}, Top3={test_metrics['top_3_accuracy']:.4f}, Misclassified={len(misclassified_cases)}"
    )
    return metrics_payload


if __name__ == "__main__":
    run_training()
