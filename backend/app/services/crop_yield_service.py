import json
import logging
import math
from pathlib import Path
import sys
import threading
from typing import Any
import joblib
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import _PROJECT_ROOT
from app.models.farm import Farm
from app.models.modules import CropPrediction
from app.models.user import User
from app.schemas.admin import AdminModelStatusItem
from app.schemas.predictions import (
    CropYieldRequest,
    CropYieldResponse,
    FeatureDriverOut,
)

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

from ml.preprocessing.crop_yield_features import RAW_FEATURE_COLUMNS  # noqa: E402
from ml.preprocessing.crop_yield_model import compute_feature_drivers  # noqa: E402

logger = logging.getLogger("terraqora.ml.yield")

DEFAULT_MODEL_PATH = _PROJECT_ROOT / "ml" / "saved_models" / "crop_yield_model.joblib"
DEFAULT_METRICS_PATH = _PROJECT_ROOT / "ml" / "evaluation" / "crop_yield_metrics.json"

_CACHE_LOCK = threading.Lock()
_cached_model: Any | None = None
_cached_model_path: Path | None = None
_model_path_override: Path | None = None
_metrics_path_override: Path | None = None


def set_paths_for_testing(
    *, model_path: Path | None = None, metrics_path: Path | None = None
) -> None:
    """Override model/metrics paths in automated tests and invalidate cached model."""
    global _cached_model, _cached_model_path, _model_path_override, _metrics_path_override
    with _CACHE_LOCK:
        _model_path_override = model_path
        _metrics_path_override = metrics_path
        _cached_model = None
        _cached_model_path = None


def reset_cache() -> None:
    """Clear cached serialized predictor and any path overrides."""
    set_paths_for_testing(model_path=None, metrics_path=None)


def _get_model_path() -> Path:
    return _model_path_override if _model_path_override is not None else DEFAULT_MODEL_PATH


def _get_metrics_path() -> Path:
    return _metrics_path_override if _metrics_path_override is not None else DEFAULT_METRICS_PATH


def _load_metrics_metadata() -> dict[str, Any]:
    metrics_path = _get_metrics_path()
    if not metrics_path.exists() or not metrics_path.is_file():
        return {}
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not parse crop yield metrics metadata cleanly.")
        return {}


def _get_loaded_model() -> Any:
    global _cached_model, _cached_model_path
    model_path = _get_model_path()

    with _CACHE_LOCK:
        if _cached_model is not None and _cached_model_path == model_path:
            return _cached_model

        if not model_path.exists() or not model_path.is_file():
            logger.warning("Crop yield model artifact missing at expected location.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Crop yield prediction model is currently unavailable. Run the ML training pipeline before requesting predictions.",
            )

        try:
            loaded = joblib.load(model_path)
        except Exception as exc:
            logger.exception("Failed to deserialize crop yield model artifact: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Crop yield prediction model could not be loaded safely.",
            ) from exc

        if not hasattr(loaded, "predict") or not callable(loaded.predict):
            logger.error("Loaded crop yield artifact does not implement callable predict().")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Crop yield prediction model artifact is invalid.",
            )

        _cached_model = loaded
        _cached_model_path = model_path
        return _cached_model


def _build_advisory_note(
    payload: CropYieldRequest, predicted_yield: float, yield_unit: str
) -> str:
    fert_per_ha = payload.fertilizer_kg / max(payload.area_hectares, 1e-6)
    notes = [
        f"Estimated yield for {payload.crop} ({payload.season}, {payload.state}) is {predicted_yield:.2f} {yield_unit} at a nutrient application rate of {fert_per_ha:.1f} kg fertilizer/ha.",
        "Trained exclusively on leak-free pre-harvest features (excluding Production).",
    ]
    if payload.crop_year > 2020:
        notes.append(
            "Target years after 2020 use the learned 1997-2020 baseline without future yield trend extrapolation."
        )
    notes.append(
        "Dataset reflects state-level aggregate rainfall and chemical inputs without soil NPK, pH, or cultivar telemetry; confirm field doses via Soil Health Card and local KVK agronomist guidance."
    )
    return " ".join(notes)


