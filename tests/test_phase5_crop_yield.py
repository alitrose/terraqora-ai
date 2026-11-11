import json
import math
import os
from pathlib import Path
import secrets
import sys
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import joblib
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

from app.core.config import get_settings  # noqa: E402
from app.db.session import build_engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import CropPrediction, User  # noqa: E402
from app.services import crop_yield_service  # noqa: E402
from ml.preprocessing.crop_yield_features import (  # noqa: E402
    RAW_FEATURE_COLUMNS,
    VALID_CROPS,
    VALID_SEASONS,
    VALID_STATES,
    YieldFeatureEngineer,
    canonicalize_crop,
    canonicalize_season,
    canonicalize_state,
    clean_crop_yield_dataframe,
)
from ml.preprocessing.crop_yield_model import compute_feature_drivers  # noqa: E402

AUDIT_JSON = ROOT / "ml" / "evaluation" / "crop_yield_audit.json"
METRICS_JSON = ROOT / "ml" / "evaluation" / "crop_yield_metrics.json"
MODEL_JOBLIB = ROOT / "ml" / "saved_models" / "crop_yield_model.joblib"


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture()
def isolated_api_client(tmp_path: Path):
    db_file = tmp_path / "phase5_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
    crop_yield_service.reset_cache()
    command.upgrade(_make_alembic_config(db_url), "head")

    engine = build_engine(db_url)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal

    crop_yield_service.reset_cache()
    app.dependency_overrides.clear()
    engine.dispose()


def _register_user(
    client: TestClient,
    *,
    email: str,
    full_name: str = "Test Farmer",
    password: str = "HarvestPass#2026",
) -> tuple[dict[str, str], dict]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "preferred_language": "en",
            "state": "Tamil Nadu",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    return headers, body["user"]


def test_audit_and_leakage_findings():
    assert AUDIT_JSON.exists(), "Stage 1 crop_yield_audit.json is missing."
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))

    assert audit["shape"]["rows"] == 19689
    assert audit["shape"]["columns"] == 10
    assert all(v == 0 for v in audit["missing_values"].values())
    assert audit["duplicates"]["raw_exact"] == 0
    assert audit["cardinality_after_trim"]["Crop"] == 55
    assert audit["cardinality_after_trim"]["State"] == 30
    assert audit["cardinality_after_trim"]["Season"] == 6
    assert audit["target_leakage_audit"]["pearson_r_prod_per_area_vs_yield_all"] > 0.99
    assert audit["yield_distribution_coconut"]["median"] > 5000
    assert audit["yield_distribution_non_coconut"]["median"] < 5.0


def test_canonicalization_and_preprocessing_guardrails():
    assert canonicalize_crop("  rice ") == "Rice"
    assert canonicalize_crop("Coconut ") == "Coconut"
    assert canonicalize_crop("Other Rabi pulses") == "Other  Rabi pulses"
    assert canonicalize_state("tamil nadu ") == "Tamil Nadu"
    assert canonicalize_season(" kharif ") == "Kharif"

    with pytest.raises(ValueError, match="Unsupported crop"):
        canonicalize_crop("MarsWheat")
    with pytest.raises(ValueError, match="Unsupported state"):
        canonicalize_state("Atlantis")
    with pytest.raises(ValueError, match="Unsupported season"):
        canonicalize_season("Monsoon")

    valid_df = pd.DataFrame(
        [
            {
                "Crop": "Rice",
                "Crop_Year": 2024,
                "Season": "Kharif ",
                "State": "Tamil Nadu",
                "Area": 5.0,
                "Annual_Rainfall": 1100.0,
                "Fertilizer": 750.0,
                "Pesticide": 15.0,
            }
        ]
    )
    cleaned = clean_crop_yield_dataframe(valid_df)
    assert cleaned["Season"].iloc[0] == "Kharif"

    # Explicit target leakage rejection
    for col in ("Production", "production"):
        leaking_df = valid_df.copy()
        leaking_df[col] = 5000.0
        with pytest.raises(ValueError, match="Target leakage error"):
            clean_crop_yield_dataframe(leaking_df)

    # Bad physical inputs rejected
    zero_area = valid_df.copy()
    zero_area["Area"] = 0.0
    with pytest.raises(ValueError, match="Area"):
        clean_crop_yield_dataframe(zero_area)

    neg_rain = valid_df.copy()
    neg_rain["Annual_Rainfall"] = -10.0
    with pytest.raises(ValueError, match="negative"):
        clean_crop_yield_dataframe(neg_rain)

    eng = YieldFeatureEngineer().fit_transform(valid_df)
    assert "log_area" not in eng.columns
    assert "Area" not in eng.columns
    assert "Fertilizer" not in eng.columns
    assert math.isclose(eng["fertilizer_per_ha"].iloc[0], 150.0, rel_tol=1e-6)
    assert math.isclose(eng["pesticide_per_ha"].iloc[0], 3.0, rel_tol=1e-6)
    assert math.isclose(
        eng["rain_x_fert_per_ha"].iloc[0],
        np.log1p(1100.0) * np.log1p(150.0),
        rel_tol=1e-6,
    )


