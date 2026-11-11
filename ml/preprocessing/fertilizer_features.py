"""Feature validation, domain harmonization, and conservative ICAR soil rules for Fertilizer Recommendation."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

RAW_COLUMN_RENAME_MAP = {
    "Temparature": "Temperature",
    "Humidity ": "Humidity",
    "Phosphorous": "Phosphorus",
}

ALL_CSV_FEATURE_COLUMNS = [
    "Nitrogen",
    "Phosphorus",
    "Potassium",
    "Temperature",
    "Humidity",
    "Moisture",
    "Soil Type",
    "Crop Type",
]

FIVE_CSV_FEATURE_COLUMNS = [
    "Nitrogen",
    "Phosphorus",
    "Potassium",
    "Soil Type",
    "Crop Type",
]

NPK_CSV_FEATURE_COLUMNS = ["Nitrogen", "Phosphorus", "Potassium"]

DATASET_SOIL_TYPES = ("Black", "Clayey", "Loamy", "Red", "Sandy")
DATASET_CROP_TYPES = (
    "Barley",
    "Cotton",
    "Ground Nuts",
    "Maize",
    "Millets",
    "Oil seeds",
    "Paddy",
    "Pulses",
    "Sugarcane",
    "Tobacco",
    "Wheat",
)
VALID_FERTILIZER_CLASSES = (
    "10-26-26",
    "14-35-14",
    "17-17-17",
    "20-20",
    "28-28",
    "DAP",
    "Urea",
)

# Agronomic soil sufficiency screening thresholds (Soil-kit / UI kg/ha aligned screening bands).
# Strictly qualitative status interpretation — NEVER used to invent chemical application dosages.
SOIL_OPTIMAL_BANDS = {
    "Nitrogen (N)": {"key": "nitrogen", "optimal_min": 40.0, "optimal_max": 95.0},
    "Phosphorus (P)": {"key": "phosphorus", "optimal_min": 30.0, "optimal_max": 65.0},
    "Potassium (K)": {"key": "potassium", "optimal_min": 30.0, "optimal_max": 75.0},
}

UI_SOIL_TO_DATASET_MAP = {
    "alluvial": ("Loamy", False),
    "black (regur)": ("Black", True),
    "black": ("Black", True),
    "red loamy": ("Red", False),
    "red": ("Red", True),
    "laterite": ("Red", False),
    "sandy loam": ("Sandy", False),
    "sandy": ("Sandy", True),
    "clay loam": ("Clayey", False),
    "clayey": ("Clayey", True),
    "loamy": ("Loamy", True),
}

UI_CROP_TO_DATASET_MAP = {
    "rice": ("Paddy", True),
    "paddy": ("Paddy", True),
    "cotton(lint)": ("Cotton", True),
    "cotton": ("Cotton", True),
    "groundnut": ("Ground Nuts", True),
    "ground nuts": ("Ground Nuts", True),
    "maize": ("Maize", True),
    "sugarcane": ("Sugarcane", True),
    "wheat": ("Wheat", True),
    "barley": ("Barley", True),
    "tobacco": ("Tobacco", True),
    "bajra": ("Millets", True),
    "jowar": ("Millets", True),
    "ragi": ("Millets", True),
    "small millets": ("Millets", True),
    "millets": ("Millets", True),
    "gram": ("Pulses", True),
    "arhar/tur": ("Pulses", True),
    "urad": ("Pulses", True),
    "moong(green gram)": ("Pulses", True),
    "masoor": ("Pulses", True),
    "khesari": ("Pulses", True),
    "moth": ("Pulses", True),
    "horse-gram": ("Pulses", True),
    "cowpea(lobia)": ("Pulses", True),
    "peas & beans (pulses)": ("Pulses", True),
    "other kharif pulses": ("Pulses", True),
    "other  rabi pulses": ("Pulses", True),
    "other rabi pulses": ("Pulses", True),
    "other summer pulses": ("Pulses", True),
    "pulses": ("Pulses", True),
    "blackgram": ("Pulses", True),
    "chickpea": ("Pulses", True),
    "kidneybeans": ("Pulses", True),
    "lentil": ("Pulses", True),
    "mothbeans": ("Pulses", True),
    "mungbean": ("Pulses", True),
    "pigeonpeas": ("Pulses", True),
    "rapeseed &mustard": ("Oil seeds", True),
    "rapeseed & mustard": ("Oil seeds", True),
    "soyabean": ("Oil seeds", True),
    "sunflower": ("Oil seeds", True),
    "sesamum": ("Oil seeds", True),
    "castor seed": ("Oil seeds", True),
    "linseed": ("Oil seeds", True),
    "safflower": ("Oil seeds", True),
    "niger seed": ("Oil seeds", True),
    "oilseeds total": ("Oil seeds", True),
    "other oilseeds": ("Oil seeds", True),
    "oil seeds": ("Oil seeds", True),
}


def clean_fertilizer_dataframe(
    df: pd.DataFrame, *, require_target: bool = False
) -> pd.DataFrame:
    """Normalize raw Fertilizer_Prediction.csv headers and validate finite non-negative bounds."""
    cleaned = df.rename(columns=lambda c: RAW_COLUMN_RENAME_MAP.get(c, str(c).strip())).copy()

    required = ["Nitrogen", "Phosphorus", "Potassium"]
    missing = [c for c in required if c not in cleaned.columns]
    if missing:
        raise ValueError(f"Missing required fertilizer columns: {missing}")

    numeric_candidates = [
        c
        for c in ("Nitrogen", "Phosphorus", "Potassium", "Temperature", "Humidity", "Moisture")
        if c in cleaned.columns
    ]
    for col in numeric_candidates:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="raise").astype(np.float64)
        if not np.isfinite(cleaned[col]).all():
            raise ValueError(f"Column '{col}' contains non-finite values.")
        if (cleaned[col] < 0).any():
            raise ValueError(f"Column '{col}' cannot be negative.")

    for cat in ("Soil Type", "Crop Type"):
        if cat in cleaned.columns:
            cleaned[cat] = cleaned[cat].astype(str).str.strip()

    if require_target:
        if "Fertilizer Name" not in cleaned.columns:
            raise ValueError("Target column 'Fertilizer Name' is required.")
        cleaned["Fertilizer Name"] = cleaned["Fertilizer Name"].astype(str).str.strip()
        unknown = set(cleaned["Fertilizer Name"]) - set(VALID_FERTILIZER_CLASSES)
        if unknown:
            raise ValueError(f"Unexpected fertilizer labels: {sorted(unknown)}")

    return cleaned


def harmonize_soil_type(soil_type: str) -> tuple[str, bool]:
    """Map UI soil texture name to closest dataset class; returns (mapped, is_exact)."""
    key = " ".join(soil_type.strip().lower().split())
    if key in UI_SOIL_TO_DATASET_MAP:
        return UI_SOIL_TO_DATASET_MAP[key]
    return ("Loamy", False)


def harmonize_crop_type(crop_type: str) -> tuple[str, bool]:
    """Map UI crop name to dataset crop category; returns (mapped, is_covered)."""
    key = " ".join(crop_type.strip().lower().split())
    if key in UI_CROP_TO_DATASET_MAP:
        return UI_CROP_TO_DATASET_MAP[key]
    return ("Paddy", False)


def assess_soil_balance(
    *,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    soil_ph: float,
) -> dict[str, Any]:
    """Evaluate soil NPK status and pH chemistry via conservative ICAR qualitative rules."""
    readings = {
        "Nitrogen (N)": float(nitrogen),
        "Phosphorus (P)": float(phosphorus),
        "Potassium (K)": float(potassium),
    }

    nutrient_levels: list[dict[str, Any]] = []
    shortfalls: dict[str, float] = {}
    surpluses: list[str] = []
    deficits: list[str] = []

    for label, meta in SOIL_OPTIMAL_BANDS.items():
        val = readings[label]
        opt_min = meta["optimal_min"]
        opt_max = meta["optimal_max"]
        if val < opt_min:
            status = "low"
            shortfalls[meta["key"]] = (opt_min - val) / opt_min
            deficits.append(label)
        elif val > opt_max:
            status = "high"
            shortfalls[meta["key"]] = 0.0
            surpluses.append(label)
        else:
            status = "optimal"
            shortfalls[meta["key"]] = 0.0

        nutrient_levels.append(
            {
                "nutrient": label,
                "value": round(val, 2),
                "optimal_min": opt_min,
                "optimal_max": opt_max,
                "status": status,
            }
        )

    if soil_ph < 5.8:
        ph_assessment = (
            f"Acidic soil (pH {soil_ph:.1f} < 5.8): Phosphorus fixation and exchangeable acidity may restrict nutrient uptake. "
            "Consult a local KVK or Soil Health Card lab regarding soil-buffer-calibrated agricultural lime amendment before mineral NPK application."
        )
    elif soil_ph > 7.8:
        ph_assessment = (
            f"Alkaline soil (pH {soil_ph:.1f} > 7.8): Elevated pH can reduce Phosphorus, Zinc, and Iron availability. "
            "Seek KVK laboratory confirmation for organic matter enrichment or gypsum/chelated micronutrient management rather than excess mineral NPK."
        )
    else:
        ph_assessment = (
            f"Favorable soil reaction (pH {soil_ph:.1f}, within 5.8–7.8): Primary macronutrient availability is well supported."
        )

    # Project agronomic shortfall weights cleanly onto Fertilizer_Prediction.csv grade geometry:
    # - Single-nutrient dominant deficit (e.g. only N low, P/K adequate) preserves ratio -> ~38 units
    #   so mild pure-N or pure-P deficits still select Urea or DAP instead of balanced N-P complexes.
    # - Multi-nutrient deficits scale total intensity from 24 (mild -> 20-20) up to 44 (severe -> 28-28 / 14-35-14).
    sum_d = shortfalls["nitrogen"] + shortfalls["phosphorus"] + shortfalls["potassium"]
    max_d = max(shortfalls["nitrogen"], shortfalls["phosphorus"], shortfalls["potassium"])
    if sum_d <= 0.0:
        need_n = 0.0
        need_p = 0.0
        need_k = 0.0
    else:
        w_n = shortfalls["nitrogen"] / sum_d
        w_p = shortfalls["phosphorus"] / sum_d
        w_k = shortfalls["potassium"] / sum_d
        if max(w_n, w_p, w_k) >= 0.85:
            total_units = 38.5
        elif w_k >= 0.20:
            # Complex NPK grades (17-17-17 sum ~38, 10-26-26 sum ~43, 14-35-14 sum ~46)
            total_units = 38.0 + 7.0 * min(max_d, 1.0)
        else:
            # Dual N-P grades (20-20 sum ~23, 28-28 sum ~44)
            total_units = 23.0 + 22.0 * min(max_d, 1.0)
        need_n = round(float(w_n * total_units), 3)
        need_p = round(float(w_p * total_units), 3)
        need_k = round(float(w_k * total_units), 3)

    return {
        "nutrient_levels": nutrient_levels,
        "shortfalls": shortfalls,
        "deficits": deficits,
        "surpluses": surpluses,
        "has_any_deficit": len(deficits) > 0,
        "demand_signature": {
            "Nitrogen": need_n,
            "Phosphorus": need_p,
            "Potassium": need_k,
        },
        "ph_assessment": ph_assessment,
    }
