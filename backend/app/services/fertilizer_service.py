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
from app.models.modules import FertilizerRecommendation
from app.models.user import User
from app.schemas.admin import AdminModelStatusItem
from app.schemas.recommendations import (
    FertilizerRequest,
    FertilizerResponse,
    NutrientLevelOut,
)

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

from ml.preprocessing.fertilizer_features import (  # noqa: E402
    NPK_CSV_FEATURE_COLUMNS,
    assess_soil_balance,
    harmonize_crop_type,
    harmonize_soil_type,
)

logger = logging.getLogger("terraqora.ml.fertilizer")

DEFAULT_MODEL_PATH = _PROJECT_ROOT / "ml" / "saved_models" / "fertilizer_model.joblib"
DEFAULT_METRICS_PATH = _PROJECT_ROOT / "ml" / "evaluation" / "fertilizer_metrics.json"

_CACHE_LOCK = threading.Lock()
_cached_model: Any | None = None
_cached_model_path: Path | None = None
_model_path_override: Path | None = None
_metrics_path_override: Path | None = None

EXPERT_DISCLAIMER = (
    "Qualitative formulation guidance only — chemical application rates (kg/ha or g/plant) "
    "are intentionally NOT calculated because soil lab bulk density, crop variety, organic carbon, "
    "and target yield calibration are absent from the public training dataset. Validate exact doses "
    "with an accredited Soil Health Card laboratory test and your local Krishi Vigyan Kendra (KVK)."
)


def set_paths_for_testing(
    *, model_path: Path | None = None, metrics_path: Path | None = None
) -> None:
    """Override model/metrics paths in automated tests and clear cached classifier."""
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
        logger.warning("Could not parse fertilizer metrics JSON cleanly.")
        return {}


def _get_loaded_model() -> Any:
    global _cached_model, _cached_model_path
    model_path = _get_model_path()

    with _CACHE_LOCK:
        if _cached_model is not None and _cached_model_path == model_path:
            return _cached_model

        if not model_path.exists() or not model_path.is_file():
            logger.warning("Fertilizer model artifact missing at expected location.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fertilizer classification model is currently unavailable. Run python -m ml.training.train_fertilizer before requesting recommendations.",
            )

        try:
            loaded = joblib.load(model_path)
        except Exception as exc:
            logger.exception(
                "Failed to load fertilizer model artifact: %s", type(exc).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fertilizer classification model could not be loaded safely.",
            ) from exc

        if not hasattr(loaded, "predict_grade_with_confidence"):
            logger.error("Loaded fertilizer artifact lacks predict_grade_with_confidence().")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fertilizer model artifact is invalid.",
            )

        _cached_model = loaded
        _cached_model_path = model_path
        return _cached_model