def test_serialized_model_metrics_and_all_55_crops_inference():
    assert METRICS_JSON.exists(), "crop_yield_metrics.json missing."
    assert MODEL_JOBLIB.exists(), "crop_yield_model.joblib missing — run ml.training.train_crop_yield."

    size_mb = MODEL_JOBLIB.stat().st_size / (1024 * 1024)
    assert size_mb < 15.0, f"Artifact exceeds size target: {size_mb:.2f} MB"

    metrics = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
    assert metrics["split_strategy"]["type"] == "chronological"
    assert metrics["dataset"]["dropped_leakage_columns"] == ["Production"]

    sel_test = metrics["selected_test_metrics"]
    assert sel_test["non_coconut_tonnes_per_ha"]["r2"] > 0.65
    assert sel_test["coconut_nuts_per_ha"]["r2"] > 0.65

    # Ensure segmented winner outperforms unified ridge and dummy baseline on Non-Coconut validation
    winner_key = metrics["selected_model_key"]
    benches = metrics["benchmarks"]
    assert (
        benches[winner_key]["validation_metrics"]["non_coconut_tonnes_per_ha"]["rmse"]
        < benches["dummy_median_segmented"]["validation_metrics"]["non_coconut_tonnes_per_ha"]["rmse"]
    )
    assert (
        benches[winner_key]["validation_metrics"]["non_coconut_tonnes_per_ha"]["rmse"]
        < benches["xgboost_unified"]["validation_metrics"]["non_coconut_tonnes_per_ha"]["rmse"]
    )

    model = joblib.load(MODEL_JOBLIB)
    batch_rows = pd.DataFrame(
        [
            {
                "Crop": crop,
                "Crop_Year": 2019,
                "Season": "Whole Year" if crop == "Coconut" else "Kharif",
                "State": "Kerala" if crop == "Coconut" else "Tamil Nadu",
                "Area": 5.0,
                "Annual_Rainfall": 1200.0,
                "Fertilizer": 725.0,
                "Pesticide": 2.0,
            }
            for crop in VALID_CROPS
        ],
        columns=RAW_FEATURE_COLUMNS,
    )
    preds = model.predict(batch_rows)
    assert len(preds) == len(VALID_CROPS) == 55
    assert np.all(np.isfinite(preds))
    assert np.all(preds >= 0.0)

    coco_idx = VALID_CROPS.index("Coconut")
    rice_idx = VALID_CROPS.index("Rice")
    assert preds[coco_idx] > 1000.0, "Coconut prediction should be in nuts/ha scale"
    assert 0.5 < preds[rice_idx] < 15.0, "Rice prediction should be in tonnes/ha scale"

    # Smallholder vs macro scale invariance check (fixed 150 kg/ha nutrient dose)
    scale_df = pd.DataFrame(
        [
            {
                "Crop": c,
                "Crop_Year": 2019,
                "Season": "Kharif" if c == "Rice" else "Whole Year",
                "State": "Kerala" if c == "Coconut" else "Uttar Pradesh" if c == "Sugarcane" else "Tamil Nadu",
                "Area": area,
                "Annual_Rainfall": 2400.0 if c == "Coconut" else 1100.0,
                "Fertilizer": 150.0 * area,
                "Pesticide": 0.4 * area,
            }
            for c in ("Rice", "Sugarcane", "Coconut")
            for area in (1.0, 50000.0)
        ],
        columns=RAW_FEATURE_COLUMNS,
    )
    scale_preds = model.predict(scale_df)
    assert math.isclose(scale_preds[0], scale_preds[1], rel_tol=1e-5)
    assert math.isclose(scale_preds[2], scale_preds[3], rel_tol=1e-5)
    assert math.isclose(scale_preds[4], scale_preds[5], rel_tol=1e-5)
    assert scale_preds[4] > 4000.0
    assert scale_preds[2] > 40.0

    drivers = compute_feature_drivers(model, batch_rows.iloc[[rice_idx]], top_k=6)
    assert len(drivers) >= 3
    assert any(d["direction"] in {"positive", "negative"} for d in drivers)
    assert all(
        0.0 <= d["impact_pct"] <= 100.0
        and d["direction"] in {"positive", "negative", "neutral"}
        for d in drivers
    )
    assert drivers == sorted(drivers, key=lambda d: d["impact_pct"], reverse=True)


