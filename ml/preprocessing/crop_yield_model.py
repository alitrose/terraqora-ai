"""Serializable model wrapper & SHAP feature-driver attribution for Crop Yield."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import xgboost as xgb

from ml.preprocessing.crop_yield_features import (
    CATEGORICAL_FEATURES,
    ENGINEERED_NUMERIC_FEATURES,
    YieldFeatureEngineer,
)

FEATURE_GROUP_LABELS = (
    ("Crop Variety", "cat__Crop_"),
    ("State Agro-Climatic Zone", "cat__State_"),
    ("Cropping Season", "cat__Season_"),
)

NUMERIC_GROUP_MAP = {
    "Crop_Year": "Target Year Baseline",
    "Annual_Rainfall": "Annual Rainfall (mm)",
    "log_rainfall": "Annual Rainfall (mm)",
    "fertilizer_per_ha": "Fertilizer Intensity (kg/ha)",
    "log_fertilizer_per_ha": "Fertilizer Intensity (kg/ha)",
    "rain_x_fert_per_ha": "Fertilizer Intensity (kg/ha)",
    "pesticide_per_ha": "Pesticide Intensity (kg/ha)",
    "log_pesticide_per_ha": "Pesticide Intensity (kg/ha)",
}


def _forest_local_contributions(forest: Any, X_enc: np.ndarray) -> np.ndarray:
    """Compute exact Saabas decision-path local feature contributions for a tree ensemble."""
    X_arr = np.asarray(X_enc, dtype=np.float32)
    n_features = X_arr.shape[1]
    total = np.zeros(n_features, dtype=np.float64)
    estimators = getattr(forest, "estimators_", [])
    if not estimators:
        return total

    for tree_est in estimators:
        tree = tree_est.tree_
        node_path = tree_est.decision_path(X_arr).indices
        features = tree.feature
        values = tree.value
        for idx in range(len(node_path) - 1):
            parent = int(node_path[idx])
            child = int(node_path[idx + 1])
            feat_idx = int(features[parent])
            if feat_idx >= 0:
                total[feat_idx] += float(values[child, 0, 0] - values[parent, 0, 0])

    return total / float(len(estimators))


def build_preprocessor(*, scale_numeric: bool = True) -> ColumnTransformer:
    """Create ColumnTransformer for categorical + engineered numeric features."""
    num_transformer: Any = StandardScaler() if scale_numeric else "passthrough"
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("num", num_transformer, ENGINEERED_NUMERIC_FEATURES),
        ],
        remainder="drop",
    )


def build_pipeline(estimator: Any, *, scale_numeric: bool = True, log_target: bool = False) -> Pipeline:
    """Wrap feature engineering + preprocessing + estimator (with optional log1p target)."""
    pipe = Pipeline(
        steps=[
            ("features", YieldFeatureEngineer()),
            ("preprocess", build_preprocessor(scale_numeric=scale_numeric)),
            ("model", estimator),
        ]
    )
    if log_target:
        return Pipeline(
            steps=[
                ("features", YieldFeatureEngineer()),
                ("preprocess", build_preprocessor(scale_numeric=scale_numeric)),
                (
                    "model",
                    TransformedTargetRegressor(
                        regressor=estimator,
                        func=np.log1p,
                        inverse_func=np.expm1,
                        check_inverse=False,
                    ),
                ),
            ]
        )
    return pipe


class SegmentedYieldPredictor(BaseEstimator, RegressorMixin):
    """Routes Coconut (nuts/ha) vs Non-Coconut (tonnes/ha) into unit-consistent regressors."""

    def __init__(
        self,
        standard_estimator: Any,
        coconut_estimator: Any,
    ) -> None:
        self.standard_estimator = standard_estimator
        self.coconut_estimator = coconut_estimator

    def fit(self, X: pd.DataFrame, y: Any) -> "SegmentedYieldPredictor":
        df = X.copy()
        crop_trimmed = df["Crop"].astype(str).str.strip()
        is_coconut = (crop_trimmed == "Coconut").to_numpy()
        y_arr = np.asarray(y, dtype=np.float64)

        self.standard_model_ = clone(self.standard_estimator)
        self.coconut_model_ = clone(self.coconut_estimator)

        if np.any(~is_coconut):
            self.standard_model_.fit(df.loc[~is_coconut], y_arr[~is_coconut])
        if np.any(is_coconut):
            self.coconut_model_.fit(df.loc[is_coconut], y_arr[is_coconut])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        df = X.copy()
        crop_trimmed = df["Crop"].astype(str).str.strip()
        is_coconut = (crop_trimmed == "Coconut").to_numpy()
        preds = np.zeros(len(df), dtype=np.float64)

        if np.any(~is_coconut):
            preds[~is_coconut] = self.standard_model_.predict(df.loc[~is_coconut])
        if np.any(is_coconut):
            preds[is_coconut] = self.coconut_model_.predict(df.loc[is_coconut])

        return np.clip(preds, 0.0, None)


def _group_feature_name(raw_name: str) -> str:
    for label, prefix in FEATURE_GROUP_LABELS:
        if raw_name.startswith(prefix):
            return label
    if raw_name.startswith("num__"):
        col = raw_name[len("num__") :]
        return NUMERIC_GROUP_MAP.get(col, col)
    return raw_name


def compute_feature_drivers(model: Any, row_df: pd.DataFrame, *, top_k: int = 6) -> list[dict[str, Any]]:
    """Compute signed, normalized feature attributions for a single-row DataFrame."""
    target_pipe = model
    if isinstance(model, SegmentedYieldPredictor):
        is_coconut = str(row_df["Crop"].iloc[0]).strip() == "Coconut"
        target_pipe = model.coconut_model_ if is_coconut else model.standard_model_

    feat_step = target_pipe.named_steps["features"]
    prep_step = target_pipe.named_steps["preprocess"]
    model_step = target_pipe.named_steps["model"]

    inner_est = model_step.regressor_ if isinstance(model_step, TransformedTargetRegressor) else model_step
    X_eng = feat_step.transform(row_df)
    X_enc = prep_step.transform(X_eng)
    feature_names = list(prep_step.get_feature_names_out())

    grouped_contribs: dict[str, float] = {}

    is_global_importance_only = False

    if isinstance(inner_est, xgb.XGBRegressor):
        booster = inner_est.get_booster()
        dmat = xgb.DMatrix(X_enc)
        # Last column of pred_contribs is bias term; exclude it
        shap_vals = booster.predict(dmat, pred_contribs=True)[0][:-1]
        for fname, val in zip(feature_names, shap_vals):
            grp = _group_feature_name(fname)
            grouped_contribs[grp] = grouped_contribs.get(grp, 0.0) + float(val)
    elif hasattr(inner_est, "estimators_"):
        local_vals = _forest_local_contributions(inner_est, X_enc)
        for fname, val in zip(feature_names, local_vals):
            grp = _group_feature_name(fname)
            grouped_contribs[grp] = grouped_contribs.get(grp, 0.0) + float(val)
    elif hasattr(inner_est, "coef_"):
        coefs = np.ravel(inner_est.coef_)
        vals = X_enc[0] * coefs
        for fname, val in zip(feature_names, vals):
            grp = _group_feature_name(fname)
            grouped_contribs[grp] = grouped_contribs.get(grp, 0.0) + float(val)
    elif hasattr(inner_est, "feature_importances_"):
        is_global_importance_only = True
        imps = np.ravel(inner_est.feature_importances_)
        for fname, val in zip(feature_names, imps):
            grp = _group_feature_name(fname)
            grouped_contribs[grp] = grouped_contribs.get(grp, 0.0) + float(val)
    else:
        return [
            {"feature": "Crop Variety", "impact_pct": 50.0, "direction": "neutral"},
            {"feature": "State Agro-Climatic Zone", "impact_pct": 50.0, "direction": "neutral"},
        ]

    total_abs = sum(abs(v) for v in grouped_contribs.values())
    if total_abs <= 1e-12:
        total_abs = 1.0

    drivers = []
    for grp, signed_val in grouped_contribs.items():
        pct = round(abs(signed_val) / total_abs * 100.0, 1)
        if is_global_importance_only:
            direction = "neutral"
        elif signed_val > 1e-6:
            direction = "positive"
        elif signed_val < -1e-6:
            direction = "negative"
        else:
            direction = "neutral"
        drivers.append({"feature": grp, "impact_pct": pct, "direction": direction})

    drivers.sort(key=lambda d: d["impact_pct"], reverse=True)
    return drivers[:top_k]