def recommend_fertilizer(
    db: Session,
    current_user: User,
    payload: FertilizerRequest,
) -> FertilizerResponse:
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

    # Always validate ML artifact availability cleanly so missing/corrupt artifacts fail closed (503).
    model = _get_loaded_model()
    metrics_meta = _load_metrics_metadata()
    model_version = str(metrics_meta.get("model_version") or "phase5b-fert-v1.0.0")[:32]

    balance = assess_soil_balance(
        nitrogen=float(payload.nitrogen),
        phosphorus=float(payload.phosphorus),
        potassium=float(payload.potassium),
        soil_ph=float(payload.soil_ph),
    )
    mapped_soil, soil_exact = harmonize_soil_type(payload.soil_type)
    mapped_crop, crop_covered = harmonize_crop_type(payload.crop_type)

    coverage_parts = []
    if soil_exact:
        coverage_parts.append(f"Soil texture '{payload.soil_type}' aligns directly with dataset class '{mapped_soil}'.")
    else:
        coverage_parts.append(
            f"Soil texture '{payload.soil_type}' mapped qualitatively to '{mapped_soil}' (public dataset covers 5 benchmark textures: Loamy, Black, Red, Sandy, Clayey)."
        )
    if crop_covered:
        coverage_parts.append(f"Crop '{payload.crop_type}' falls within the 11 dataset crop groups ('{mapped_crop}').")
    else:
        coverage_parts.append(
            f"Crop '{payload.crop_type}' is outside the 11 crops represented in Fertilizer_Prediction.csv; grade selection relies on ICAR macronutrient balance rules without crop-specific trial calibration."
        )
    dataset_coverage_note = " ".join(coverage_parts)

    region_note = payload.location or "Regional profile"
    deficits: list[str] = balance["deficits"]
    surpluses: list[str] = balance["surpluses"]

    if not balance["has_any_deficit"]:
        # Conservative Agronomic Sufficiency Guardrail: do not push synthetic chemical NPK escalation
        rec_mode = "agronomic_sufficiency_guardrail"
        ml_grade = None
        recommended_fert = "Soil Nutrients Sufficient — Organic Maintenance Only"
        confidence = 1.0
        surplus_text = (
            f" Elevated readings observed for {', '.join(surpluses)} — avoid unnecessary mineral inputs to prevent leaching or salinity stress."
            if surpluses
            else ""
        )
        advisory_notes = (
            f"Rule Guardrail Active ({payload.crop_type} on {payload.soil_type}, {region_note}): "
            f"All measured macronutrients meet or exceed baseline sufficiency thresholds.{surplus_text} "
            "Maintain organic compost/residue incorporation and verify crop-stage maintenance needs with a local KVK Soil Health Card test."
        )
    else:
        sig = balance["demand_signature"]
        row_df = pd.DataFrame(
            [
                {
                    "Nitrogen": sig["Nitrogen"],
                    "Phosphorus": sig["Phosphorus"],
                    "Potassium": sig["Potassium"],
                }
            ],
            columns=NPK_CSV_FEATURE_COLUMNS,
        )
        try:
            ml_grade, confidence, top_alts = model.predict_grade_with_confidence(row_df)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Fertilizer ML grade inference failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Fertilizer classification failed safely.",
            ) from exc

        rec_mode = "ml_grade_with_agronomic_guardrails"
        recommended_fert = ml_grade[:100]

        notes = [
            f"ML Grade Classifier + Agronomic Balancing ({payload.crop_type} on {payload.soil_type}, {region_note}): Detected low status in {', '.join(deficits)}.",
            f"Classifier matched deficit signature to '{ml_grade}' ({confidence * 100:.0f}% model probability).",
        ]
        if deficits == ["Potassium (K)"]:
            notes.append(
                "Note: Fertilizer_Prediction.csv's 7 grade labels exclude straight Potash (MOP 0-0-60); "
                "10-26-26 is the closest K-enriched dataset grade, though a soil-test-guided straight potassium source may avoid surplus N/P buildup."
            )
        if confidence < 0.75 and len(top_alts) > 1:
            alt_desc = ", ".join(
                f"{a['fertilizer']} ({a['probability'] * 100:.0f}%)" for a in top_alts[1:]
            )
            notes.append(f"Alternative dataset grade candidates: {alt_desc}.")
        if surpluses:
            notes.append(
                f"Avoid excess inputs for currently elevated nutrient(s): {', '.join(surpluses)}."
            )
        notes.append(
            "Consider split nutrient timing across basal and active vegetative stages to reduce nutrient loss, confirming field rates via local KVK testing."
        )
        advisory_notes = " ".join(notes)

    nutrient_levels = [NutrientLevelOut(**n) for n in balance["nutrient_levels"]]

    record = FertilizerRecommendation(
        user_id=current_user.id,
        farm_id=payload.farm_id,
        nitrogen=float(payload.nitrogen),
        phosphorus=float(payload.phosphorus),
        potassium=float(payload.potassium),
        soil_ph=float(payload.soil_ph),
        soil_type=payload.soil_type,
        crop_type=payload.crop_type,
        location=payload.location,
        recommended_fertilizer=recommended_fert,
        confidence=float(confidence),
        nutrient_status_json={
            "nutrient_levels": [n.model_dump() for n in nutrient_levels],
            "ph_assessment": balance["ph_assessment"],
            "ml_predicted_grade": ml_grade,
            "recommendation_mode": rec_mode,
            "dataset_coverage_note": dataset_coverage_note,
        },
        advisory_notes=advisory_notes,
        expert_disclaimer=EXPERT_DISCLAIMER,
        model_version=model_version,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Fertilizer recommendation id=%s user_id=%s mode=%s result=%s",
        record.id,
        current_user.id,
        rec_mode,
        record.recommended_fertilizer,
    )
    return _record_to_response(record)


