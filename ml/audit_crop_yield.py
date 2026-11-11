"""Stage 1 Data Audit & Leakage Investigation for crop_yield.csv.

Reads ml/datasets/raw/crop_yield.csv strictly read-only without modifying it,
writes empirical audit metrics to ml/evaluation/crop_yield_audit.json, and prints
a detailed summary for ML methodology design.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "ml" / "datasets" / "raw" / "crop_yield.csv"
AUDIT_OUT = ROOT / "ml" / "evaluation" / "crop_yield_audit.json"


def run_audit() -> dict:
    df = pd.read_csv(RAW_CSV)

    null_counts = {col: int(df[col].isna().sum()) for col in df.columns}
    raw_dups = int(df.duplicated().sum())

    # Check whitespace anomalies on string columns
    str_cols = [c for c in df.columns if df[c].dtype == "object" or str(df[c].dtype) == "str"]
    whitespace_issues = {}
    df_clean = df.copy()
    for col in str_cols:
        series_str = df[col].astype(str)
        trimmed = series_str.str.strip()
        whitespace_issues[col] = int((series_str != trimmed).sum())
        df_clean[col] = trimmed

    cleaned_exact_dups = int(df_clean.duplicated().sum())
    key_cols = ["Crop", "Crop_Year", "Season", "State"]
    composite_key_dups = int(df_clean.duplicated(subset=key_cols).sum())

    # Leakage verification: Production / Area vs Yield
    computed_yield = df_clean["Production"] / df_clean["Area"].replace(0, np.nan)
    abs_diff = (df_clean["Yield"] - computed_yield).abs()
    rel_diff = abs_diff / df_clean["Yield"].replace(0, np.nan).abs()

    corr_numeric = df_clean[
        ["Crop_Year", "Area", "Production", "Annual_Rainfall", "Fertilizer", "Pesticide", "Yield"]
    ].corr(numeric_only=True)

    # Zero / negative checks
    anomalies = {
        "area_lte_zero": int((df_clean["Area"] <= 0).sum()),
        "production_lt_zero": int((df_clean["Production"] < 0).sum()),
        "production_eq_zero": int((df_clean["Production"] == 0).sum()),
        "yield_lt_zero": int((df_clean["Yield"] < 0).sum()),
        "yield_eq_zero": int((df_clean["Yield"] == 0).sum()),
        "rainfall_lte_zero": int((df_clean["Annual_Rainfall"] <= 0).sum()),
        "fertilizer_eq_zero": int((df_clean["Fertilizer"] == 0).sum()),
        "pesticide_eq_zero": int((df_clean["Pesticide"] == 0).sum()),
        "yield_eq_zero_and_prod_eq_zero": int(
            ((df_clean["Yield"] == 0) & (df_clean["Production"] == 0)).sum()
        ),
        "yield_eq_zero_but_prod_gt_zero": int(
            ((df_clean["Yield"] == 0) & (df_clean["Production"] > 0)).sum()
        ),
    }

    # Unit divergence: Coconut vs other crops
    is_coconut = df_clean["Crop"] == "Coconut"
    coconut_df = df_clean[is_coconut]
    other_df = df_clean[~is_coconut]

    def _dist_summary(s: pd.Series) -> dict:
        return {
            "count": int(len(s)),
            "min": float(s.min()),
            "p25": float(s.quantile(0.25)),
            "median": float(s.median()),
            "mean": float(s.mean()),
            "p75": float(s.quantile(0.75)),
            "p95": float(s.quantile(0.95)),
            "max": float(s.max()),
            "std": float(s.std()),
        }

    # Year coverage
    year_counts = {int(k): int(v) for k, v in df_clean["Crop_Year"].value_counts().sort_index().items()}
    year_counts_non_coco = {
        int(k): int(v)
        for k, v in other_df["Crop_Year"].value_counts().sort_index().items()
    }

    # Chronological split coverage simulation (using 1997-2019 non-Coconut vs 2020)
    train_years_cand = df_clean[df_clean["Crop_Year"] <= 2015]
    val_years_cand = df_clean[(df_clean["Crop_Year"] >= 2016) & (df_clean["Crop_Year"] <= 2017)]
    test_years_cand = df_clean[df_clean["Crop_Year"] >= 2018]

    unseen_crops_val = sorted(set(val_years_cand["Crop"]) - set(train_years_cand["Crop"]))
    unseen_crops_test = sorted(set(test_years_cand["Crop"]) - set(train_years_cand["Crop"]))
    unseen_states_val = sorted(set(val_years_cand["State"]) - set(train_years_cand["State"]))
    unseen_states_test = sorted(set(test_years_cand["State"]) - set(train_years_cand["State"]))

    top_crop_means = (
        df_clean.groupby("Crop")["Yield"]
        .agg(["count", "mean", "median", "max"])
        .sort_values("mean", ascending=False)
        .head(10)
        .round(3)
        .to_dict(orient="index")
    )

    low_count_crops = {
        str(k): int(v)
        for k, v in df_clean["Crop"].value_counts().tail(10).items()
    }

    audit = {
        "dataset_path": str(RAW_CSV.relative_to(ROOT)),
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": null_counts,
        "duplicates": {
            "raw_exact": raw_dups,
            "trimmed_exact": cleaned_exact_dups,
            "composite_crop_year_season_state": composite_key_dups,
        },
        "whitespace_anomalies": whitespace_issues,
        "cardinality_after_trim": {
            "Crop": int(df_clean["Crop"].nunique()),
            "Season": int(df_clean["Season"].nunique()),
            "State": int(df_clean["State"].nunique()),
            "Crop_Year": int(df_clean["Crop_Year"].nunique()),
            "seasons_list": sorted(df_clean["Season"].unique().tolist()),
        },
        "target_leakage_audit": {
            "pearson_r_production_vs_yield_all": float(corr_numeric.loc["Production", "Yield"]),
            "pearson_r_production_vs_yield_non_coconut": float(
                other_df[["Production", "Yield"]].corr().iloc[0, 1]
            ),
            "pearson_r_prod_per_area_vs_yield_all": float(
                pd.Series(computed_yield).corr(df_clean["Yield"])
            ),
            "median_abs_diff_yield_vs_prod_over_area": float(abs_diff.median()),
            "p95_abs_diff_yield_vs_prod_over_area": float(abs_diff.quantile(0.95)),
            "max_abs_diff_yield_vs_prod_over_area": float(abs_diff.max()),
            "rows_within_1pct_of_prod_over_area": int((rel_diff <= 0.01).sum()),
            "conclusion": "Production directly leaks Yield (Yield ~= Production / Area at district/state aggregate). Production MUST be excluded from inference features and training inputs.",
        },
        "anomalies": anomalies,
        "yield_distribution_all": _dist_summary(df_clean["Yield"]),
        "yield_distribution_coconut": _dist_summary(coconut_df["Yield"]),
        "yield_distribution_non_coconut": _dist_summary(other_df["Yield"]),
        "year_counts_all": year_counts,
        "year_counts_non_coconut": year_counts_non_coco,
        "chronological_split_preview_1997_2015_train__2016_2017_val__2018_2020_test": {
            "train_rows": int(len(train_years_cand)),
            "val_rows": int(len(val_years_cand)),
            "test_rows": int(len(test_years_cand)),
            "unseen_crops_in_val": unseen_crops_val,
            "unseen_crops_in_test": unseen_crops_test,
            "unseen_states_in_val": unseen_states_val,
            "unseen_states_in_test": unseen_states_test,
        },
        "top_10_crops_by_mean_yield": top_crop_means,
        "lowest_count_10_crops": low_count_crops,
    }

    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return audit


if __name__ == "__main__":
    run_audit()
