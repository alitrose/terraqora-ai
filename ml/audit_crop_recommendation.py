"""Stage 1 Read-Only Data Audit for ml/datasets/raw/Crop_recommendation.csv.

Verifies SHA-256 checksum, schema, missing values, duplicates, class balance,
feature distributions, physical bounds, outlier rates, and inter-class centroid overlap.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "ml" / "datasets" / "raw" / "Crop_recommendation.csv"
AUDIT_OUT = ROOT / "ml" / "evaluation" / "crop_rec_audit.json"
EXPECTED_SHA256 = "54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e"

FEATURE_COLS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


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
            f"Crop_recommendation.csv checksum mismatch: expected {EXPECTED_SHA256}, got {sha256}"
        )

    df = pd.read_csv(RAW_CSV)
    null_counts = {col: int(df[col].isna().sum()) for col in df.columns}

    raw_label = df["label"].astype(str)
    trimmed_label = raw_label.str.strip()
    whitespace_issues = int((raw_label != trimmed_label).sum())

    exact_duplicates = int(df.duplicated().sum())
    feature_only_duplicates = int(df.duplicated(subset=FEATURE_COLS).sum())

    # Check if any identical feature vector has conflicting labels
    grouped_labels_per_x = df.groupby(FEATURE_COLS)["label"].nunique()
    conflicting_label_rows = int((grouped_labels_per_x > 1).sum())

    class_counts = {
        str(k): int(v) for k, v in trimmed_label.value_counts().sort_index().items()
    }

    dist = {}
    iqr_outliers = {}
    for col in FEATURE_COLS:
        s = df[col].astype(float)
        q1 = float(s.quantile(0.25))
        q3 = float(s.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        iqr_outliers[col] = int(((s < lower) | (s > upper)).sum())
        dist[col] = {
            "min": round(float(s.min()), 4),
            "p5": round(float(s.quantile(0.05)), 4),
            "p25": round(q1, 4),
            "median": round(float(s.median()), 4),
            "mean": round(float(s.mean()), 4),
            "p75": round(q3, 4),
            "p95": round(float(s.quantile(0.95)), 4),
            "max": round(float(s.max()), 4),
            "std": round(float(s.std()), 4),
        }

    domain_anomalies = {
        "negative_N": int((df["N"] < 0).sum()),
        "negative_P": int((df["P"] < 0).sum()),
        "negative_K": int((df["K"] < 0).sum()),
        "humidity_out_of_0_100": int(((df["humidity"] < 0) | (df["humidity"] > 100)).sum()),
        "ph_out_of_0_14": int(((df["ph"] < 0) | (df["ph"] > 14)).sum()),
        "negative_rainfall": int((df["rainfall"] < 0).sum()),
        "non_finite_numeric": int((~np.isfinite(df[FEATURE_COLS].to_numpy())).sum()),
    }

    # Standardized centroid distances between crops to inspect natural class overlap
    X_std = (df[FEATURE_COLS] - df[FEATURE_COLS].mean()) / df[FEATURE_COLS].std()
    X_std["label"] = trimmed_label
    centroids = X_std.groupby("label")[FEATURE_COLS].mean()
    crops = list(centroids.index)
    pair_distances = []
    mat = centroids.to_numpy()
    for i in range(len(crops)):
        for j in range(i + 1, len(crops)):
            d = float(np.linalg.norm(mat[i] - mat[j]))
            pair_distances.append({"crop_a": crops[i], "crop_b": crops[j], "std_euclidean_dist": round(d, 4)})
    pair_distances.sort(key=lambda x: x["std_euclidean_dist"])

    # Per-crop mean profile for explainability verification
    per_crop_means = (
        df.assign(label=trimmed_label)
        .groupby("label")[FEATURE_COLS]
        .mean()
        .round(2)
        .to_dict(orient="index")
    )

    # Compute correlation matrix among features
    corr_matrix = df[FEATURE_COLS].corr().round(4).to_dict()

    audit = {
        "dataset_path": str(RAW_CSV.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256,
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": null_counts,
        "duplicates": {
            "exact_rows": exact_duplicates,
            "feature_only_duplicates": feature_only_duplicates,
            "conflicting_label_feature_vectors": conflicting_label_rows,
        },
        "whitespace_anomalies_in_label": whitespace_issues,
        "class_balance": {
            "num_classes": len(class_counts),
            "min_samples_per_class": min(class_counts.values()),
            "max_samples_per_class": max(class_counts.values()),
            "counts": class_counts,
        },
        "feature_distributions": dist,
        "iqr_outlier_counts": iqr_outliers,
        "domain_anomalies": domain_anomalies,
        "closest_5_crop_centroid_pairs_standardized": pair_distances[:5],
        "farthest_3_crop_centroid_pairs_standardized": pair_distances[-3:],
        "feature_correlations": corr_matrix,
        "per_crop_feature_means": per_crop_means,
        "leakage_and_quality_notes": [
            "Zero missing values and zero exact or feature-level duplicates across 2,200 observations.",
            "All 22 crop classes have exactly 100 samples each (perfectly balanced benchmark dataset).",
            "No temporal, spatial ID, or target-derived proxy columns exist; all 7 inputs are observable soil/climate metrics.",
            "Note: Season and Region/State from the frontend UI are NOT present in Crop_recommendation.csv; ML classification must rely solely on the 7 verified soil/climate inputs.",
            "Expect strong class separability in tree/boosting ensembles, with remaining edge-case boundary confusion concentrated among closely related pulses (e.g., lentil/blackgram/mungbean) and high-humidity crops (rice/jute/papaya).",
        ],
    }

    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return audit


if __name__ == "__main__":
    run_audit()
