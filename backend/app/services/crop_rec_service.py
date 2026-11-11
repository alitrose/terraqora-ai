import json
import logging
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
from app.models.modules import CropRecommendation
from app.models.user import User
from app.schemas.admin import AdminModelStatusItem
from app.schemas.recommendations import (
    CropCandidateOut,
    CropRecommendationRequest,
    CropRecommendationResponse,
)

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

from ml.preprocessing.crop_rec_features import RAW_CROP_REC_FEATURES  # noqa: E402

logger = logging.getLogger("terraqora.ml.crop_recommendation")

DEFAULT_MODEL_PATH = (
    _PROJECT_ROOT / "ml" / "saved_models" / "crop_recommendation_model.joblib"
)
DEFAULT_METRICS_PATH = (
    _PROJECT_ROOT / "ml" / "evaluation" / "crop_rec_metrics.json"
)

_CACHE_LOCK = threading.Lock()
_cached_model: Any | None = None
_cached_model_path: Path | None = None
_model_path_override: Path | None = None
_metrics_path_override: Path | None = None


def set_paths_for_testing(
    *, model_path: Path | None = None, metrics_path: Path | None = None
) -> None:
    """Override artifact/metrics paths in automated tests and clear cached classifier."""
    global _cached_model, _cached_model_path, _model_path_override, _metrics_path_override
    with _CACHE_LOCK:
        _model_path_override = model_path
        _metrics_path_override = metrics_path
        _cached_model = None
        _cached_model_path = None


def reset_cache() -> None:
    set_paths_for_testing(model_path=None, metrics_path=None)


def _get_model_path() -> Path:
    return _model_path_override if _model_path_override is not None else DEFAULT_MODEL_PATH


def _get_metrics_path() -> Path:
    return (
        _metrics_path_override if _metrics_path_override is not None else DEFAULT_METRICS_PATH
    )


def _load_metrics_metadata() -> dict[str, Any]:
    metrics_path = _get_metrics_path()
    if not metrics_path.exists() or not metrics_path.is_file():
        return {}
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not parse crop recommendation metrics JSON cleanly.")
        return {}


def _get_loaded_model() -> Any:
    global _cached_model, _cached_model_path
    model_path = _get_model_path()

    with _CACHE_LOCK:
        if _cached_model is not None and _cached_model_path == model_path:
            return _cached_model

        if not model_path.exists() or not model_path.is_file():
            logger.warning("Crop recommendation artifact missing at expected location.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Crop recommendation model is currently unavailable. Run python -m ml.training.train_crop_recommendation before requesting recommendations.",
            )

        try:
            loaded = joblib.load(model_path)
        except Exception as exc:
            logger.exception(
                "Failed to load crop recommendation model artifact: %s", type(exc).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Crop recommendation model could not be loaded safely.",
            ) from exc

        if not hasattr(loaded, "predict_proba") or not hasattr(loaded, "top_k_candidates"):
            logger.error("Loaded crop recommendation artifact lacks required methods.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Crop recommendation model artifact is invalid.",
            )

        _cached_model = loaded
        _cached_model_path = model_path
        return _cached_model


def _build_soil_climate_summary(
    *,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    temperature_c: float,
    humidity_pct: float,
    soil_ph: float,
    rainfall_mm: float,
    season: str | None,
    region: str | None,
) -> str:
    context_parts = [p for p in (season, region) if p]
    context_note = (
        f" Context noted ({', '.join(context_parts)}); ranking is computed strictly from the 7 validated soil & climate features in Crop_recommendation.csv."
        if context_note_needed(context_parts)
        else " Ranked strictly from the 7 validated soil & climate features across 22 benchmark crops."
    )
    return (
        f"Evaluated soil NPK ({nitrogen:.0f}-{phosphorus:.0f}-{potassium:.0f}), "
        f"pH {soil_ph:.1f}, {temperature_c:.1f}°C, {humidity_pct:.0f}% humidity, "
        f"and {rainfall_mm:.0f} mm rainfall.{context_note}"
    )


def context_note_needed(context_parts: list[str]) -> bool:
    return len(context_parts) > 0