def _record_to_response(record: FertilizerRecommendation) -> FertilizerResponse:
    meta = record.nutrient_status_json or {}
    levels = [NutrientLevelOut(**n) for n in meta.get("nutrient_levels", [])]
    ph_assessment = str(
        meta.get("ph_assessment")
        or f"Soil pH recorded at {float(record.soil_ph):.1f}."
    )
    rec_mode = meta.get("recommendation_mode") or "ml_grade_with_agronomic_guardrails"
    if rec_mode not in (
        "ml_grade_with_agronomic_guardrails",
        "agronomic_sufficiency_guardrail",
    ):
        rec_mode = "ml_grade_with_agronomic_guardrails"
    ml_grade = meta.get("ml_predicted_grade")
    coverage_note = str(
        meta.get("dataset_coverage_note")
        or "Evaluated against the 7-class Fertilizer_Prediction.csv grade model and ICAR NPK screening bands."
    )

    return FertilizerResponse(
        id=record.id,
        farm_id=record.farm_id,
        nitrogen=float(record.nitrogen),
        phosphorus=float(record.phosphorus),
        potassium=float(record.potassium),
        soil_ph=float(record.soil_ph),
        soil_type=record.soil_type,
        crop_type=record.crop_type,
        location=record.location,
        recommended_fertilizer=record.recommended_fertilizer,
        confidence=float(record.confidence if record.confidence is not None else 1.0),
        ml_predicted_grade=str(ml_grade) if ml_grade is not None else None,
        recommendation_mode=rec_mode,
        dataset_coverage_note=coverage_note,
        nutrient_levels=levels,
        ph_assessment=ph_assessment,
        advisory_notes=record.advisory_notes,
        expert_disclaimer=record.expert_disclaimer,
        model_version=record.model_version,
        created_at=record.created_at,
        source_mode="live_api",
    )


def list_fertilizer_history(
    db: Session,
    current_user: User,
    *,
    limit: int = 10,
) -> list[FertilizerResponse]:
    rows = db.scalars(
        select(FertilizerRecommendation)
        .where(FertilizerRecommendation.user_id == current_user.id)
        .order_by(FertilizerRecommendation.created_at.desc())
        .limit(limit)
    ).all()
    return [_record_to_response(r) for r in rows]


def get_fertilizer_registry_status() -> AdminModelStatusItem:
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
    algo = str(
        metrics.get("selected_algorithm")
        or "Logistic Regression (NPK Grade) + ICAR Agronomic Guardrails"
    )

    if artifact_exists and cv5 and test_m:
        metric_val = (
            f"Macro-F1 {test_m['macro_f1']:.4f} | Acc {test_m['accuracy']:.4f} "
            f"(5-Fold CV {cv5['accuracy_mean']:.4f})"
        )
        status_label = "Active (Phase 5b Live)"
    elif artifact_exists:
        metric_val = "Artifact loaded (metrics JSON pending)"
        status_label = "Active (Phase 5b Live)"
    else:
        metric_val = "Run python -m ml.training.train_fertilizer"
        status_label = "Artifact Missing"

    return AdminModelStatusItem(
        module="Fertilizer Recommendation",
        algorithm=algo,
        status=status_label,
        metric_label="Stratified Held-Out Test (99-row Dataset)",
        metric_value=metric_val,
        artifact_size=size_str,
    )