def test_yield_prediction_api_end_to_end_and_persistence(isolated_api_client):
    client, SessionLocal = isolated_api_client

    # Unauthenticated blocked
    base_payload = {
        "crop": "Rice",
        "crop_year": 2025,
        "season": "Kharif",
        "state": "Tamil Nadu",
        "area_hectares": 4.0,
        "annual_rainfall_mm": 1150.0,
        "fertilizer_kg": 600.0,
        "pesticide_kg": 1.6,
    }
    assert client.post("/api/v1/predictions/yield", json=base_payload).status_code == 401
    assert client.get("/api/v1/predictions/yield/history").status_code == 401

    headers_a, user_a = _register_user(client, email="farmer.a@farm.in", full_name="Farmer A")
    headers_b, _ = _register_user(client, email="farmer.b@farm.in", full_name="Farmer B")

    # Create a farm for Farmer A
    farm_resp = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Pollachi Coconut Grove",
            "state": "Kerala",
            "area_hectares": 3.5,
            "primary_crop": "Coconut",
        },
    )
    assert farm_resp.status_code == 201
    farm_id = farm_resp.json()["id"]

    # 1. Standard crop (Rice) with canonical whitespace handling
    rice_resp = client.post(
        "/api/v1/predictions/yield",
        headers=headers_a,
        json={**base_payload, "crop": " rice ", "season": " kharif "},
    )
    assert rice_resp.status_code == 200, rice_resp.text
    rice_data = rice_resp.json()
    assert rice_data["source_mode"] == "live_api"
    assert rice_data["crop"] == "Rice"
    assert rice_data["season"] == "Kharif"
    assert rice_data["yield_unit"] == "tonnes/hectare"
    assert rice_data["production_unit"] == "tonnes"
    assert 0.5 <= rice_data["predicted_yield"] <= 15.0
    assert math.isclose(
        rice_data["estimated_total_production"],
        round(rice_data["predicted_yield"] * 4.0, 2),
        abs_tol=0.05,
    )
    assert len(rice_data["feature_drivers"]) >= 3

    # 2. Coconut prediction linked to owned farm -> nuts/hectare
    coco_resp = client.post(
        "/api/v1/predictions/yield",
        headers=headers_a,
        json={
            "farm_id": farm_id,
            "crop": "Coconut",
            "crop_year": 2024,
            "season": "Whole Year",
            "state": "Kerala",
            "area_hectares": 3.5,
            "annual_rainfall_mm": 2400.0,
            "fertilizer_kg": 500.0,
            "pesticide_kg": 1.2,
        },
    )
    assert coco_resp.status_code == 200, coco_resp.text
    coco_data = coco_resp.json()
    assert coco_data["farm_id"] == farm_id
    assert coco_data["yield_unit"] == "nuts/hectare"
    assert coco_data["production_unit"] == "nuts"
    assert coco_data["predicted_yield"] > 1000.0

    # 3. Cold-start / whitespace crop tolerance ('Other Rabi pulses' -> 'Other  Rabi pulses')
    pulses_resp = client.post(
        "/api/v1/predictions/yield",
        headers=headers_a,
        json={**base_payload, "crop": "Other Rabi pulses", "season": "Rabi"},
    )
    assert pulses_resp.status_code == 200, pulses_resp.text
    assert pulses_resp.json()["crop"] == "Other  Rabi pulses"

    # Verify DB persistence & history isolation
    hist_a = client.get("/api/v1/predictions/yield/history", headers=headers_a)
    assert hist_a.status_code == 200
    assert len(hist_a.json()) == 3
    assert hist_a.json()[0]["crop"] == "Other  Rabi pulses"

    hist_b = client.get("/api/v1/predictions/yield/history", headers=headers_b)
    assert hist_b.status_code == 200
    assert hist_b.json() == []

    with SessionLocal() as db:
        rows = db.scalars(
            select(CropPrediction).where(CropPrediction.user_id == uuid.UUID(user_a["id"]))
        ).all()
        assert len(rows) == 3

        # Promote Farmer B to admin to inspect live Admin model registry + prediction count
        admin_user = db.get(User, uuid.UUID(headers_b_user_id := client.get("/api/v1/auth/me", headers=headers_b).json()["id"]))
        assert admin_user is not None
        admin_user.role = "admin"
        db.commit()

    admin_overview = client.get("/api/v1/admin/overview", headers=headers_b)
    assert admin_overview.status_code == 200
    ov_data = admin_overview.json()
    assert ov_data["total_predictions"] == 3
    yield_reg = next(m for m in ov_data["models"] if m["module"] == "Crop Yield Prediction")
    assert yield_reg["status"] == "Active (Phase 5 Live)"
    assert "MB" in yield_reg["artifact_size"]
    assert "R²" in yield_reg["metric_value"]