def predict_crop_yield(
    db: Session,
    current_user: User,
    payload: CropYieldRequest,
) -> CropYieldResponse:
    if payload.farm_id is not None:
        farm = db.get(Farm, payload.farm_id)
        if farm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farm plot not found.",
            )
        if farm.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to link this farm plot.",
            )

    model = _get_loaded_model()
    metrics_meta = _load_metrics_metadata()
    model_key = str(metrics_meta.get("selected_model_key") or "")
    algo_map = {
        "random_forest_segmented": "Segmented Random Forest Regressor (Scale-Invariant)",
        "xgboost_segmented_native": "Segmented XGBoost Regressor (Native Target)",
        "xgboost_segmented_log1p": "Segmented XGBoost Regressor (log1p Target)",
        "ridge_segmented": "Segmented Ridge Regressor (Scale-Invariant)",
    }
    raw_algo = algo_map.get(
        model_key,
        str(metrics_meta.get("selected_algorithm") or "Segmented Crop Yield Regressor"),
    )
    model_name = raw_algo[:64]
    model_version = str(metrics_meta.get("model_version") or "phase5-v1.0.0")[:32]

    row_df = pd.DataFrame(
        [
            {
                "Crop": payload.crop,
                "Crop_Year": payload.crop_year,
                "Season": payload.season,
                "State": payload.state,
                "Area": float(payload.area_hectares),
                "Annual_Rainfall": float(payload.annual_rainfall_mm),
                "Fertilizer": float(payload.fertilizer_kg),
                "Pesticide": float(payload.pesticide_kg),
            }
        ],
        columns=RAW_FEATURE_COLUMNS,
    )

    try:
        raw_pred = float(model.predict(row_df)[0])
        if not math.isfinite(raw_pred):
            raise ValueError("Model returned non-finite prediction.")
        predicted_yield = round(max(0.0, raw_pred), 2)
        drivers_raw = compute_feature_drivers(model, row_df, top_k=6)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Crop yield inference execution failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Crop yield inference failed safely. Check inputs or contact support.",
        ) from exc

    is_coconut = payload.crop == "Coconut"
    yield_unit = "nuts/hectare" if is_coconut else "tonnes/hectare"
    production_unit = "nuts" if is_coconut else "tonnes"
    estimated_total = round(predicted_yield * float(payload.area_hectares), 2)
    advisory_note = _build_advisory_note(payload, predicted_yield, yield_unit)
    drivers = [FeatureDriverOut(**d) for d in drivers_raw]

    record = CropPrediction(
        user_id=current_user.id,
        farm_id=payload.farm_id,
        crop=payload.crop,
        crop_year=payload.crop_year,
        season=payload.season,
        state=payload.state,
        area_hectares=float(payload.area_hectares),
        annual_rainfall_mm=float(payload.annual_rainfall_mm),
        fertilizer_kg=float(payload.fertilizer_kg),
        pesticide_kg=float(payload.pesticide_kg),
        predicted_yield=predicted_yield,
        yield_unit=yield_unit,
        estimated_total_production=estimated_total,
        model_name=model_name,
        model_version=model_version,
        feature_importance_json={
            "drivers": [d.model_dump() for d in drivers],
            "advisory_note": advisory_note,
            "production_unit": production_unit,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Yield prediction id=%s user_id=%s crop=%s state=%s unit=%s",
        record.id,
        current_user.id,
        record.crop,
        record.state,
        record.yield_unit,
    )

    return _record_to_response(record)


def _record_to_response(record: CropPrediction) -> CropYieldResponse:
    meta = record.feature_importance_json or {}
    raw_drivers = meta.get("drivers", [])
    drivers = [FeatureDriverOut(**d) for d in raw_drivers]
    default_prod_unit = "nuts" if record.yield_unit == "nuts/hectare" else "tonnes"
    production_unit = str(meta.get("production_unit") or default_prod_unit)
    advisory_note = str(
        meta.get("advisory_note")
        or f"Leak-free crop yield prediction ({record.model_version}) in {record.yield_unit}."
    )
    estimated_total = (
        float(record.estimated_total_production)
        if record.estimated_total_production is not None
        else round(float(record.predicted_yield) * float(record.area_hectares), 2)
    )

    return CropYieldResponse(
        id=record.id,
        farm_id=record.farm_id,
        crop=record.crop,
        state=record.state,
        season=record.season,
        crop_year=record.crop_year,
        area_hectares=float(record.area_hectares),
        predicted_yield=float(record.predicted_yield),
        yield_unit=record.yield_unit,
        estimated_total_production=estimated_total,
        production_unit=production_unit,
        model_name=record.model_name,
        model_version=record.model_version,
        feature_drivers=drivers,
        advisory_note=advisory_note,
        created_at=record.created_at,
        source_mode="live_api",
    )


def list_yield_history(
    db: Session,
    current_user: User,
    *,
    limit: int = 10,
) -> list[CropYieldResponse]:
    rows = db.scalars(
        select(CropPrediction)
        .where(CropPrediction.user_id == current_user.id)
        .order_by(CropPrediction.created_at.desc())
        .limit(limit)
    ).all()
    return [_record_to_response(r) for r in rows]


def get_crop_yield_registry_status() -> AdminModelStatusItem:
    model_path = _get_model_path()
    metrics = _load_metrics_metadata()

    artifact_exists = model_path.exists() and model_path.is_file()
    if artifact_exists:
        size_mb = model_path.stat().st_size / (1024 * 1024)
        size_str = f"{size_mb:.2f} MB"
    else:
        size_str = "Missing (.joblib)"

    test_metrics = metrics.get("selected_test_metrics", {})
    non_coco = test_metrics.get("non_coconut_tonnes_per_ha")
    coco = test_metrics.get("coconut_nuts_per_ha")
    model_key = str(metrics.get("selected_model_key") or "")

    registry_algo_map = {
        "random_forest_segmented": "Segmented Random Forest (Scale-Invariant, Leak-Free)",
        "xgboost_segmented_native": "Segmented XGBoost (Scale-Invariant, Leak-Free)",
        "xgboost_segmented_log1p": "Segmented XGBoost (log1p Target, Leak-Free)",
        "ridge_segmented": "Segmented Ridge Regression (Scale-Invariant, Leak-Free)",
    }
    algorithm_label = registry_algo_map.get(
        model_key, "Segmented Crop Yield ML Pipeline (Leak-Free)"
    )

    if artifact_exists and non_coco and coco:
        metric_val = (
            f"R² {non_coco['r2']:.4f} | MAE {non_coco['mae']:.2f} t/ha "
            f"(Coconut R² {coco['r2']:.4f})"
        )
        status_label = "Active (Phase 5 Live)"
    elif artifact_exists:
        metric_val = "Artifact loaded (metrics JSON pending)"
        status_label = "Active (Phase 5 Live)"
    else:
        metric_val = "Run python -m ml.training.train_crop_yield"
        status_label = "Artifact Missing"

    return AdminModelStatusItem(
        module="Crop Yield Prediction",
        algorithm=algorithm_label,
        status=status_label,
        metric_label="Chronological Test (2018-2020)",
        metric_value=metric_val,
        artifact_size=size_str,
    )
