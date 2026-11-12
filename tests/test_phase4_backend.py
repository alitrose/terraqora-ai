from datetime import timedelta
import os
from pathlib import Path
import secrets
import sys
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import inspect, select

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Configure isolated test environment BEFORE importing application modules
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.security import create_access_token, hash_password, verify_password  # noqa: E402
from app.db.session import build_engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import (  # noqa: E402
    ChatMessage,
    ChatSession,
    CropPrediction,
    Farm,
    FarmerProfile,
    User,
)
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

EXPECTED_TABLES = {
    "users",
    "farmer_profiles",
    "farms",
    "crop_predictions",
    "disease_detections",
    "fertilizer_recommendations",
    "irrigation_recommendations",
    "crop_recommendations",
    "chat_sessions",
    "chat_messages",
    "generated_reports",
}


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture()
def isolated_env(tmp_path: Path):
    db_file = tmp_path / "terraqora_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
    alembic_cfg = _make_alembic_config(db_url)
    command.upgrade(alembic_cfg, "head")

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
        yield client, TestingSessionLocal, engine, app

    app.dependency_overrides.clear()
    engine.dispose()


def _register_farmer(
    client: TestClient,
    *,
    email: str = "ananya.k@farm.in",
    password: str = "HarvestPass#2026",
    full_name: str = "Ananya Krishnan",
    preferred_language: str = "ta",
    state: str | None = "Tamil Nadu",
) -> dict:
    payload = {
        "email": email,
        "password": password,
        "full_name": full_name,
        "preferred_language": preferred_language,
    }
    if state is not None:
        payload["state"] = state
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_admin_and_login(
    client: TestClient,
    session_factory: sessionmaker,
    *,
    email: str = "admin@terraqora.in",
    password: str = "AdminRootPass#2026",
) -> dict:
    with session_factory() as db:
        admin = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Dr. Karthik Menon",
            role="admin",
            preferred_language="en",
            is_active=True,
        )
        db.add(admin)
        db.flush()
        db.add(FarmerProfile(user_id=admin.id, preferred_units="metric", state="Kerala"))
        db.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_alembic_upgrade_downgrade_cycle(tmp_path: Path):
    db_file = tmp_path / "alembic_cycle.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = _make_alembic_config(db_url)

    command.upgrade(cfg, "head")
    engine = build_engine(db_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
        assert "alembic_version" in tables
    finally:
        engine.dispose()

    command.downgrade(cfg, "base")
    engine = build_engine(db_url)
    try:
        remaining = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.isdisjoint(remaining)
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    engine = build_engine(db_url)
    try:
        restored = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(restored)
    finally:
        engine.dispose()


def test_settings_production_guardrails_and_url_normalization():
    s = Settings(
        APP_ENV="development",
        DATABASE_URL="postgres://u:p@db.render.com:5432/tq",
        JWT_SECRET_KEY="",
    )
    assert s.DATABASE_URL == "postgresql+psycopg://u:p@db.render.com:5432/tq"
    assert len(s.JWT_SECRET_KEY) >= 32

    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DATABASE_URL="sqlite:///./local.db",
            JWT_SECRET_KEY="x" * 40,
        )

    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql://u:p@host:5432/db",
            JWT_SECRET_KEY="replace-with-secure-random-64-char-secret",
        )


