import json
import logging
from pathlib import Path
import re
import sys
import threading
from typing import Any
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import _PROJECT_ROOT, get_settings
from app.models.farm import Farm
from app.models.modules import DiseaseDetection
from app.models.user import User
from app.schemas.admin import AdminModelStatusItem
from app.schemas.disease import DiseaseCandidateOut, DiseaseDetectionResponse

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

from ml.preprocessing.disease_features import (  # noqa: E402
    SUPPORTED_SPECIES_CANONICAL,
    get_disease_guidance,
    parse_plantvillage_label,
    validate_and_decode_leaf_image,
)
from ml.preprocessing.disease_model import (  # noqa: E402
    DiseasePredictionOutput,
    PlantDiseasePredictor,
)

logger = logging.getLogger("terraqora.ml.disease")

DEFAULT_MODEL_PATH = _PROJECT_ROOT / "ml" / "saved_models" / "plant_disease_model.pt"
DEFAULT_METRICS_PATH = _PROJECT_ROOT / "ml" / "evaluation" / "disease_metrics.json"

_CACHE_LOCK = threading.Lock()
_cached_predictor: PlantDiseasePredictor | Any | None = None
_cached_model_path: Path | None = None
_model_path_override: Path | None = None
_metrics_path_override: Path | None = None
_predictor_override: Any | None = None


def set_paths_for_testing(
    *, model_path: Path | None = None, metrics_path: Path | None = None
) -> None:
    """Override vision checkpoint/metrics paths in tests and clear singleton cache."""
    global _cached_predictor, _cached_model_path, _model_path_override, _metrics_path_override
    with _CACHE_LOCK:
        _model_path_override = model_path
        _metrics_path_override = metrics_path
        _cached_predictor = None
        _cached_model_path = None


def set_predictor_for_testing(predictor: Any | None) -> None:
    """Allow automated tests to inject a deterministic vision predictor cleanly."""
    global _predictor_override
    with _CACHE_LOCK:
        _predictor_override = predictor


def reset_cache() -> None:
    set_paths_for_testing(model_path=None, metrics_path=None)
    set_predictor_for_testing(None)


def _get_model_path() -> Path:
    return _model_path_override if _model_path_override is not None else DEFAULT_MODEL_PATH


def _get_metrics_path() -> Path:
    return (
        _metrics_path_override
        if _metrics_path_override is not None
        else DEFAULT_METRICS_PATH
    )


def _load_metrics_metadata() -> dict[str, Any]:
    metrics_path = _get_metrics_path()
    if not metrics_path.exists() or not metrics_path.is_file():
        return {}
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not parse plant disease metrics JSON cleanly.")
        return {}


def _get_loaded_predictor() -> PlantDiseasePredictor | Any:
    global _cached_predictor, _cached_model_path

    with _CACHE_LOCK:
        if _predictor_override is not None:
            return _predictor_override

        model_path = _get_model_path()
        if _cached_predictor is not None and _cached_model_path == model_path:
            return _cached_predictor

        if not model_path.exists() or not model_path.is_file():
            logger.warning("Plant disease vision artifact missing at expected location.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Plant disease vision model is currently unavailable. "
                    "Run python -m ml.audit_plant_disease and python -m ml.training.train_plant_disease first."
                ),
            )

        try:
            loaded = PlantDiseasePredictor.from_checkpoint(model_path)
        except Exception as exc:
            logger.exception(
                "Failed to load plant disease vision model safely: %s", type(exc).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plant disease vision model artifact could not be loaded safely.",
            ) from exc

        _cached_predictor = loaded
        _cached_model_path = model_path
        return _cached_predictor


def _sanitize_filename(filename: str | None) -> str:
    raw = Path(filename or "leaf_upload.jpg").name
    cleaned = re.sub(r"[^\w.\- ]+", "_", raw).strip()
    return (cleaned or "leaf_upload.jpg")[:255]


def _verify_farm_ownership(
    db: Session, current_user: User, farm_id: uuid.UUID
) -> Farm:
    farm = db.get(Farm, farm_id)
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
    return farm


