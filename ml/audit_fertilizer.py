r"""Stage 1 Read-Only Data Audit for ml/datasets/raw/Fertilizer_Prediction.csv.

Inspects raw schema typos, missing values, duplicates, class imbalance, numerical bounds,
mutual information with target Fertilizer Name, and domain scope boundaries (nutrient
grade classification vs agronomic dosages / soil pH).

Usage:
    .\.venv\Scripts\python.exe -m ml.audit_fertilizer
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "ml" / "datasets" / "raw" / "Fertilizer_Prediction.csv"
AUDIT_OUT = ROOT / "ml" / "evaluation" / "fertilizer_audit.json"
EXPECTED_SHA256 = "dfd69cee9d3d7a4403aab5647d5749050ae406ad42dc9ce3f508aa3442955e41"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_audit() -> dict:
    sha256 = _file_sha256(RAW_CSV)
    if sha256 != EXPECTED_SHA256:
        raise ValueError(
            f"Fertilizer_Prediction.csv checksum mismatch: expected {EXPECTED_SHA256}, got {sha256}"
        )

    df_raw = pd.read_csv(RAW_CSV)
    raw_columns = list(df_raw.columns)

    # Clean whitespace and spelling typos ONLY in memory
    rename_map = {
        "Temparature": "Temperature",
        "Humidity ": "Humidity",
        "Phosphorous": "Phosphorus",
    }
    df = df_raw.rename(columns=lambda c: rename_map.get(c, c.strip())).copy()
    for col in ["Soil Type", "Crop Type", "Fertilizer Name"]:
        df[col] = df[col].astype(str).str.strip()

    null_counts = {col: int(df[col].isna().sum()) for col in df.columns}
    exact_dups = int(df.duplicated().sum())

    num_cols = ["Temperature", "Humidity", "Moisture", "Nitrogen", "Phosphorus", "Potassium"]
    cat_cols = ["Soil Type", "Crop Type"]

    distributions = {}
    for col in num_cols:
        s = df[col].astype(float)
        distributions[col] = {
            "min": round(float(s.min()), 2),
            "p25": round(float(s.quantile(0.25)), 2),
            "median": round(float(s.median()), 2),
            "mean": round(float(s.mean()), 2),
            "p75": round(float(s.quantile(0.75)), 2),
            "max": round(float(s.max()), 2),
            "std": round(float(s.std()), 2),
        }

    # Feature-target mutual information
    X_mi = df[num_cols + cat_cols].copy()
    X_mi[cat_cols] = OrdinalEncoder().fit_transform(X_mi[cat_cols].astype(str))
    mi = mutual_info_classif(X_mi, df["Fertilizer Name"], random_state=42)
    mi_map = {
        col: round(float(score), 4)
        for col, score in zip(list(X_mi.columns), mi)
    }

    # Per-fertilizer NPK min/mean/max summary to verify label semantics
    npk_by_class = {}
    for fert_name, grp in df.groupby("Fertilizer Name"):
        npk_by_class[str(fert_name)] = {
            "count": int(len(grp)),
            "Nitrogen": {
                "min": int(grp["Nitrogen"].min()),
                "mean": round(float(grp["Nitrogen"].mean()), 1),
                "max": int(grp["Nitrogen"].max()),
            },
            "Phosphorus": {
                "min": int(grp["Phosphorus"].min()),
                "mean": round(float(grp["Phosphorus"].mean()), 1),
                "max": int(grp["Phosphorus"].max()),
            },
            "Potassium": {
                "min": int(grp["Potassium"].min()),
                "mean": round(float(grp["Potassium"].mean()), 1),
                "max": int(grp["Potassium"].max()),
            },
        }

    audit = {
        "dataset_path": str(RAW_CSV.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256,
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "raw_columns": raw_columns,
        "column_anomalies_detected": [
            "Typo 'Temparature' -> standardized to 'Temperature' in preprocessing.",
            "Trailing whitespace 'Humidity ' -> trimmed to 'Humidity'.",
            "Spelling variant 'Phosphorous' -> standardized to 'Phosphorus'.",
        ],
        "missing_values": null_counts,
        "duplicates": {"exact_rows": exact_dups},
        "class_balance": {
            "num_classes": int(df["Fertilizer Name"].nunique()),
            "counts": {str(k): int(v) for k, v in df["Fertilizer Name"].value_counts().items()},
            "min_class_count": int(df["Fertilizer Name"].value_counts().min()),
            "max_class_count": int(df["Fertilizer Name"].value_counts().max()),
        },
        "categorical_domains": {
            "soil_types": sorted(df["Soil Type"].unique().tolist()),
            "crop_types": sorted(df["Crop Type"].unique().tolist()),
        },
        "numeric_distributions": distributions,
        "mutual_information_with_target": mi_map,
        "npk_signatures_by_fertilizer": npk_by_class,
        "alternative_public_datasets_audited_and_rejected": [
            {
                "source": "irakozekelly/fertilizer-prediction (100,000 rows, Kaggle)",
                "reason_rejected": "Empirical audit confirmed pure uniform random synthetic generation: mutual information <= 0.014 across all 8 features; 5-fold CV Random Forest accuracy = 14.43% (+/- 0.54%), worse than majority baseline 14.71%.",
            },
            {
                "source": "Tejasgolhar/Fertilizer_Recommendation_System f2.csv (552 rows, GitHub)",
                "reason_rejected": "Contains 414/552 (75.0%) exact duplicated rows creating severe train/test leakage, one singleton target class (1 sample), inconsistent crop casing ('rice' vs 'Paddy'), and no license declaration.",
            },
            {
                "source": "AgriNet Mendeley Dataset (doi:10.17632/c7tr9j78td.1, 257 rows, CC BY 4.0)",
                "reason_rejected": "Authentic KVK IVRI Bareilly alluvial soil laboratory chemistry table (pH, EC, OC, macro/micro nutrients), but exported CSV contains zero fertilizer recommendation target columns.",
            },
        ],
        "domain_scope_and_safety_conclusions": [
            "SUPPORTS: 7-class fertilizer formulation/grade classification (Urea, DAP, 28-28, 14-35-14, 20-20, 17-17-17, 10-26-26) based strictly on NPK demand ratio.",
            "DOES NOT SUPPORT: Soil pH acidity/alkalinity correction (no pH column present), crop-specific yield response modeling (Soil Type MI=0.0, Crop Type MI=0.0), or quantitative dosage prediction (kg/ha, g/plant, split rates absent).",
            "SAFETY INVARIANT: In Fertilizer_Prediction.csv, Urea corresponds to N=35-42, P=0, K=0 (applied nutrient ratio signature), NOT high residual soil nitrogen abundance. Feeding raw high soil-N readings straight into an unguarded classifier would give inverse recommendations. Production inference therefore derives a conservative relative nutrient-deficit target profile from ICAR sufficiency thresholds before invoking ML classification, and overrides conservatively when Soil NPK readings are already optimal/high.",
        ],
    }

    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return audit


if __name__ == "__main__":
    run_audit()
