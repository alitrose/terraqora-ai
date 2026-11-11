"""Leak-free feature engineering and canonical validation for Crop Yield Prediction."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

RAW_FEATURE_COLUMNS = [
    "Crop",
    "Crop_Year",
    "Season",
    "State",
    "Area",
    "Annual_Rainfall",
    "Fertilizer",
    "Pesticide",
]

CATEGORICAL_FEATURES = ["Crop", "Season", "State"]

ENGINEERED_NUMERIC_FEATURES = [
    "Crop_Year",
    "Annual_Rainfall",
    "log_rainfall",
    "fertilizer_per_ha",
    "pesticide_per_ha",
    "log_fertilizer_per_ha",
    "log_pesticide_per_ha",
    "rain_x_fert_per_ha",
]

ALL_MODEL_INPUT_FEATURES = CATEGORICAL_FEATURES + ENGINEERED_NUMERIC_FEATURES

VALID_CROPS = (
    "Arecanut",
    "Arhar/Tur",
    "Bajra",
    "Banana",
    "Barley",
    "Black pepper",
    "Cardamom",
    "Cashewnut",
    "Castor seed",
    "Coconut",
    "Coriander",
    "Cotton(lint)",
    "Cowpea(Lobia)",
    "Dry chillies",
    "Garlic",
    "Ginger",
    "Gram",
    "Groundnut",
    "Guar seed",
    "Horse-gram",
    "Jowar",
    "Jute",
    "Khesari",
    "Linseed",
    "Maize",
    "Masoor",
    "Mesta",
    "Moong(Green Gram)",
    "Moth",
    "Niger seed",
    "Oilseeds total",
    "Onion",
    "Other  Rabi pulses",
    "Other Cereals",
    "Other Kharif pulses",
    "Other Summer Pulses",
    "Peas & beans (Pulses)",
    "Potato",
    "Ragi",
    "Rapeseed &Mustard",
    "Rice",
    "Safflower",
    "Sannhamp",
    "Sesamum",
    "Small millets",
    "Soyabean",
    "Sugarcane",
    "Sunflower",
    "Sweet potato",
    "Tapioca",
    "Tobacco",
    "Turmeric",
    "Urad",
    "Wheat",
    "other oilseeds",
)

VALID_STATES = (
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)

VALID_SEASONS = (
    "Autumn",
    "Kharif",
    "Rabi",
    "Summer",
    "Whole Year",
    "Winter",
)

_CROP_CANONICAL_MAP = {c.lower(): c for c in VALID_CROPS}
_CROP_WHITESPACE_MAP = {" ".join(c.split()).lower(): c for c in VALID_CROPS}
_STATE_CANONICAL_MAP = {s.lower(): s for s in VALID_STATES}
_STATE_WHITESPACE_MAP = {" ".join(s.split()).lower(): s for s in VALID_STATES}
_SEASON_CANONICAL_MAP = {se.lower(): se for se in VALID_SEASONS}
_SEASON_WHITESPACE_MAP = {" ".join(se.split()).lower(): se for se in VALID_SEASONS}


def canonicalize_crop(value: str) -> str:
    key = value.strip().lower()
    if key in _CROP_CANONICAL_MAP:
        return _CROP_CANONICAL_MAP[key]
    ws_key = " ".join(value.split()).lower()
    if ws_key in _CROP_WHITESPACE_MAP:
        return _CROP_WHITESPACE_MAP[ws_key]
    raise ValueError(
        f"Unsupported crop '{value}'. Must match one of the {len(VALID_CROPS)} supported dataset crops."
    )


def canonicalize_state(value: str) -> str:
    key = value.strip().lower()
    if key in _STATE_CANONICAL_MAP:
        return _STATE_CANONICAL_MAP[key]
    ws_key = " ".join(value.split()).lower()
    if ws_key in _STATE_WHITESPACE_MAP:
        return _STATE_WHITESPACE_MAP[ws_key]
    raise ValueError(
        f"Unsupported state '{value}'. Must match one of the {len(VALID_STATES)} supported Indian states/UTs."
    )


def canonicalize_season(value: str) -> str:
    key = value.strip().lower()
    if key in _SEASON_CANONICAL_MAP:
        return _SEASON_CANONICAL_MAP[key]
    ws_key = " ".join(value.split()).lower()
    if ws_key in _SEASON_WHITESPACE_MAP:
        return _SEASON_WHITESPACE_MAP[ws_key]
    raise ValueError(
        f"Unsupported season '{value}'. Supported values: {', '.join(VALID_SEASONS)}."
    )


def clean_crop_yield_dataframe(df: pd.DataFrame, *, require_target: bool = False) -> pd.DataFrame:
    """Validate and clean raw crop_yield DataFrame without allowing target leakage."""
    for forbidden in ("Production", "production"):
        if forbidden in df.columns:
            raise ValueError(
                f"Target leakage error: '{forbidden}' must be dropped before modeling or inference."
            )

    missing_cols = [c for c in RAW_FEATURE_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required feature columns: {missing_cols}")

    cleaned = df.copy()
    for col in CATEGORICAL_FEATURES:
        cleaned[col] = cleaned[col].astype(str).str.strip()

    numeric_cols = ["Crop_Year", "Area", "Annual_Rainfall", "Fertilizer", "Pesticide"]
    if require_target:
        if "Yield" not in cleaned.columns:
            raise ValueError("Target column 'Yield' is required.")
        numeric_cols.append("Yield")

    for col in numeric_cols:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="raise")

    if (cleaned["Area"] <= 0).any():
        raise ValueError("Area must be strictly greater than 0 hectares.")
    for col in ("Annual_Rainfall", "Fertilizer", "Pesticide"):
        if (cleaned[col] < 0).any():
            raise ValueError(f"{col} cannot be negative.")
    if require_target and (cleaned["Yield"] < 0).any():
        raise ValueError("Target 'Yield' cannot be negative.")

    return cleaned


class YieldFeatureEngineer(BaseEstimator, TransformerMixin):
    """Stateless transformer deriving scale-invariant agronomic input intensities."""

    def fit(self, X: pd.DataFrame, y: Any = None) -> "YieldFeatureEngineer":
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = clean_crop_yield_dataframe(X, require_target=False)

        area = df["Area"].to_numpy(dtype=np.float64)
        rainfall = df["Annual_Rainfall"].to_numpy(dtype=np.float64)
        fertilizer = df["Fertilizer"].to_numpy(dtype=np.float64)
        pesticide = df["Pesticide"].to_numpy(dtype=np.float64)

        fert_per_ha = fertilizer / np.maximum(area, 1e-6)
        pest_per_ha = pesticide / np.maximum(area, 1e-6)

        df["log_rainfall"] = np.log1p(rainfall)
        df["fertilizer_per_ha"] = fert_per_ha
        df["pesticide_per_ha"] = pest_per_ha
        df["log_fertilizer_per_ha"] = np.log1p(fert_per_ha)
        df["log_pesticide_per_ha"] = np.log1p(pest_per_ha)
        df["rain_x_fert_per_ha"] = df["log_rainfall"] * df["log_fertilizer_per_ha"]

        return df[ALL_MODEL_INPUT_FEATURES]