def detect_plant_disease(
    db: Session,
    current_user: User,
    *,
    image_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    crop_hint: str | None = None,
    farm_id: uuid.UUID | None = None,
) -> DiseaseDetectionResponse:
    settings = get_settings()
    max_bytes = int(settings.MAX_UPLOAD_IMAGE_MB) * 1024 * 1024

    if farm_id is not None:
        farm = _verify_farm_ownership(db, current_user, farm_id)
        if not crop_hint and farm.primary_crop:
            crop_hint = farm.primary_crop

    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image exceeds the {settings.MAX_UPLOAD_IMAGE_MB} MB upload limit.",
        )

    try:
        validated = validate_and_decode_leaf_image(
            image_bytes,
            declared_mime=content_type,
            max_bytes=max_bytes,
        )
    except ValueError as exc:
        msg = str(exc)
        err_status = (
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            if "Unsupported media type" in msg or "Unsupported image format" in msg
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=err_status, detail=msg) from exc

    predictor = _get_loaded_predictor()
    metrics_meta = _load_metrics_metadata()
    fallback_version = str(metrics_meta.get("model_version") or "phase7-vision-v1.0.0")[:32]

    try:
        pred: DiseasePredictionOutput = predictor.predict(
            validated,
            crop_hint=crop_hint,
            confidence_threshold=float(settings.DISEASE_CONFIDENCE_THRESHOLD),
            min_margin=float(settings.DISEASE_MIN_MARGIN),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Plant disease inference failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plant disease screening inference failed safely.",
        ) from exc

    safe_filename = _sanitize_filename(filename)
    model_version = (pred.model_version or fallback_version)[:32]
    top_candidates = [
        DiseaseCandidateOut(label=str(c["label"]), confidence=float(c["confidence"]))
        for c in pred.top_predictions
    ]

    record = DiseaseDetection(
        user_id=current_user.id,
        farm_id=farm_id,
        crop_hint=crop_hint.strip()[:80] if crop_hint and crop_hint.strip() else None,
        image_filename=safe_filename,
        image_mime_type=validated.detected_mime[:64],
        image_size_bytes=validated.size_bytes,
        image_sha256=validated.sha256,
        predicted_label=pred.predicted_label[:120],
        confidence=float(pred.confidence),
        is_uncertain=bool(pred.is_uncertain),
        top_predictions_json=[c.model_dump() for c in top_candidates],
        treatment_summary=pred.treatment_summary,
        prevention_notes=pred.prevention_notes,
        model_version=model_version,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Disease scan id=%s user_id=%s label=%s conf=%.4f uncertain=%s",
        record.id,
        current_user.id,
        record.predicted_label,
        record.confidence,
        record.is_uncertain,
    )

    return DiseaseDetectionResponse(
        id=record.id,
        farm_id=record.farm_id,
        crop_hint=record.crop_hint,
        image_filename=record.image_filename,
        predicted_label=record.predicted_label,
        crop_name=pred.crop_name,
        disease_name=pred.disease_name,
        is_healthy=pred.is_healthy,
        confidence=round(float(record.confidence), 4),
        top2_margin=pred.top2_margin,
        is_uncertain=bool(record.is_uncertain),
        uncertainty_reason=pred.uncertainty_reason,
        top_predictions=top_candidates,
        treatment_summary=record.treatment_summary,
        prevention_notes=record.prevention_notes or "",
        next_steps=pred.next_steps,
        limitations=pred.limitations,
        supported_scope_note=pred.supported_scope_note,
        model_version=record.model_version,
        created_at=record.created_at,
        source_mode="live_api",
    )


