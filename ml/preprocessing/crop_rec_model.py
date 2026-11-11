"""Sklearn-compatible multiclass wrapper and profile explainability for Crop Recommendation."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ml.preprocessing.crop_rec_features import (
    CropRecFeatureEngineer,
    RAW_CROP_REC_FEATURES,
    clean_crop_rec_dataframe,
)


class CropRecommendationModel(BaseEstimator, ClassifierMixin):
    """Serializable multiclass pipeline supporting sklearn & XGBoost string-label classifiers.

    Stores per-crop training-split quartile profiles cleanly inside `fit()` (zero test leakage)
    to generate human-readable fit reasons alongside calibrated top-k probabilities.
    """

    def __init__(
        self,
        estimator: Any,
        *,
        use_scaler: bool = False,
        include_engineered: bool = True,
        encode_labels: bool = False,
    ) -> None:
        self.estimator = estimator
        self.use_scaler = use_scaler
        self.include_engineered = include_engineered
        self.encode_labels = encode_labels

    def fit(self, X: pd.DataFrame, y: Any) -> "CropRecommendationModel":
        df = clean_crop_rec_dataframe(X, require_target=False)
        y_arr = np.asarray([str(v).strip() for v in y], dtype=object)

        steps: list[tuple[str, Any]] = [
            ("features", CropRecFeatureEngineer(include_engineered=self.include_engineered)),
            ("scaler", StandardScaler() if self.use_scaler else "passthrough"),
            ("clf", clone(self.estimator)),
        ]
        self.pipeline_ = Pipeline(steps)

        if self.encode_labels:
            self.label_encoder_ = LabelEncoder()
            y_fit = self.label_encoder_.fit_transform(y_arr)
            self.classes_ = np.asarray(self.label_encoder_.classes_, dtype=object)
        else:
            self.label_encoder_ = None
            y_fit = y_arr

        self.pipeline_.fit(df, y_fit)
        if not self.encode_labels:
            self.classes_ = np.asarray(self.pipeline_.named_steps["clf"].classes_, dtype=object)

        # Compute training-only quartile benchmarks per crop for transparent explanation
        profiles: dict[str, dict[str, dict[str, float]]] = {}
        df_prof = df[RAW_CROP_REC_FEATURES].copy()
        df_prof["_label"] = y_arr
        for crop_name, grp in df_prof.groupby("_label"):
            crop_stats: dict[str, dict[str, float]] = {}
            for col in RAW_CROP_REC_FEATURES:
                s = grp[col].astype(float)
                crop_stats[col] = {
                    "p25": round(float(s.quantile(0.25)), 2),
                    "median": round(float(s.median()), 2),
                    "p75": round(float(s.quantile(0.75)), 2),
                }
            profiles[str(crop_name)] = crop_stats
        self.crop_profiles_ = profiles
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        df = clean_crop_rec_dataframe(X, require_target=False)
        probs = np.asarray(self.pipeline_.predict_proba(df), dtype=np.float64)
        # Ensure rows normalize cleanly to 1.0
        row_sums = probs.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1.0)
        return probs / row_sums

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        indices = np.argmax(probs, axis=1)
        return self.classes_[indices]

    def top_k_candidates(
        self, row_df: pd.DataFrame, *, k: int = 3
    ) -> list[dict[str, Any]]:
        """Return top-k crop candidates with calibrated probability and training-band fit reason."""
        df = clean_crop_rec_dataframe(row_df, require_target=False)
        probs = self.predict_proba(df)[0]
        order = np.argsort(probs)[::-1][:k]

        row_vals = {col: float(df.iloc[0][col]) for col in RAW_CROP_REC_FEATURES}
        candidates: list[dict[str, Any]] = []
        profiles = getattr(self, "crop_profiles_", {})

        for idx in order:
            crop = str(self.classes_[idx])
            prob = round(float(probs[idx]), 4)
            reason = _build_fit_reason(crop, row_vals, profiles.get(crop, {}))
            candidates.append(
                {
                    "crop": crop,
                    "probability": prob,
                    "fit_reason": reason,
                }
            )
        return candidates


def _build_fit_reason(
    crop: str,
    row_vals: dict[str, float],
    crop_profile: dict[str, dict[str, float]],
) -> str:
    if not crop_profile:
        return f"Predicted compatibility match for {crop} from validated soil and climate features."

    in_band: list[str] = []
    out_of_band: list[str] = []
    labels = {
        "rainfall": ("rainfall", "mm"),
        "humidity": ("humidity", "%"),
        "temperature": ("temp", "°C"),
        "ph": ("pH", ""),
        "N": ("N", ""),
        "P": ("P", ""),
        "K": ("K", ""),
    }

    for col in ("rainfall", "humidity", "temperature", "ph", "N", "P", "K"):
        stats = crop_profile.get(col)
        if not stats:
            continue
        val = row_vals[col]
        p25, med, p75 = stats["p25"], stats["median"], stats["p75"]
        # Expand IQR margin gently to describe typical crop suitability band
        margin = max((p75 - p25) * 0.5, 0.25 if col == "ph" else 2.0)
        low, high = p25 - margin, p75 + margin
        name, unit = labels[col]
        suffix = f" {unit}" if unit else ""
        if low <= val <= high:
            in_band.append(f"{name} near {med:.0f}{suffix}" if col != "ph" else f"pH near {med:.1f}")
        else:
            direction = "below" if val < low else "above"
            out_of_band.append(f"{name} {direction} typical ({p25:.1f}–{p75:.1f}{suffix})")

    parts: list[str] = []
    if in_band:
        parts.append(f"Aligns with {crop} training band ({', '.join(in_band[:3])})")
    if out_of_band:
        parts.append(f"note {out_of_band[0]}")
    return "; ".join(parts) + "." if parts else f"Best relative fit for {crop}."