def test_health_and_cors_preflight(isolated_env):
    client, _, _, app = isolated_env
    assert app.state.limiter is not None

    root_health = client.get("/health")
    assert root_health.status_code == 200
    assert root_health.json()["status"] == "ok"
    assert root_health.json()["database"] == "connected"

    api_health = client.get("/api/v1/health")
    assert api_health.status_code == 200
    assert api_health.json()["database"] == "connected"

    preflight = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_registration_login_jwt_and_security_controls(isolated_env):
    client, session_factory, _, _ = isolated_env

    # Register attempt trying to inject role="admin" must still create role="farmer"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Farmer.One@Example.com",
            "password": "StrongPassword#99",
            "full_name": "  Raghavendra Rao  ",
            "preferred_language": "te",
            "state": "Andhra Pradesh",
            "role": "admin",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    reg_data = reg_resp.json()
    assert reg_data["token_type"] == "bearer"
    assert reg_data["user"]["email"] == "farmer.one@example.com"
    assert reg_data["user"]["full_name"] == "Raghavendra Rao"
    assert reg_data["user"]["role"] == "farmer"
    assert reg_data["user"]["preferred_language"] == "te"

    # Password in database must be hashed with bcrypt (not plaintext)
    with session_factory() as db:
        db_user = db.scalar(select(User).where(User.email == "farmer.one@example.com"))
        assert db_user is not None
        assert db_user.hashed_password != "StrongPassword#99"
        assert db_user.hashed_password.startswith("$2")
        assert verify_password("StrongPassword#99", db_user.hashed_password)
        profile = db.scalar(select(FarmerProfile).where(FarmerProfile.user_id == db_user.id))
        assert profile is not None
        assert profile.state == "Andhra Pradesh"

    # Duplicate email conflict
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "FARMER.ONE@example.com",
            "password": "AnotherPassword#1",
            "full_name": "Duplicate User",
            "preferred_language": "en",
        },
    )
    assert dup_resp.status_code == 409

    # Login success & failure
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "farmer.one@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    ok_login = client.post(
        "/api/v1/auth/login",
        json={"email": "farmer.one@example.com", "password": "StrongPassword#99"},
    )
    assert ok_login.status_code == 200
    token = ok_login.json()["access_token"]

    # Protected /auth/me checks
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer malformed.jwt.token"},
        ).status_code
        == 401
    )

    expired_token = create_access_token(
        subject=reg_data["user"]["id"],
        role="farmer",
        expires_delta=timedelta(minutes=-5),
    )
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        ).status_code
        == 401
    )

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "farmer.one@example.com"


def test_farmer_profile_get_update_and_validation(isolated_env):
    client, _, _, _ = isolated_env
    session = _register_farmer(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}

    get_resp = client.get("/api/v1/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["state"] == "Tamil Nadu"
    assert get_resp.json()["preferred_units"] == "metric"
    assert get_resp.json()["preferred_language"] == "ta"

    # Update profile including preferred_language sync to User
    put_resp = client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "phone": "+91 98400 11223",
            "state": "Kerala",
            "district": "Palakkad",
            "experience_years": 12,
            "primary_soil_type": "Alluvial",
            "preferred_units": "imperial",
            "preferred_language": "ml",
        },
    )
    assert put_resp.status_code == 200, put_resp.text
    updated = put_resp.json()
    assert updated["state"] == "Kerala"
    assert updated["district"] == "Palakkad"
    assert updated["experience_years"] == 12
    assert updated["preferred_units"] == "imperial"
    assert updated["preferred_language"] == "ml"

    # Confirm language persisted on User
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["preferred_language"] == "ml"

    # Validation failures return clean 422 with string detail + errors list
    bad_exp = client.put(
        "/api/v1/profile",
        headers=headers,
        json={"experience_years": -3},
    )
    assert bad_exp.status_code == 422
    assert isinstance(bad_exp.json()["detail"], str)
    assert isinstance(bad_exp.json()["errors"], list)

    bad_units = client.put(
        "/api/v1/profile",
        headers=headers,
        json={"preferred_units": "hectare_only"},
    )
    assert bad_units.status_code == 422

    bad_phone = client.put(
        "/api/v1/profile",
        headers=headers,
        json={"phone": "123"},
    )
    assert bad_phone.status_code == 422


