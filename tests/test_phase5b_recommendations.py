import hashlib
import json
import math
import os
from pathlib import Path
import re
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
from app.models import (  # noqa: E402
    CropRecommendation,
    FertilizerRecommendation,
    User,
)
from app.services import crop_rec_service, fertilizer_service  # noqa: E402
from ml.preprocessing.crop_rec_features import (  # noqa: E402
    RAW_CROP_REC_FEATURES,
    VALID_CROP_LABELS,
    clean_crop_rec_dataframe,
)
from ml.preprocessing.fertilizer_features import (  # noqa: E402
    NPK_CSV_FEATURE_COLUMNS,
    VALID_FERTILIZER_CLASSES,
    assess_soil_balance,
    clean_fertilizer_dataframe,
)

CROP_REC_CSV = ROOT / "ml" / "datasets" / "raw" / "Crop_recommendation.csv"
FERT_CSV = ROOT / "ml" / "datasets" / "raw" / "Fertilizer_Prediction.csv"
CROP_REC_AUDIT = ROOT / "ml" / "evaluation" / "crop_rec_audit.json"
CROP_REC_METRICS = ROOT / "ml" / "evaluation" / "crop_rec_metrics.json"
FERT_AUDIT = ROOT / "ml" / "evaluation" / "fertilizer_audit.json"
FERT_METRICS = ROOT / "ml" / "evaluation" / "fertilizer_metrics.json"
CROP_REC_MODEL = ROOT / "ml" / "saved_models" / "crop_recommendation_model.joblib"
FERT_MODEL = ROOT / "ml" / "saved_models" / "fertilizer_model.joblib"

EXPECTED_CROP_REC_SHA256 = (
    "54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e"
)
EXPECTED_FERT_SHA256 = (
    "dfd69cee9d3d7a4403aab5647d5749050ae406ad42dc9ce3f508aa3442955e41"
)

DOSAGE_FABRICATION_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:kg/ha|kg/acre|g/plant|tonnes/ha|bags/acre|ml/L|l/ha)\b",
    re.IGNORECASE,
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture()
def isolated_api_client(tmp_path: Path):
    db_file = tmp_path / "phase5b_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
    crop_rec_service.reset_cache()
    fertilizer_service.reset_cache()
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

    crop_rec_service.reset_cache()
    fertilizer_service.reset_cache()
    app.dependency_overrides.clear()
    engine.dispose()


