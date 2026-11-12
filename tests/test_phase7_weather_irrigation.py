from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import secrets
import sys
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import httpx
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
from app.models.modules import IrrigationRecommendation  # noqa: E402
from app.services import weather_provider  # noqa: E402
from app.services.weather_provider import (  # noqa: E402
    OpenMeteoProvider,
    OpenWeatherProvider,
    WeatherProviderError,
)


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture()
def isolated_weather_client(tmp_path: Path):
    db_file = tmp_path / "phase7_weather_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
    weather_provider.reset_weather_cache()
    weather_provider.set_provider_factory_for_testing(None)
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

    weather_provider.reset_weather_cache()
    weather_provider.set_provider_factory_for_testing(None)


def _register_headers(client: TestClient, email: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Weather Test Farmer",
            "email": email,
            "password": "StrongPassword!123",
            "preferred_language": "en",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _sample_open_meteo_payload(obs_time_iso: str) -> dict:
    base_date = datetime(2026, 11, 12, tzinfo=timezone.utc).date()
    return {
        "latitude": 11.0168,
        "longitude": 76.9558,
        "utc_offset_seconds": 0,
        "current": {
            "time": obs_time_iso,
            "temperature_2m": 30.4,
            "relative_humidity_2m": 66.0,
            "wind_speed_10m": 12.2,
            "weather_code": 2,
            "precipitation": 0.0,
        },
        "daily": {
            "time": [(base_date + timedelta(days=i)).isoformat() for i in range(7)],
            "temperature_2m_max": [32.1, 31.8, 29.4, 28.9, 30.2, 31.0, 31.5],
            "temperature_2m_min": [23.2, 23.0, 22.4, 22.1, 22.8, 23.0, 23.1],
            "precipitation_sum": [0.0, 0.4, 2.0, 1.0, 0.0, 0.0, 0.2],
            "precipitation_probability_max": [10, 20, 45, 30, 10, 10, 15],
            "et0_fao_evapotranspiration": [4.6, 4.5, 3.9, 3.8, 4.4, 4.7, 4.8],
            "relative_humidity_2m_mean": [62, 65, 74, 72, 64, 60, 61],
        },
    }


def _mock_response(status_code: int, json_body=None, text_body: str = "") -> httpx.Response:
    req = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    if json_body is not None:
        return httpx.Response(status_code=status_code, json=json_body, request=req)
    return httpx.Response(status_code=status_code, text=text_body, request=req)


def test_open_meteo_provider_success_stale_timeout_rate_limit_and_invalid_json():
    now_utc = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)
    fresh_obs = (now_utc - timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M")

    p_ok = OpenMeteoProvider(
        http_get=lambda *_args, **_kw: _mock_response(
            200, _sample_open_meteo_payload(fresh_obs)
        ),
        now_fn=lambda: now_utc,
    )
    snap = p_ok.fetch_forecast(latitude=11.0168, longitude=76.9558)
    assert snap.provider_id == "open_meteo"
    assert snap.observation_age_minutes == 25
    assert snap.current_temp_c == 30.4
    assert len(snap.forecast_7d) == 7
    assert "CC BY 4.0" in snap.attribution

    # Stale weather (> 180 mins old) rejected cleanly
    stale_obs = (now_utc - timedelta(minutes=240)).strftime("%Y-%m-%dT%H:%M")
    p_stale = OpenMeteoProvider(
        stale_max_age_minutes=180,
        http_get=lambda *_args, **_kw: _mock_response(
            200, _sample_open_meteo_payload(stale_obs)
        ),
        now_fn=lambda: now_utc,
    )
    with pytest.raises(WeatherProviderError) as stale_exc:
        p_stale.fetch_forecast(latitude=11.0, longitude=77.0)
    assert stale_exc.value.code == "stale_data"
    assert stale_exc.value.status_code == 503

    # Timeout -> 504
    def raise_timeout(*_args, **_kw):
        raise httpx.ReadTimeout("timeout")

    with pytest.raises(WeatherProviderError) as timeout_exc:
        OpenMeteoProvider(http_get=raise_timeout).fetch_forecast(
            latitude=11.0, longitude=77.0
        )
    assert timeout_exc.value.status_code == 504

    # Upstream rate limit -> 429
    with pytest.raises(WeatherProviderError) as rate_exc:
        OpenMeteoProvider(
            http_get=lambda *_a, **_k: _mock_response(429, {"error": True})
        ).fetch_forecast(latitude=11.0, longitude=77.0)
    assert rate_exc.value.status_code == 429

    # Malformed non-JSON / missing fields -> 502
    with pytest.raises(WeatherProviderError) as bad_json_exc:
        OpenMeteoProvider(
            http_get=lambda *_a, **_k: _mock_response(200, text_body="<html>bad</html>")
        ).fetch_forecast(latitude=11.0, longitude=77.0)
    assert bad_json_exc.value.status_code == 502

    with pytest.raises(WeatherProviderError) as missing_blocks_exc:
        OpenMeteoProvider(
            http_get=lambda *_a, **_k: _mock_response(200, {"current": {}})
        ).fetch_forecast(latitude=11.0, longitude=77.0)
    assert missing_blocks_exc.value.status_code == 502


def test_openweather_missing_and_invalid_key_handling():
    p_missing = OpenWeatherProvider(api_key="")
    with pytest.raises(WeatherProviderError) as exc_missing:
        p_missing.fetch_forecast(latitude=11.0, longitude=77.0)
    assert exc_missing.value.code == "missing_key"
    assert exc_missing.value.status_code == 503

    p_bad = OpenWeatherProvider(
        api_key="owm-secret-test-key",
        http_get=lambda *_a, **_k: _mock_response(401, {"message": "Invalid API key"}),
    )
    with pytest.raises(WeatherProviderError) as exc_bad:
        p_bad.fetch_forecast(latitude=11.0, longitude=77.0)
    assert exc_bad.value.code == "invalid_credentials"
    assert exc_bad.value.status_code == 503
    assert "owm-secret-test-key" not in exc_bad.value.message


def test_weather_irrigation_endpoint_farm_context_caching_and_missing_inputs(
    isolated_weather_client,
):
    client, SessionLocal = isolated_weather_client
    now_utc = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)
    obs_iso = (now_utc - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    call_counter = {"count": 0}

    def fake_http_get(*_args, **_kw):
        call_counter["count"] += 1
        return _mock_response(200, _sample_open_meteo_payload(obs_iso))

    weather_provider.set_provider_factory_for_testing(
        lambda _s: OpenMeteoProvider(
            http_get=fake_http_get,
            now_fn=lambda: now_utc,
        )
    )

    assert client.post("/api/v1/weather/irrigation", json={}).status_code == 401

    headers_a = _register_headers(client, "farmer_wx_a@example.com")
    headers_b = _register_headers(client, "farmer_wx_b@example.com")

    farm_a = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Thanjavur Plot 1",
            "state": "Tamil Nadu",
            "district": "Thanjavur",
            "latitude": 10.787,
            "longitude": 79.1378,
            "area_hectares": 3.0,
            "soil_type": "Alluvial",
            "soil_ph": 6.7,
            "irrigation_type": "canal",
            "primary_crop": "Rice",
        },
    ).json()

    # Cross-user farm access blocked
    assert (
        client.post(
            "/api/v1/weather/irrigation",
            headers=headers_b,
            json={"farm_id": farm_a["id"], "growth_stage": "mid_season"},
        ).status_code
        == 403
    )

    # Missing coordinates rejected cleanly with 422
    assert (
        client.post(
            "/api/v1/weather/irrigation",
            headers=headers_a,
            json={"crop_type": "Rice", "growth_stage": "mid_season"},
        ).status_code
        == 422
    )

    # Complete farm context computes water schedule + persists history
    res1 = client.post(
        "/api/v1/weather/irrigation",
        headers=headers_a,
        json={"farm_id": farm_a["id"], "growth_stage": "mid_season"},
    )
    assert res1.status_code == 200, res1.text
    d1 = res1.json()
    assert d1["saved_to_history"] is True
    assert d1["schedule_status"] == "computed"
    assert d1["recommended_water_mm"] > 0
    assert d1["is_sensor_backed"] is False
    assert "in_field_soil_moisture_sensor_reading" in d1["missing_inputs"]
    assert d1["cache_hit"] is False
    assert call_counter["count"] == 1

    # Second identical coordinate request uses TTL cache
    res2 = client.post(
        "/api/v1/weather/irrigation",
        headers=headers_a,
        json={"farm_id": farm_a["id"], "growth_stage": "mid_season"},
    )
    assert res2.status_code == 200
    assert res2.json()["cache_hit"] is True
    assert call_counter["count"] == 1

    # Missing agronomic inputs (soil_type & irrigation_type missing) -> abstains from inventing quantity & does not persist
    res_missing = client.post(
        "/api/v1/weather/irrigation",
        headers=headers_a,
        json={
            "location_name": "Erode Field",
            "latitude": 11.341,
            "longitude": 77.717,
            "crop_type": "Rice",
            "growth_stage": "unknown",
        },
    )
    assert res_missing.status_code == 200, res_missing.text
    dm = res_missing.json()
    assert dm["recommended_water_mm"] is None
    assert dm["schedule_status"] == "insufficient_agronomic_inputs"
    assert dm["irrigation_urgency"] == "insufficient_data"
    assert dm["saved_to_history"] is False
    assert "soil_type" in dm["missing_inputs"]
    assert "irrigation_system_type" in dm["missing_inputs"]
    assert "crop_growth_stage" in dm["missing_inputs"]

    # History only includes complete saved advisories and isolates users
    hist_a = client.get("/api/v1/weather/irrigation/history", headers=headers_a).json()
    hist_b = client.get("/api/v1/weather/irrigation/history", headers=headers_b).json()
    assert len(hist_a) == 2
    assert hist_b == []

    with SessionLocal() as db:
        rows = db.scalars(select(IrrigationRecommendation)).all()
        assert len(rows) == 2