def test_yield_api_leakage_validation_and_missing_model_safety(isolated_api_client, tmp_path: Path):
    client, _ = isolated_api_client
    headers, _ = _register_user(client, email="validator.farmer@farm.in")
    other_headers, _ = _register_user(client, email="owner.farmer@farm.in")

    owner_farm = client.post(
        "/api/v1/farms",
        headers=other_headers,
        json={"name": "Owner Plot", "state": "Karnataka", "area_hectares": 2.0},
    ).json()

    valid = {
        "crop": "Wheat",
        "crop_year": 2024,
        "season": "Rabi",
        "state": "Punjab",
        "area_hectares": 3.0,
        "annual_rainfall_mm": 620.0,
        "fertilizer_kg": 450.0,
        "pesticide_kg": 1.2,
    }

    # Target leakage payload strictly forbidden (extra="forbid")
    for leak_key in ("production", "Production", "yield"):
        resp = client.post(
            "/api/v1/predictions/yield",
            headers=headers,
            json={**valid, leak_key: 9999.0},
        )
        assert resp.status_code == 422, f"Should reject extra leaking field '{leak_key}'"

    # Invalid domain values -> 422
    invalid_cases = [
        {**valid, "area_hectares": 0.0},
        {**valid, "area_hectares": -2.0},
        {**valid, "annual_rainfall_mm": -5.0},
        {**valid, "fertilizer_kg": -10.0},
        {**valid, "pesticide_kg": -1.0},
        {**valid, "crop_year": 1980},
        {**valid, "crop_year": 2150},
        {**valid, "crop": "MarsWheat"},
        {**valid, "state": "Atlantis"},
        {**valid, "season": "Monsoon"},
    ]
    for bad in invalid_cases:
        resp = client.post("/api/v1/predictions/yield", headers=headers, json=bad)
        assert resp.status_code == 422, f"Expected 422 for {bad}"

    # Cross-farmer farm_id linking -> 403
    forbidden_farm = client.post(
        "/api/v1/predictions/yield",
        headers=headers,
        json={**valid, "farm_id": owner_farm["id"]},
    )
    assert forbidden_farm.status_code == 403

    # Non-existent farm_id -> 404
    missing_farm = client.post(
        "/api/v1/predictions/yield",
        headers=headers,
        json={**valid, "farm_id": str(uuid.uuid4())},
    )
    assert missing_farm.status_code == 404

    # Missing model artifact -> safe 503 without traceback leakage
    try:
        crop_yield_service.set_paths_for_testing(model_path=tmp_path / "does_not_exist.joblib")
        missing_resp = client.post("/api/v1/predictions/yield", headers=headers, json=valid)
        assert missing_resp.status_code == 503
        assert "unavailable" in missing_resp.json()["detail"].lower()
        assert "does_not_exist" not in missing_resp.json()["detail"]

        # Corrupt artifact -> safe 503 without traceback leakage
        bad_artifact = tmp_path / "corrupt.joblib"
        bad_artifact.write_text("not a valid joblib pickle", encoding="utf-8")
        crop_yield_service.set_paths_for_testing(model_path=bad_artifact)
        corrupt_resp = client.post("/api/v1/predictions/yield", headers=headers, json=valid)
        assert corrupt_resp.status_code == 503
        assert "could not be loaded" in corrupt_resp.json()["detail"].lower()
        assert "traceback" not in corrupt_resp.text.lower()
    finally:
        crop_yield_service.reset_cache()