def _register_user(
    client: TestClient,
    *,
    email: str,
    full_name: str = "Phase5B Farmer",
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


def test_raw_datasets_untouched_and_audits_verified():
    assert CROP_REC_CSV.exists()
    assert FERT_CSV.exists()
    assert _sha256_file(CROP_REC_CSV) == EXPECTED_CROP_REC_SHA256
    assert _sha256_file(FERT_CSV) == EXPECTED_FERT_SHA256

    crop_audit = json.loads(CROP_REC_AUDIT.read_text(encoding="utf-8"))
    assert crop_audit["shape"]["rows"] == 2200
    assert crop_audit["class_balance"]["num_classes"] == 22
    assert crop_audit["duplicates"]["exact_rows"] == 0
    assert all(v == 0 for v in crop_audit["missing_values"].values())

    fert_audit = json.loads(FERT_AUDIT.read_text(encoding="utf-8"))
    assert fert_audit["shape"]["rows"] == 99
    assert fert_audit["class_balance"]["num_classes"] == 7
    assert fert_audit["duplicates"]["exact_rows"] == 0
    assert fert_audit["mutual_information_with_target"]["Phosphorus"] > 1.5
    assert fert_audit["mutual_information_with_target"]["Crop Type"] == 0.0
    assert len(fert_audit["alternative_public_datasets_audited_and_rejected"]) >= 3


def test_crop_recommendation_preprocessing_and_model_quality():
    assert CROP_REC_METRICS.exists()
    assert CROP_REC_MODEL.exists()
    assert CROP_REC_MODEL.stat().st_size < 5 * 1024 * 1024

    metrics = json.loads(CROP_REC_METRICS.read_text(encoding="utf-8"))
    assert metrics["selected_model_key"] == "gaussian_nb_raw"
    assert metrics["split_strategy"]["test_rows"] == 440
    assert metrics["selected_test_metrics"]["accuracy"] >= 0.98
    assert metrics["selected_test_metrics"]["macro_f1"] >= 0.98
    assert metrics["selected_test_metrics"]["top_3_accuracy"] == 1.0

    # Domain validation rejects invalid climate/soil inputs
    valid_row = pd.DataFrame(
        [
            {
                "N": 85.0,
                "P": 50.0,
                "K": 42.0,
                "temperature": 24.5,
                "humidity": 80.0,
                "ph": 6.6,
                "rainfall": 225.0,
            }
        ],
        columns=RAW_CROP_REC_FEATURES,
    )
    cleaned = clean_crop_rec_dataframe(valid_row)
    assert len(cleaned) == 1

    for bad_col, bad_val in [("N", -1.0), ("humidity", 105.0), ("ph", 14.5), ("rainfall", -5.0)]:
        bad = valid_row.copy()
        bad[bad_col] = bad_val
        with pytest.raises(ValueError):
            clean_crop_rec_dataframe(bad)

    model = joblib.load(CROP_REC_MODEL)
    probs = model.predict_proba(valid_row)
    assert probs.shape == (1, 22)
    assert np.all(np.isfinite(probs))
    assert math.isclose(float(probs.sum()), 1.0, abs_tol=1e-6)

    top3 = model.top_k_candidates(valid_row, k=3)
    assert len(top3) == 3
    assert all(c["crop"] in VALID_CROP_LABELS for c in top3)
    assert top3[0]["probability"] >= top3[1]["probability"] >= top3[2]["probability"]
    assert top3[0]["crop"] in ("rice", "jute")
    assert all(len(c["fit_reason"]) > 15 for c in top3)


def test_fertilizer_model_metrics_and_clinical_guardrails():
    assert FERT_METRICS.exists()
    assert FERT_MODEL.exists()
    assert FERT_MODEL.stat().st_size < 4 * 1024 * 1024

    metrics = json.loads(FERT_METRICS.read_text(encoding="utf-8"))
    assert metrics["selected_model_key"] == "logistic_regression_npk3"
    assert metrics["selected_feature_columns"] == NPK_CSV_FEATURE_COLUMNS
    assert metrics["selected_test_metrics"]["accuracy"] >= 0.95
    assert metrics["selected_test_metrics"]["macro_f1"] >= 0.95

    raw_df = pd.DataFrame(
        [
            {
                "Temparature": 30,
                "Humidity ": 60,
                "Moisture": 40,
                "Soil Type": "Loamy",
                "Crop Type": "Wheat",
                "Nitrogen": 12,
                "Potassium": 0,
                "Phosphorous": 38,
                "Fertilizer Name": "DAP",
            }
        ]
    )
    cleaned = clean_fertilizer_dataframe(raw_df, require_target=True)
    assert "Temperature" in cleaned.columns
    assert "Humidity" in cleaned.columns
    assert "Phosphorus" in cleaned.columns

    # Sufficiency guardrail check: optimal/high NPK never triggers deficit grade demand
    sufficient = assess_soil_balance(
        nitrogen=70.0, phosphorus=50.0, potassium=55.0, soil_ph=6.7
    )
    assert sufficient["has_any_deficit"] is False
    assert sufficient["demand_signature"] == {"Nitrogen": 0.0, "Phosphorus": 0.0, "Potassium": 0.0}

    # Acidic/alkaline qualitative KVK guidance
    acidic = assess_soil_balance(nitrogen=30.0, phosphorus=45.0, potassium=45.0, soil_ph=4.9)
    alkaline = assess_soil_balance(nitrogen=30.0, phosphorus=45.0, potassium=45.0, soil_ph=8.4)
    assert "Acidic" in acidic["ph_assessment"] and "KVK" in acidic["ph_assessment"]
    assert "Alkaline" in alkaline["ph_assessment"] and "KVK" in alkaline["ph_assessment"]

    # Archetype calibration against live fertilizer_model.joblib
    model = joblib.load(FERT_MODEL)
    archetypes = [
        ("Pure N mild deficit", 28.0, 45.0, 45.0, "Urea"),
        ("Pure P deficit", 60.0, 15.0, 45.0, "DAP"),
        ("Moderate N+P deficit", 28.0, 20.0, 45.0, "20-20"),
        ("Severe N+P deficit", 12.0, 12.0, 45.0, "28-28"),
        ("Balanced N+P+K deficit", 20.0, 16.0, 15.0, "17-17-17"),
        ("P+K dominant deficit", 35.0, 12.0, 10.0, "10-26-26"),
        ("Severe P with moderate N+K", 30.0, 5.0, 18.0, "14-35-14"),
    ]
    for label, n, p, k, expected_grade in archetypes:
        bal = assess_soil_balance(nitrogen=n, phosphorus=p, potassium=k, soil_ph=6.5)
        assert bal["has_any_deficit"] is True, label
        row_df = pd.DataFrame([bal["demand_signature"]], columns=NPK_CSV_FEATURE_COLUMNS)
        pred_grade, conf, alts = model.predict_grade_with_confidence(row_df)
        assert pred_grade in VALID_FERTILIZER_CLASSES
        assert pred_grade == expected_grade, f"{label}: expected {expected_grade}, got {pred_grade}"
        assert 0.0 < conf <= 1.0
        assert len(alts) == 3


def test_recommendation_endpoints_end_to_end_safety_and_admin_registry(
    isolated_api_client, tmp_path: Path
):
    client, SessionLocal = isolated_api_client

    crop_payload = {
        "nitrogen": 85.0,
        "phosphorus": 50.0,
        "potassium": 42.0,
        "temperature_c": 24.5,
        "humidity_pct": 80.0,
        "soil_ph": 6.6,
        "rainfall_mm": 225.0,
        "season": "Kharif",
        "region": "Tamil Nadu",
    }
    fert_deficit_payload = {
        "nitrogen": 28.0,
        "phosphorus": 45.0,
        "potassium": 45.0,
        "soil_ph": 6.4,
        "soil_type": "Alluvial",
        "crop_type": "Rice",
        "location": "Tamil Nadu",
    }

    # Unauthenticated blocked
    assert client.post("/api/v1/recommendations/crop", json=crop_payload).status_code == 401
    assert client.get("/api/v1/recommendations/crop/history").status_code == 401
    assert (
        client.post("/api/v1/recommendations/fertilizer", json=fert_deficit_payload).status_code
        == 401
    )
    assert client.get("/api/v1/recommendations/fertilizer/history").status_code == 401

    headers_a, user_a = _register_user(client, email="rec.farmer.a@farm.in", full_name="Farmer A")
    headers_b, user_b = _register_user(client, email="rec.farmer.b@farm.in", full_name="Farmer B")

    farm_a = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Thanjavur Paddy Block",
            "state": "Tamil Nadu",
            "area_hectares": 3.2,
            "soil_type": "Alluvial",
            "soil_ph": 6.6,
            "primary_crop": "Rice",
        },
    ).json()
    farm_b = client.post(
        "/api/v1/farms",
        headers=headers_b,
        json={"name": "Mysuru Plot", "state": "Karnataka", "area_hectares": 2.0},
    ).json()

    # 1. Crop Recommendation endpoint + DB persistence + history isolation
    cr_resp = client.post(
        "/api/v1/recommendations/crop",
        headers=headers_a,
        json={**crop_payload, "farm_id": farm_a["id"]},
    )
    assert cr_resp.status_code == 200, cr_resp.text
    cr = cr_resp.json()
    assert cr["source_mode"] == "live_api"
    assert cr["farm_id"] == farm_a["id"]
    assert cr["recommended_crop"] in VALID_CROP_LABELS
    assert len(cr["top_candidates"]) == 3
    assert len(cr["model_version"]) <= 32
    assert "7 validated soil" in cr["soil_climate_summary"]

    cr_hist_a = client.get("/api/v1/recommendations/crop/history", headers=headers_a)
    assert cr_hist_a.status_code == 200
    assert len(cr_hist_a.json()) == 1
    assert cr_hist_a.json()[0]["id"] == cr["id"]
    assert client.get("/api/v1/recommendations/crop/history", headers=headers_b).json() == []

    # 2. Fertilizer Recommendation endpoint:
    # 2a. Deficit mode (Pure N deficit -> Urea + non-exact soil disclosure)
    fert_n_resp = client.post(
        "/api/v1/recommendations/fertilizer",
        headers=headers_a,
        json={**fert_deficit_payload, "farm_id": farm_a["id"]},
    )
    assert fert_n_resp.status_code == 200, fert_n_resp.text
    fert_n = fert_n_resp.json()
    assert fert_n["source_mode"] == "live_api"
    assert fert_n["farm_id"] == farm_a["id"]
    assert fert_n["recommended_fertilizer"] == "Urea"
    assert fert_n["ml_predicted_grade"] == "Urea"
    assert fert_n["recommendation_mode"] == "ml_grade_with_agronomic_guardrails"
    assert "Soil texture 'Alluvial' mapped qualitatively" in fert_n["dataset_coverage_note"]
    assert "Nutrient".lower() not in fert_n["recommended_fertilizer"].lower()
    for txt_field in (
        fert_n["recommended_fertilizer"],
        fert_n["advisory_notes"],
        fert_n["ph_assessment"],
        fert_n["dataset_coverage_note"],
    ):
        assert not DOSAGE_FABRICATION_RE.search(txt_field), f"Dosage found in: {txt_field}"

    # 2b. Sufficiency guardrail bypasses chemical escalation
    fert_ok_resp = client.post(
        "/api/v1/recommendations/fertilizer",
        headers=headers_a,
        json={
            "nitrogen": 75.0,
            "phosphorus": 50.0,
            "potassium": 55.0,
            "soil_ph": 6.8,
            "soil_type": "Black (Regur)",
            "crop_type": "Coconut",
            "location": "Kerala",
        },
    )
    assert fert_ok_resp.status_code == 200, fert_ok_resp.text
    fert_ok = fert_ok_resp.json()
    assert fert_ok["recommendation_mode"] == "agronomic_sufficiency_guardrail"
    assert fert_ok["ml_predicted_grade"] is None
    assert fert_ok["recommended_fertilizer"] == "Soil Nutrients Sufficient — Organic Maintenance Only"
    assert "outside the 11 crops" in fert_ok["dataset_coverage_note"]
    assert not DOSAGE_FABRICATION_RE.search(fert_ok["advisory_notes"])

    # 2c. Pure Potassium deficit discloses missing MOP 0-0-60 cleanly
    fert_k_resp = client.post(
        "/api/v1/recommendations/fertilizer",
        headers=headers_a,
        json={
            "nitrogen": 65.0,
            "phosphorus": 45.0,
            "potassium": 10.0,
            "soil_ph": 6.3,
            "soil_type": "Red Loamy",
            "crop_type": "Sugarcane",
            "location": "Maharashtra",
        },
    )
    assert fert_k_resp.status_code == 200, fert_k_resp.text
    fert_k = fert_k_resp.json()
    assert "exclude straight Potash (MOP 0-0-60)" in fert_k["advisory_notes"]
    assert not DOSAGE_FABRICATION_RE.search(fert_k["advisory_notes"])

    fert_hist_a = client.get("/api/v1/recommendations/fertilizer/history", headers=headers_a)
    assert fert_hist_a.status_code == 200
    assert len(fert_hist_a.json()) == 3
    assert client.get("/api/v1/recommendations/fertilizer/history", headers=headers_b).json() == []

    # Ownership & domain validation checks
    assert (
        client.post(
            "/api/v1/recommendations/crop",
            headers=headers_a,
            json={**crop_payload, "farm_id": farm_b["id"]},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/recommendations/fertilizer",
            headers=headers_a,
            json={**fert_deficit_payload, "farm_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/recommendations/crop",
            headers=headers_a,
            json={**crop_payload, "unknown_extra": 123},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/recommendations/crop",
            headers=headers_a,
            json={**crop_payload, "soil_ph": 15.0},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/recommendations/fertilizer",
            headers=headers_a,
            json={**fert_deficit_payload, "soil_type": "   "},
        ).status_code
        == 422
    )

    # DB rows & Admin registry verification
    with SessionLocal() as db:
        assert (
            len(
                db.scalars(
                    select(CropRecommendation).where(
                        CropRecommendation.user_id == uuid.UUID(user_a["id"])
                    )
                ).all()
            )
            == 1
        )
        assert (
            len(
                db.scalars(
                    select(FertilizerRecommendation).where(
                        FertilizerRecommendation.user_id == uuid.UUID(user_a["id"])
                    )
                ).all()
            )
            == 3
        )
        admin_user = db.get(User, uuid.UUID(user_b["id"]))
        assert admin_user is not None
        admin_user.role = "admin"
        db.commit()

    ov = client.get("/api/v1/admin/overview", headers=headers_b).json()
    by_mod = {m["module"]: m for m in ov["models"]}
    assert by_mod["Crop Recommendation"]["status"] == "Active (Phase 5b Live)"
    assert "KB" in by_mod["Crop Recommendation"]["artifact_size"]
    assert by_mod["Fertilizer Recommendation"]["status"] == "Active (Phase 5b Live)"
    assert "KB" in by_mod["Fertilizer Recommendation"]["artifact_size"]
    assert by_mod["Plant Disease Vision"]["status"] in {
        "Active (Phase 7 Live)",
        "Artifact Missing",
    }

    # Missing/corrupt artifacts fail closed with 503 and no path/traceback leakage
    try:
        crop_rec_service.set_paths_for_testing(model_path=tmp_path / "missing_crop.joblib")
        fertilizer_service.set_paths_for_testing(model_path=tmp_path / "missing_fert.joblib")

        r1 = client.post("/api/v1/recommendations/crop", headers=headers_a, json=crop_payload)
        r2 = client.post(
            "/api/v1/recommendations/fertilizer", headers=headers_a, json=fert_deficit_payload
        )
        assert r1.status_code == 503 and "missing_crop" not in r1.text
        assert r2.status_code == 503 and "missing_fert" not in r2.text

        corrupt = tmp_path / "corrupt.joblib"
        corrupt.write_text("bad bytes", encoding="utf-8")
        crop_rec_service.set_paths_for_testing(model_path=corrupt)
        fertilizer_service.set_paths_for_testing(model_path=corrupt)
        c1 = client.post("/api/v1/recommendations/crop", headers=headers_a, json=crop_payload)
        c2 = client.post(
            "/api/v1/recommendations/fertilizer", headers=headers_a, json=fert_deficit_payload
        )
        assert c1.status_code == 503 and "traceback" not in c1.text.lower()
        assert c2.status_code == 503 and "traceback" not in c2.text.lower()
    finally:
        crop_rec_service.reset_cache()
        fertilizer_service.reset_cache()
