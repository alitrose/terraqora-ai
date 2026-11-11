"""Serializable pipeline wrapper for 7-class Fertilizer Grade Classification."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from ml.preprocessing.fertilizer_features import clean_fertilizer_dataframe


class FertilizerClassifierModel(BaseEstimator, ClassifierMixin):
    """Wraps sklearn / XGBoost classifiers with safe header normalization and string labels."""

    def __init__(
        self,
        estimator: Any,
        *,
        feature_columns: list[str],
        use_scaler: bool = False,
        encode_labels: bool = False,
    ) -> None:
        self.estimator = estimator
        self.feature_columns = list(feature_columns)
        self.use_scaler = use_scaler
        self.encode_labels = encode_labels

    def fit(self, X: pd.DataFrame, y: Any) -> "FertilizerClassifierModel":
        df = clean_fertilizer_dataframe(X, require_target=False)
        for col in self.feature_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required training column '{col}'.")

        X_sub = df[self.feature_columns].copy()
        num_cols = [c for c in self.feature_columns if c not in ("Soil Type", "Crop Type")]
        cat_cols = [c for c in self.feature_columns if c in ("Soil Type", "Crop Type")]

        transformers: list[tuple[str, Any, list[str]]] = [
            ("num", StandardScaler() if self.use_scaler else "passthrough", num_cols)
        ]
        if cat_cols:
            transformers.append(
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    cat_cols,
                )
            )

        pre = ColumnTransformer(transformers=transformers, remainder="drop")
        self.pipeline_ = Pipeline([("pre", pre), ("clf", clone(self.estimator))])

        y_arr = np.asarray([str(v).strip() for v in y], dtype=object)
        if self.encode_labels:
            self.label_encoder_ = LabelEncoder()
            y_fit = self.label_encoder_.fit_transform(y_arr)
            self.classes_ = np.asarray(self.label_encoder_.classes_, dtype=object)
        else:
            self.label_encoder_ = None
            y_fit = y_arr

        self.pipeline_.fit(X_sub, y_fit)
        if not self.encode_labels:
            self.classes_ = np.asarray(self.pipeline_.named_steps["clf"].classes_, dtype=object)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        df = clean_fertilizer_dataframe(X, require_target=False)
        for col in self.feature_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required inference column '{col}'.")
        probs = np.asarray(self.pipeline_.predict_proba(df[self.feature_columns]), dtype=np.float64)
        row_sums = probs.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1.0)
        return probs / row_sums

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        return self.classes_[np.argmax(probs, axis=1)]

    def predict_grade_with_confidence(
        self, row_df: pd.DataFrame
    ) -> tuple[str, float, list[dict[str, Any]]]:
        probs = self.predict_proba(row_df)[0]
        order = np.argsort(probs)[::-1]
        best_idx = int(order[0])
        top = [
            {"fertilizer": str(self.classes_[i]), "probability": round(float(probs[i]), 4)}
            for i in order[:3]
        ]
        return str(self.classes_[best_idx]), round(float(probs[best_idx]), 4), top