def _record_to_response(record: DiseaseDetection) -> DiseaseDetectionResponse:
    raw_top = record.top_predictions_json or []
    top_candidates = [
        DiseaseCandidateOut(
            label=str(item.get("label", "Unknown")),
            confidence=float(item.get("confidence", 0.0)),
        )
        for item in raw_top
        if isinstance(item, dict)
    ]

    primary_label = top_candidates[0].label if top_candidates else record.predicted_label
    crop_name, disease_name, is_healthy = parse_plantvillage_label(primary_label)
    if record.is_uncertain:
        if "Out_Of_Scope_Crop" in record.predicted_label:
            disease_name = "Uncertain / Unsupported Crop"
        else:
            disease_name = f"Uncertain Screening (Closest match: {crop_name} — {disease_name})"
        is_healthy = False
        if record.crop_hint and "Out_Of_Scope_Crop" in record.predicted_label:
            crop_name = record.crop_hint

    guidance = get_disease_guidance(primary_label, is_uncertain=bool(record.is_uncertain))
    margin = (
        round(top_candidates[0].confidence - top_candidates[1].confidence, 4)
        if len(top_candidates) >= 2
        else None
    )

    uncertainty_reason = (
        f"Saved screening was marked uncertain ({float(record.confidence) * 100:.1f}% calibrated confidence); verify physically with KVK."
        if record.is_uncertain
        else None
    )

    scope_note = (
        f"PlantVillage 38-class vision scope covers {len(SUPPORTED_SPECIES_CANONICAL)} crop species only."
    )

    return DiseaseDetectionResponse(
        id=record.id,
        farm_id=record.farm_id,
        crop_hint=record.crop_hint,
        image_filename=record.image_filename,
        predicted_label=record.predicted_label,
        crop_name=crop_name,
        disease_name=disease_name,
        is_healthy=is_healthy,
        confidence=round(float(record.confidence), 4),
        top2_margin=margin,
        is_uncertain=bool(record.is_uncertain),
        uncertainty_reason=uncertainty_reason,
        top_predictions=top_candidates,
        treatment_summary=record.treatment_summary,
        prevention_notes=record.prevention_notes or guidance["prevention_notes"],
        next_steps=guidance["next_steps"],
        limitations=[
            "Vision screening aid only; confirm field diagnoses with a local extension officer or KVK before chemical intervention."
        ],
        supported_scope_note=scope_note,
        model_version=record.model_version,
        created_at=record.created_at,
        source_mode="live_api",
    )


def list_disease_history(
    db: Session,
    current_user: User,
    *,
    limit: int = 10,
) -> list[DiseaseDetectionResponse]:
    rows = db.scalars(
        select(DiseaseDetection)
        .where(DiseaseDetection.user_id == current_user.id)
        .order_by(DiseaseDetection.created_at.desc())
        .limit(limit)
    ).all()
    return [_record_to_response(row) for row in rows]


def get_disease_registry_status() -> AdminModelStatusItem:
    model_path = _get_model_path()
    metrics = _load_metrics_metadata()
    artifact_exists = model_path.exists() and model_path.is_file()

    if artifact_exists:
        size_kb = model_path.stat().st_size / 1024
        size_str = f"{size_kb / 1024:.2f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
    else:
        size_str = "Missing (.pt)"

    algo = str(
        metrics.get("selected_algorithm")
        or "EfficientNet-B0 Transfer Learning (ImageNet)"
    )
    test_m = metrics.get("selected_test_metrics", {})

    if artifact_exists and test_m:
        metric_val = (
            f"Acc {test_m['accuracy']:.4f} | Macro-F1 {test_m['macro_f1']:.4f} "
            f"(ECE {test_m['ece_10bin']:.4f})"
        )
        status_label = "Active (Phase 7 Live)"
    elif artifact_exists:
        metric_val = "Artifact loaded (metrics JSON pending)"
        status_label = "Active (Phase 7 Live)"
    else:
        metric_val = "Run python -m ml.training.train_plant_disease"
        status_label = "Artifact Missing"

    return AdminModelStatusItem(
        module="Plant Disease Vision",
        algorithm=algo,
        status=status_label,
        metric_label="Deduplicated Test (38 Classes)",
        metric_value=metric_val,
        artifact_size=size_str,
    )
