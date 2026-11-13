from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
import secrets
import sys
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
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

from app.core.config import get_settings
from app.db.session import build_engine, get_db
from app.main import create_app
from app.models import (
    CropPrediction,
    CropRecommendation,
    DiseaseDetection,
    Farm,
    FertilizerRecommendation,
    GeneratedReport,
    IrrigationRecommendation,
    User,
)
from app.schemas.auth import UserRole


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture()
def phase8_client(tmp_path: Path):
    db_file = tmp_path / "phase8_integration_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
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
        engine.dispose()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    engine.dispose()


def _register(client: TestClient, full_name: str, email: str, role: str = "farmer") -> tuple[str, dict[str, str]]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": "StrongPassword!123",
            "preferred_language": "en",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    user_id = resp.json()["user"]["id"]
    return user_id, {"Authorization": f"Bearer {token}"}


def _promote_to_admin(session_factory, user_id: str) -> None:
    with session_factory() as db:
        user = db.scalar(select(User).where(User.id == uuid.UUID(user_id)))
        assert user is not None
        user.role = "admin"
        db.commit()


def test_offline_postgresql_ddl_compilation(capsys):
    """Verify Alembic compiles clean PostgreSQL DDL offline without errors."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://terra_user:secret@localhost:5432/terraqora_ai",
    )

    command.upgrade(cfg, "head", sql=True)
    captured = capsys.readouterr()
    ddl_sql = captured.out
    assert "CREATE TABLE users" in ddl_sql
    assert "CREATE TABLE farms" in ddl_sql
    assert "CREATE TABLE generated_reports" in ddl_sql
    assert "TIMESTAMP WITH TIME ZONE" in ddl_sql


def test_operational_analytics_multi_module_aggregation_and_isolation(phase8_client):
    client, session_factory = phase8_client

    user_a_id, headers_a = _register(client, "Ramesh Patel", "ramesh@terraqora.ai")
    user_b_id, headers_b = _register(client, "Anita Sharma", "anita@terraqora.ai")

    # Farmer A creates two farm plots
    resp_f1 = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Ramesh Green Acres",
            "state": "Gujarat",
            "district": "Anand",
            "area_hectares": 5.5,
            "primary_crop": "Groundnut",
            "soil_type": "Sandy Loam",
            "irrigation_type": "drip",
        },
    )
    assert resp_f1.status_code == 201
    f1_id = resp_f1.json()["id"]

    resp_f2 = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Ramesh Riverside Plot",
            "state": "Gujarat",
            "district": "Vadodara",
            "area_hectares": 3.0,
            "primary_crop": "Cotton",
            "soil_type": "Black",
            "irrigation_type": "canal",
        },
    )
    assert resp_f2.status_code == 201
    f2_id = resp_f2.json()["id"]

    # Populate module records directly for Farmer A
    now = datetime.now(timezone.utc)
    with session_factory() as db:
        # 1. Yield prediction
        db.add(
            CropPrediction(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_a_id),
                farm_id=uuid.UUID(f1_id),
                crop="Groundnut",
                crop_year=2024,
                season="Kharif",
                state="Gujarat",
                area_hectares=5.5,
                annual_rainfall_mm=850.0,
                fertilizer_kg=1200.0,
                pesticide_kg=40.0,
                predicted_yield=2.85,
                yield_unit="tonnes/hectare",
                estimated_total_production=15.67,
                model_name="random_forest_regressor",
                model_version="v1",
                created_at=now - timedelta(days=2),
            )
        )
        # 2. Crop recommendation
        db.add(
            CropRecommendation(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_a_id),
                farm_id=uuid.UUID(f1_id),
                nitrogen=65.0,
                phosphorus=42.0,
                potassium=48.0,
                temperature_c=28.5,
                humidity_pct=72.0,
                soil_ph=6.8,
                rainfall_mm=180.0,
                recommended_crop="Groundnut",
                top_candidates_json=[{"crop": "Groundnut", "probability": 0.88, "fit_reason": "Optimal soil NPK"}],
                model_version="v1",
                created_at=now - timedelta(days=1),
            )
        )
        # 3. Fertilizer recommendation
        db.add(
            FertilizerRecommendation(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_a_id),
                farm_id=uuid.UUID(f2_id),
                nitrogen=35.0,
                phosphorus=25.0,
                potassium=30.0,
                soil_ph=7.2,
                soil_type="Black",
                crop_type="Cotton",
                recommended_fertilizer="14-35-14",
                confidence=0.91,
                nutrient_status_json={"nitrogen": "optimal", "phosphorus": "adequate"},
                advisory_notes="Apply basal split at planting.",
                expert_disclaimer="Verify via local soil health card.",
                model_version="v1",
                created_at=now - timedelta(hours=12),
            )
        )
        # 4. Disease detection
        db.add(
            DiseaseDetection(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_a_id),
                farm_id=uuid.UUID(f1_id),
                crop_hint="Tomato",
                image_filename="leaf1.jpg",
                image_mime_type="image/jpeg",
                image_size_bytes=10240,
                image_sha256="a" * 64,
                predicted_label="Tomato___Early_blight",
                confidence=0.94,
                is_uncertain=False,
                top_predictions_json=[{"label": "Tomato___Early_blight", "confidence": 0.94}],
                treatment_summary="Apply copper-based fungicide.",
                prevention_notes="Ensure drip lines avoid foliage splash.",
                model_version="v1",
                created_at=now - timedelta(hours=6),
            )
        )
        # 5. Irrigation recommendation
        db.add(
            IrrigationRecommendation(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_a_id),
                farm_id=uuid.UUID(f2_id),
                location_name="Vadodara Plot",
                latitude=22.3072,
                longitude=73.1812,
                crop_type="Cotton",
                growth_stage="mid_season",
                weather_provider="open_meteo",
                weather_snapshot_json={"temp_c": 30.2, "humidity_pct": 65},
                forecast_rainfall_7d_mm=5.0,
                estimated_et0_mm=4.0,
                recommended_water_mm=18.5,
                irrigation_urgency="moderate",
                is_sensor_backed=False,
                advisory_notes="Schedule irrigation across two 9 mm cycles.",
                created_at=now - timedelta(hours=2),
            )
        )
        db.commit()

    # Query operational analytics for Farmer A (all farms, 30 days)
    res_a = client.get("/api/v1/analytics/operational?range_days=30", headers=headers_a)
    assert res_a.status_code == 200, res_a.text
    data_a = res_a.json()

    summary_a = data_a["summary"]
    assert summary_a["yield_predictions"] == 1
    assert summary_a["crop_recommendations"] == 1
    assert summary_a["fertilizer_recommendations"] == 1
    assert summary_a["disease_detections"] == 1
    assert summary_a["irrigation_advisories"] == 1
    assert summary_a["total_activities"] == 5
    assert summary_a["active_farms_count"] == 2
    assert summary_a["total_hectares_managed"] == 8.5

    assert len(data_a["timeline"]) >= 1
    assert any(c["crop"] == "Groundnut" for c in data_a["top_crops"])
    assert any("early blight" in d["disease_name"].lower() for d in data_a["disease_findings"])
    assert any(f["recommended_fertilizer"] == "14-35-14" for f in data_a["fertilizer_grades"])

    # Farm breakdown verification
    assert len(data_a["farm_breakdown"]) == 2
    f1_stat = next(fb for fb in data_a["farm_breakdown"] if fb["farm_id"] == f1_id)
    assert f1_stat["total_activities"] == 3  # yield + crop + disease

    # Filter by specific farm
    res_f1 = client.get(f"/api/v1/analytics/operational?farm_id={f1_id}", headers=headers_a)
    assert res_f1.status_code == 200
    data_f1 = res_f1.json()
    assert data_f1["summary"]["total_activities"] == 3
    assert data_f1["filter_farm_id"] == f1_id

    # Filter with non-existent or other user's farm -> 404
    res_bad_farm = client.get(f"/api/v1/analytics/operational?farm_id={uuid.uuid4()}", headers=headers_a)
    assert res_bad_farm.status_code == 404

    # Tenant isolation: Farmer B must see 0 activities and empty breakdowns
    res_b = client.get("/api/v1/analytics/operational", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["summary"]["total_activities"] == 0
    assert data_b["summary"]["active_farms_count"] == 0
    assert len(data_b["top_crops"]) == 0
    assert len(data_b["disease_findings"]) == 0

    # Macro dataset analytics
    res_dataset = client.get("/api/v1/analytics/dataset?year_start=2015&year_end=2020", headers=headers_a)
    assert res_dataset.status_code == 200
    d_data = res_dataset.json()
    assert d_data["total_records"] > 0
    assert len(d_data["correlation_matrix"]) > 0


def test_pdf_report_generation_download_and_access_control(phase8_client):
    client, session_factory = phase8_client

    user_a_id, headers_a = _register(client, "Deepak Varma", "deepak@terraqora.ai")
    user_b_id, headers_b = _register(client, "Sneha Kulkarni", "sneha@terraqora.ai")

    report_types = [
        ("combined_intelligence", "Comprehensive Farm Intelligence Audit"),
        ("crop_yield", "Wheat Acreage & Productivity Forecast"),
        ("crop_recommendation", "Soil Chemistry & Crop Suitability Assessment"),
        ("fertilizer_recommendation", "ICAR Split Nitrogen & Phosphate Plan"),
        ("disease_detection", "Tomato Foliage CV Screening Audit"),
        ("weather_irrigation", "7-Day Evapotranspiration Irrigation Schedule"),
    ]

    generated_ids = []

    for r_type, title in report_types:
        resp = client.post(
            "/api/v1/reports",
            headers=headers_a,
            json={
                "title": title,
                "report_type": r_type,
                "crop": "Wheat",
                "state": "Punjab",
                "season": "Rabi",
                "area_hectares": 12.0,
                "predicted_yield": 4.85,
                "yield_unit": "tonnes/hectare",
                "fertilizer_recommendation": "120 kg N + 60 kg P2O5 per ha in split dosages.",
                "irrigation_summary": "Estimated ET0 is 3.8 mm/day; deliver 35 mm across 2 applications.",
                "language": "en",
            },
        )
        assert resp.status_code == 201, resp.text
        report_data = resp.json()
        assert report_data["title"] == title
        assert report_data["report_type"] == r_type
        assert report_data["pdf_filename"].endswith(".pdf")
        assert len(report_data["agricultural_observations"]) >= 2
        generated_ids.append(report_data["id"])

        # Test download endpoint
        dl_resp = client.get(f"/api/v1/reports/{report_data['id']}/download", headers=headers_a)
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/pdf"
        assert f'filename="{report_data["pdf_filename"]}"' in dl_resp.headers["content-disposition"]

        pdf_bytes = dl_resp.content
        # PDF magic bytes verification
        assert pdf_bytes.startswith(b"%PDF-1.")
        # Ensure it is a non-trivial publication-quality document
        assert len(pdf_bytes) > 3000, f"PDF was unexpectedly small: {len(pdf_bytes)} bytes"

        # Also test /pdf endpoint
        pdf_resp = client.get(f"/api/v1/reports/{report_data['id']}/pdf", headers=headers_a)
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"

    # List reports for User A
    list_resp = client.get("/api/v1/reports", headers=headers_a)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 6

    # Cross-user authorization check: User B cannot access or download User A's report (403 Forbidden)
    target_id = generated_ids[0]
    res_b_get = client.get(f"/api/v1/reports/{target_id}", headers=headers_b)
    assert res_b_get.status_code == 403

    res_b_dl = client.get(f"/api/v1/reports/{target_id}/download", headers=headers_b)
    assert res_b_dl.status_code == 403


def test_admin_dashboard_services_health_and_events(phase8_client):
    client, session_factory = phase8_client

    admin_id, admin_headers = _register(client, "Super Administrator", "admin@terraqora.ai")
    _promote_to_admin(session_factory, admin_id)

    farmer_id, farmer_headers = _register(client, "Kiran Kumar", "kiran@terraqora.ai")

    overview_resp = client.get("/api/v1/admin/overview", headers=admin_headers)
    assert overview_resp.status_code == 200, overview_resp.text
    data = overview_resp.json()

    assert data["total_users"] >= 2
    assert data["active_users"] >= 2
    assert data["inactive_users"] == 0

    # Verify services health telemetry
    health_services = {sh["service"]: sh for sh in data["services_health"]}
    assert "PostgreSQL / Database Session" in health_services
    assert health_services["PostgreSQL / Database Session"]["status"] == "Operational"
    assert "Weather API (Open Meteo)" in health_services
    assert "ML/CV Model Artifacts" in health_services
    assert "Local Reports & PDF Storage" in health_services

    # Verify sanitized recent events
    events = data["recent_events"]
    assert len(events) >= 1
    for evt in events:
        assert evt["level"] in ("INFO", "WARNING", "ERROR")
        assert "password" not in evt["message"].lower()
        assert "secret" not in evt["message"].lower()

    # Toggle user active status
    patch_resp = client.patch(
        f"/api/v1/admin/users/{farmer_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False

    # Check that inactive user count reflects the change
    overview_resp_2 = client.get("/api/v1/admin/overview", headers=admin_headers)
    assert overview_resp_2.status_code == 200
    data_2 = overview_resp_2.json()
    assert data_2["inactive_users"] >= 1