def test_farm_crud_validation_and_cross_farmer_isolation(isolated_env):
    client, _, _, _ = isolated_env
    farmer_a = _register_farmer(client, email="farmera@terra.in", full_name="Farmer A")
    farmer_b = _register_farmer(client, email="farmerb@terra.in", full_name="Farmer B")

    headers_a = {"Authorization": f"Bearer {farmer_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {farmer_b['access_token']}"}

    # Create Farm for Farmer A
    create_resp = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Pollachi North Block",
            "state": "Tamil Nadu",
            "district": "Coimbatore",
            "latitude": 10.658,
            "longitude": 77.008,
            "area_hectares": 4.8,
            "soil_type": "Red Loamy",
            "soil_ph": 6.5,
            "irrigation_type": "drip",
            "primary_crop": "Coconut",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    farm = create_resp.json()
    farm_id = farm["id"]
    assert farm["name"] == "Pollachi North Block"

    # List & Get own farm
    list_a = client.get("/api/v1/farms", headers=headers_a)
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["id"] == farm_id

    get_a = client.get(f"/api/v1/farms/{farm_id}", headers=headers_a)
    assert get_a.status_code == 200
    assert get_a.json()["primary_crop"] == "Coconut"

    # Cross-user isolation: Farmer B sees 0 farms & gets 403 on Read/Update/Delete
    assert client.get("/api/v1/farms", headers=headers_b).json() == []
    assert client.get(f"/api/v1/farms/{farm_id}", headers=headers_b).status_code == 403
    assert (
        client.put(
            f"/api/v1/farms/{farm_id}",
            headers=headers_b,
            json={"name": "Hijacked Plot"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/farms/{farm_id}",
            headers=headers_b,
            json={"area_hectares": 99},
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/farms/{farm_id}", headers=headers_b).status_code == 403

    # Update via PUT & PATCH by owner
    put_resp = client.put(
        f"/api/v1/farms/{farm_id}",
        headers=headers_a,
        json={
            "name": "Pollachi East Block",
            "area_hectares": 5.2,
            "soil_ph": 6.7,
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == "Pollachi East Block"
    assert put_resp.json()["area_hectares"] == 5.2

    patch_resp = client.patch(
        f"/api/v1/farms/{farm_id}",
        headers=headers_a,
        json={"irrigation_type": "sprinkler"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["irrigation_type"] == "sprinkler"

    # Farm validation checks (area <= 0, pH > 14, bad lat, bad irrigation enum)
    assert (
        client.post(
            "/api/v1/farms",
            headers=headers_a,
            json={"name": "Zero Area", "state": "Tamil Nadu", "area_hectares": 0},
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/v1/farms/{farm_id}",
            headers=headers_a,
            json={"soil_ph": 15.0},
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/v1/farms/{farm_id}",
            headers=headers_a,
            json={"irrigation_type": "laser_grid"},
        ).status_code
        == 422
    )

    # Not found UUID returns 404
    missing_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/farms/{missing_id}", headers=headers_a).status_code == 404

    # Delete own farm -> 204 then 404
    del_resp = client.delete(f"/api/v1/farms/{farm_id}", headers=headers_a)
    assert del_resp.status_code == 204
    assert client.get(f"/api/v1/farms/{farm_id}", headers=headers_a).status_code == 404


def test_rbac_admin_routes_and_user_deactivation(isolated_env):
    client, session_factory, _, _ = isolated_env
    farmer = _register_farmer(client, email="rbactest.farmer@terra.in", full_name="Meera Nair")
    farmer_headers = {"Authorization": f"Bearer {farmer['access_token']}"}
    farmer_id = farmer["user"]["id"]

    # Add a farm so admin counts reflect real DB state
    farm_res = client.post(
        "/api/v1/farms",
        headers=farmer_headers,
        json={"name": "Thrissur Wetland", "state": "Kerala", "area_hectares": 3.0},
    )
    assert farm_res.status_code == 201

    # Farmer must receive 403 on all /admin routes
    assert client.get("/api/v1/admin/overview", headers=farmer_headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=farmer_headers).status_code == 403
    assert (
        client.patch(
            f"/api/v1/admin/users/{farmer_id}",
            headers=farmer_headers,
            json={"role": "admin"},
        ).status_code
        == 403
    )

    # Admin login & telemetry overview
    admin = _create_admin_and_login(client, session_factory)
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    admin_id = admin["user"]["id"]

    ov_resp = client.get("/api/v1/admin/overview", headers=admin_headers)
    assert ov_resp.status_code == 200, ov_resp.text
    ov = ov_resp.json()
    assert ov["source_mode"] == "live_api"
    assert ov["total_users"] == 2
    assert ov["active_farms"] == 1
    assert ov["total_predictions"] == 0
    assert any("Active" in m["status"] for m in ov["models"])
    by_mod = {m["module"]: m for m in ov["models"]}
    assert "Plant Disease Vision" in by_mod
    assert by_mod["Plant Disease Vision"]["status"] in {
        "Active (Phase 7 Live)",
        "Artifact Missing",
    }

    # Verify farmer row reports farms_count == 1
    farmer_row = next(u for u in ov["users"] if u["id"] == farmer_id)
    assert farmer_row["farms_count"] == 1

    # Admin cannot deactivate or demote self
    assert (
        client.patch(
            f"/api/v1/admin/users/{admin_id}",
            headers=admin_headers,
            json={"is_active": False},
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/admin/users/{admin_id}",
            headers=admin_headers,
            json={"role": "farmer"},
        ).status_code
        == 400
    )

    # Admin disables farmer account -> farmer blocked on login & existing JWT
    disable_resp = client.patch(
        f"/api/v1/admin/users/{farmer_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    assert client.get("/api/v1/auth/me", headers=farmer_headers).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "rbactest.farmer@terra.in", "password": "HarvestPass#2026"},
        ).status_code
        == 403
    )


def test_database_cascade_delete_and_set_null_relationships(isolated_env):
    client, session_factory, _, _ = isolated_env
    farmer = _register_farmer(client, email="cascade@terra.in", full_name="Cascade Test")
    headers = {"Authorization": f"Bearer {farmer['access_token']}"}
    user_id = uuid.UUID(farmer["user"]["id"])

    farm_resp = client.post(
        "/api/v1/farms",
        headers=headers,
        json={"name": "Cascade Plot", "state": "Karnataka", "area_hectares": 4.0},
    )
    assert farm_resp.status_code == 201
    farm_id = uuid.UUID(farm_resp.json()["id"])

    with session_factory() as db:
        pred = CropPrediction(
            user_id=user_id,
            farm_id=farm_id,
            crop="Rice",
            crop_year=2025,
            season="Kharif",
            state="Karnataka",
            area_hectares=4.0,
            annual_rainfall_mm=1200.0,
            fertilizer_kg=450.0,
            pesticide_kg=12.0,
            predicted_yield=3.4,
            yield_unit="tonnes/hectare",
            estimated_total_production=13.6,
            model_name="pending",
            model_version="v0",
            feature_importance_json={"rainfall": 0.4},
        )
        chat_sess = ChatSession(
            user_id=user_id,
            farm_id=farm_id,
            title="Test Session",
            language="en",
        )
        db.add_all([pred, chat_sess])
        db.flush()
        db.add(
            ChatMessage(
                session_id=chat_sess.id,
                role="user",
                content="Should I irrigate today?",
                citations_json=[],
            )
        )
        db.commit()
        pred_id = pred.id
        sess_id = chat_sess.id

    # Deleting the Farm must SET NULL on CropPrediction.farm_id without deleting pred
    with session_factory() as db:
        farm_obj = db.get(Farm, farm_id)
        db.delete(farm_obj)
        db.commit()

    with session_factory() as db:
        pred_after_farm_del = db.get(CropPrediction, pred_id)
        assert pred_after_farm_del is not None
        assert pred_after_farm_del.farm_id is None

        # Deleting the User must CASCADE delete profile, predictions, chat sessions & messages
        user_obj = db.get(User, user_id)
        db.delete(user_obj)
        db.commit()

    with session_factory() as db:
        assert db.scalar(select(FarmerProfile).where(FarmerProfile.user_id == user_id)) is None
        assert db.get(CropPrediction, pred_id) is None
        assert db.get(ChatSession, sess_id) is None
        assert (
            db.scalar(select(ChatMessage).where(ChatMessage.session_id == sess_id))
            is None
        )
