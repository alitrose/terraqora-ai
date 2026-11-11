"""Feature validation, cleaning, and agronomic ratios for Crop Recommendation."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

RAW_CROP_REC_FEATURES = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
]

ENGINEERED_CROP_REC_FEATURES = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
    "npk_total",
    "n_ratio",
    "p_ratio",
    "k_ratio",
    "moisture_index",
]

VALID_CROP_LABELS = (
    "apple",
    "banana",
    "blackgram",
    "chickpea",
    "coconut",
    "coffee",
    "cotton",
    "grapes",
    "jute",
    "kidneybeans",
    "lentil",
    "maize",
    "mango",
    "mothbeans",
    "mungbean",
    "muskmelon",
    "orange",
    "papaya",
    "pigeonpeas",
    "pomegranate",
    "rice",
    "watermelon",
)


def clean_crop_rec_dataframe(
    df: pd.DataFrame, *, require_target: bool = False
) -> pd.DataFrame:
    """Validate physical domains and dtypes for 7 crop recommendation inputs."""
    missing = [c for c in RAW_CROP_REC_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required crop recommendation columns: {missing}")

    cleaned = df.copy()
    for col in RAW_CROP_REC_FEATURES:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="raise").astype(np.float64)
        if not np.isfinite(cleaned[col]).all():
            raise ValueError(f"Column '{col}' contains non-finite values.")

    for col in ("N", "P", "K", "rainfall"):
        if (cleaned[col] < 0).any():
            raise ValueError(f"Column '{col}' cannot be negative.")
    if ((cleaned["humidity"] < 0) | (cleaned["humidity"] > 100)).any():
        raise ValueError("Humidity must be within [0, 100] %.")
    if ((cleaned["ph"] < 0) | (cleaned["ph"] > 14)).any():
        raise ValueError("Soil pH must be within [0, 14].")

    if require_target:
        if "label" not in cleaned.columns:
            raise ValueError("Target column 'label' is required.")
        cleaned["label"] = cleaned["label"].astype(str).str.strip()
        unknown = set(cleaned["label"]) - set(VALID_CROP_LABELS)
        if unknown:
            raise ValueError(f"Unexpected crop labels found: {sorted(unknown)}")

    return cleaned


class CropRecFeatureEngineer(BaseEstimator, TransformerMixin):
    """Derives leak-free NPK share ratios and climate moisture interaction."""

    def __init__(self, include_engineered: bool = True) -> None:
        self.include_engineered = include_engineered

    def fit(self, X: pd.DataFrame, y: Any = None) -> "CropRecFeatureEngineer":
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = clean_crop_rec_dataframe(X, require_target=False)
        if not self.include_engineered:
            return df[RAW_CROP_REC_FEATURES]

        n = df["N"].to_numpy(dtype=np.float64)
        p = df["P"].to_numpy(dtype=np.float64)
        k = df["K"].to_numpy(dtype=np.float64)
        npk_total = n + p + k
        denom = np.maximum(npk_total, 1.0)

        df["npk_total"] = npk_total
        df["n_ratio"] = n / denom
        df["p_ratio"] = p / denom
        df["k_ratio"] = k / denom
        df["moisture_index"] = (df["humidity"].to_numpy(dtype=np.float64) / 100.0) * df[
            "rainfall"
        ].to_numpy(dtype=np.float64)
        return df[ENGINEERED_CROP_REC_FEATURES]