def recommend_crop(
    db: Session,
    current_user: User,
    payload: CropRecommendationRequest,
) -> CropRecommendationResponse:
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
    model_version = str(metrics_meta.get("model_version") or "phase5b-crop-v1.0.0")[:32]

    row_df = pd.DataFrame(
        [
            {
                "N": float(payload.nitrogen),
                "P": float(payload.phosphorus),
                "K": float(payload.potassium),
                "temperature": float(payload.temperature_c),
                "humidity": float(payload.humidity_pct),
                "ph": float(payload.soil_ph),
                "rainfall": float(payload.rainfall_mm),
            }
        ],
        columns=RAW_CROP_REC_FEATURES,
    )

    try:
        candidates_raw = model.top_k_candidates(row_df, k=3)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Crop recommendation inference failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Crop recommendation inference failed safely.",
        ) from exc

    candidates = [CropCandidateOut(**item) for item in candidates_raw]
    top_crop = candidates[0].crop[:80]

    record = CropRecommendation(
        user_id=current_user.id,
        farm_id=payload.farm_id,
        nitrogen=float(payload.nitrogen),
        phosphorus=float(payload.phosphorus),
        potassium=float(payload.potassium),
        temperature_c=float(payload.temperature_c),
        humidity_pct=float(payload.humidity_pct),
        soil_ph=float(payload.soil_ph),
        rainfall_mm=float(payload.rainfall_mm),
        season=payload.season,
        region=payload.region,
        recommended_crop=top_crop,
        top_candidates_json=[c.model_dump() for c in candidates],
        model_version=model_version,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Crop recommendation id=%s user_id=%s recommended_crop=%s",
        record.id,
        current_user.id,
        record.recommended_crop,
    )
    return _record_to_response(record)


def _record_to_response(record: CropRecommendation) -> CropRecommendationResponse:
    candidates = [CropCandidateOut(**item) for item in (record.top_candidates_json or [])]
    summary = _build_soil_climate_summary(
        nitrogen=float(record.nitrogen),
        phosphorus=float(record.phosphorus),
        potassium=float(record.potassium),
        temperature_c=float(record.temperature_c),
        humidity_pct=float(record.humidity_pct),
        soil_ph=float(record.soil_ph),
        rainfall_mm=float(record.rainfall_mm),
        season=record.season,
        region=record.region,
    )
    return CropRecommendationResponse(
        id=record.id,
        farm_id=record.farm_id,
        nitrogen=float(record.nitrogen),
        phosphorus=float(record.phosphorus),
        potassium=float(record.potassium),
        temperature_c=float(record.temperature_c),
        humidity_pct=float(record.humidity_pct),
        soil_ph=float(record.soil_ph),
        rainfall_mm=float(record.rainfall_mm),
        season=record.season,
        region=record.region,
        recommended_crop=record.recommended_crop,
        top_candidates=candidates,
        soil_climate_summary=summary,
        model_version=record.model_version,
        created_at=record.created_at,
        source_mode="live_api",
    )


def list_crop_recommendation_history(
    db: Session,
    current_user: User,
    *,
    limit: int = 10,
) -> list[CropRecommendationResponse]:
    rows = db.scalars(
        select(CropRecommendation)
        .where(CropRecommendation.user_id == current_user.id)
        .order_by(CropRecommendation.created_at.desc())
        .limit(limit)
    ).all()
    return [_record_to_response(r) for r in rows]


def get_crop_rec_registry_status() -> AdminModelStatusItem:
    model_path = _get_model_path()
    metrics = _load_metrics_metadata()
    artifact_exists = model_path.exists() and model_path.is_file()

    if artifact_exists:
        size_kb = model_path.stat().st_size / 1024
        size_str = f"{size_kb / 1024:.2f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
    else:
        size_str = "Missing (.joblib)"

    cv5 = metrics.get("selected_cv5_dev", {})
    test_m = metrics.get("selected_test_metrics", {})
    algo = str(metrics.get("selected_algorithm") or "Gaussian Naive Bayes (22 Crops)")

    if artifact_exists and cv5 and test_m:
        metric_val = (
            f"Acc {test_m['accuracy']:.4f} | Macro-F1 {test_m['macro_f1']:.4f} "
            f"(5-Fold CV {cv5['accuracy_mean']:.4f})"
        )
        status_label = "Active (Phase 5b Live)"
    elif artifact_exists:
        metric_val = "Artifact loaded (metrics JSON pending)"
        status_label = "Active (Phase 5b Live)"
    else:
        metric_val = "Run python -m ml.training.train_crop_recommendation"
        status_label = "Artifact Missing"

    return AdminModelStatusItem(
        module="Crop Recommendation",
        algorithm=algo,
        status=status_label,
        metric_label="Stratified Held-Out Test (440 rows)",
        metric_value=metric_val,
        artifact_size=size_str,
    )
