from datetime import datetime, timezone
import logging
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.farm import Farm
from app.models.modules import IrrigationRecommendation
from app.models.user import User
from app.schemas.weather import (
    DailyForecastPointOut,
    WeatherAlertOut,
    WeatherIrrigationRequest,
    WeatherIrrigationResponse,
)
from app.services.weather_provider import (
    LiveWeatherSnapshot,
    WeatherProviderError,
    get_cached_or_live_weather,
)

logger = logging.getLogger("terraqora.weather.service")

_UNITS_SUMMARY = {
    "temperature": "°C",
    "humidity": "% RH",
    "wind_speed": "km/h",
    "precipitation": "mm",
    "et0": "mm/day",
    "irrigation_depth": "mm",
}

# FAO-56 approximate Kc coefficients by growth stage for major crop groups
_CROP_STAGE_KC: dict[str, dict[str, float]] = {
    "rice": {"initial": 1.05, "development": 1.15, "mid_season": 1.20, "late_season": 0.90},
    "wheat": {"initial": 0.40, "development": 0.80, "mid_season": 1.15, "late_season": 0.40},
    "maize": {"initial": 0.40, "development": 0.80, "mid_season": 1.20, "late_season": 0.60},
    "cotton(lint)": {"initial": 0.35, "development": 0.75, "mid_season": 1.20, "late_season": 0.70},
    "cotton": {"initial": 0.35, "development": 0.75, "mid_season": 1.20, "late_season": 0.70},
    "sugarcane": {"initial": 0.40, "development": 0.85, "mid_season": 1.25, "late_season": 0.75},
    "banana": {"initial": 0.50, "development": 0.85, "mid_season": 1.10, "late_season": 1.00},
    "coconut": {"initial": 0.75, "development": 0.85, "mid_season": 0.95, "late_season": 0.90},
    "potato": {"initial": 0.50, "development": 0.80, "mid_season": 1.15, "late_season": 0.75},
    "onion": {"initial": 0.70, "development": 0.90, "mid_season": 1.05, "late_season": 0.85},
    "tomato": {"initial": 0.60, "development": 0.90, "mid_season": 1.15, "late_season": 0.80},
    "groundnut": {"initial": 0.40, "development": 0.75, "mid_season": 1.15, "late_season": 0.60},
    "soyabean": {"initial": 0.40, "development": 0.80, "mid_season": 1.15, "late_season": 0.50},
}

# Effective rainfall factor by soil texture (water retention vs runoff/percolation)
_SOIL_RAIN_EFFICIENCY: dict[str, float] = {
    "alluvial": 0.75,
    "black (regur)": 0.80,
    "clay loam": 0.80,
    "red loamy": 0.72,
    "laterite": 0.65,
    "sandy loam": 0.60,
}

# Application efficiency by irrigation method
_IRRIGATION_EFFICIENCY: dict[str, float] = {
    "drip": 0.90,
    "sprinkler": 0.78,
    "canal": 0.60,
    "borewell": 0.70,
    "mixed": 0.72,
}


def _resolve_crop_kc(crop_type: str | None, growth_stage: str | None) -> tuple[float | None, bool]:
    if not crop_type or not growth_stage or growth_stage == "unknown":
        return None, False
    key = crop_type.strip().lower()
    stage_map = _CROP_STAGE_KC.get(key)
    if stage_map and growth_stage in stage_map:
        return stage_map[growth_stage], False
    # Generic annual crop FAO-56 fallback if crop is valid text but outside exact table
    generic = {"initial": 0.45, "development": 0.80, "mid_season": 1.10, "late_season": 0.70}
    return generic.get(growth_stage), True


def _build_alerts(snap: LiveWeatherSnapshot, total_rain_7d: float) -> list[WeatherAlertOut]:
    alerts: list[WeatherAlertOut] = []
    near_rain = sum(d.rain_mm for d in snap.forecast_7d[:3])

    if near_rain >= 15.0:
        alerts.append(
            WeatherAlertOut(
                severity="info",
                title="Significant 72-Hour Rainfall Expected",
                message=f"Forecast predicts {near_rain:.1f} mm precipitation within 3 days. Defer non-essential irrigation and ensure field drainage outlets are clear.",
            )
        )
    elif total_rain_7d < 2.0 and snap.current_temp_c >= 34.0:
        alerts.append(
            WeatherAlertOut(
                severity="warning",
                title="Dry Heat Evapotranspiration Stress",
                message=f"Current temperature ({snap.current_temp_c:.1f}°C) with <2 mm 7-day rain elevates crop transpiration demand. Verify topsoil moisture manually.",
            )
        )

    if snap.wind_speed_kmh >= 25.0:
        alerts.append(
            WeatherAlertOut(
                severity="warning",
                title="High Wind Advisory for Sprinklers & Spraying",
                message=f"Surface winds ({snap.wind_speed_kmh:.1f} km/h) increase drift losses; avoid foliar sprays and overhead sprinklers during gusty hours.",
            )
        )
    return alerts


def compute_weather_irrigation_advisory(
    db: Session,
    current_user: User,
    payload: WeatherIrrigationRequest,
) -> WeatherIrrigationResponse:
    settings = get_settings()

    farm: Farm | None = None
    if payload.farm_id is not None:
        farm = db.get(Farm, payload.farm_id)
        if farm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected farm plot was not found.",
            )
        if farm.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this farm plot.",
            )

    # Resolve coordinates from explicit request or owned Farm record
    latitude = payload.latitude if payload.latitude is not None else (farm.latitude if farm else None)
    longitude = payload.longitude if payload.longitude is not None else (farm.longitude if farm else None)

    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Location coordinates (latitude and longitude) are required. "
                "Add GPS coordinates to your farm profile or select an agricultural weather station."
            ),
        )

    location_name = (
        payload.location_name.strip()
        if payload.location_name
        else (
            f"{farm.name} ({farm.district}, {farm.state})"
            if farm
            else f"Coordinates ({latitude:.3f}, {longitude:.3f})"
        )
    )[:120]

    crop_type = (payload.crop_type.strip() if payload.crop_type else (farm.primary_crop if farm else None))
    growth_stage = payload.growth_stage
    soil_type = (payload.soil_type.strip() if payload.soil_type else (farm.soil_type if farm else None))
    irrigation_type = payload.irrigation_type or (farm.irrigation_type if farm else None)

    # Retrieve live weather (or valid short-lived cache)
    try:
        snap = get_cached_or_live_weather(
            settings=settings,
            latitude=float(latitude),
            longitude=float(longitude),
        )
    except WeatherProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    total_rain_7d = round(sum(d.rain_mm for d in snap.forecast_7d), 1)
    avg_et0 = round(
        sum(d.et0_mm for d in snap.forecast_7d) / max(1, len(snap.forecast_7d)), 2
    )
    total_et0_7d = round(sum(d.et0_mm for d in snap.forecast_7d), 1)

    missing_inputs: list[str] = []
    if payload.soil_moisture_pct is None:
        missing_inputs.append("in_field_soil_moisture_sensor_reading")
    if not crop_type:
        missing_inputs.append("crop_type")
    if not growth_stage or growth_stage == "unknown":
        missing_inputs.append("crop_growth_stage")
    if not soil_type:
        missing_inputs.append("soil_type")
    if not irrigation_type:
        missing_inputs.append("irrigation_system_type")

    assumptions: list[str] = [
        f"Forecast and reference ET₀ are meteorological estimates from {snap.provider_label}; physical soil moisture probes are not connected."
    ]
    if payload.soil_moisture_pct is not None:
        assumptions.append(
            f"User-reported topsoil moisture ({payload.soil_moisture_pct:.1f}%) noted as contextual field observation."
        )

    kc_val, used_generic_kc = _resolve_crop_kc(crop_type, growth_stage)
    required_missing = [
        m
        for m in missing_inputs
        if m in {"crop_type", "crop_growth_stage", "soil_type", "irrigation_system_type"}
    ]

    recommended_water_mm: float | None = None
    schedule_status: str
    irrigation_urgency: str
    advisory_notes: str

    if required_missing:
        # Honest abstention: never invent irrigation quantities when required farm/crop inputs are missing
        schedule_status = "insufficient_agronomic_inputs"
        irrigation_urgency = "insufficient_data"
        advisory_notes = (
            f"Live weather summary for {location_name}: {total_rain_7d:.1f} mm 7-day forecast rain vs "
            f"{total_et0_7d:.1f} mm cumulative reference ET₀. Exact irrigation depth (mm) is intentionally "
            f"withheld because required agronomic inputs are missing: {', '.join(required_missing)}. "
            "Supply crop type, growth stage, soil type, and irrigation method (or link a complete Farm profile)."
        )
    elif irrigation_type == "rainfed":
        schedule_status = "rainfed_advisory"
        near_rain = sum(d.rain_mm for d in snap.forecast_7d[:3])
        irrigation_urgency = "skip_rain_expected" if near_rain >= 15.0 else "low"
        recommended_water_mm = 0.0
        assumptions.append(
            "Plot is configured as rainfed (no active pumped/canal irrigation system); schedule focuses on moisture conservation and drainage."
        )
        advisory_notes = (
            f"Rainfed advisory for {crop_type} ({growth_stage.replace('_', ' ')}) on {soil_type} soil: "
            f"{total_rain_7d:.1f} mm 7-day rain expected vs {total_et0_7d:.1f} mm ET₀. "
            "Prioritize bunding/mulching for moisture conservation or clear drainage channels ahead of heavy showers."
        )
    else:
        assert kc_val is not None
        schedule_status = "computed"
        rain_eff = _SOIL_RAIN_EFFICIENCY.get((soil_type or "").lower(), 0.70)
        app_eff = _IRRIGATION_EFFICIENCY.get((irrigation_type or "").lower(), 0.75)

        if soil_type and soil_type.lower() not in _SOIL_RAIN_EFFICIENCY:
            assumptions.append(
                f"Generic effective-rainfall infiltration factor (0.70) applied for soil '{soil_type}'."
            )
        else:
            assumptions.append(
                f"Effective rainfall factor {rain_eff:.2f} applied for {soil_type} soil."
            )
        assumptions.append(
            f"FAO-56 stage coefficient Kc={kc_val:.2f} ({'generic crop table' if used_generic_kc else crop_type}, {growth_stage}) "
            f"and {irrigation_type} application efficiency {app_eff:.2f} assumed."
        )

        crop_etc_7d = total_et0_7d * kc_val
        effective_rain_7d = total_rain_7d * rain_eff
        net_deficit = max(0.0, crop_etc_7d - effective_rain_7d)
        gross_water_mm = round(net_deficit / app_eff, 1) if net_deficit > 0 else 0.0

        # Adjust qualitatively if user explicitly entered very high soil moisture
        if payload.soil_moisture_pct is not None and payload.soil_moisture_pct >= 80.0:
            assumptions.append(
                "Reported soil moisture >= 80%; physical field moisture already appears saturated — verify before irrigating."
            )

        recommended_water_mm = gross_water_mm
        near_rain = sum(d.rain_mm for d in snap.forecast_7d[:3])
        if near_rain >= 15.0 or gross_water_mm < 5.0:
            irrigation_urgency = "skip_rain_expected" if near_rain >= 15.0 else "low"
        elif gross_water_mm < 22.0:
            irrigation_urgency = "moderate"
        else:
            irrigation_urgency = "high"

        advisory_notes = (
            f"Estimated 7-day crop water demand (ETc ≈ {crop_etc_7d:.1f} mm) minus effective forecast rainfall "
            f"({effective_rain_7d:.1f} mm) yields ~{gross_water_mm:.1f} mm gross {irrigation_type} requirement "
            f"for {crop_type} ({growth_stage.replace('_', ' ')}). Manually inspect topsoil at root depth before irrigating."
        )

    freshness_status: str = (
        "cached"
        if snap.cache_hit
        else ("delayed" if snap.observation_age_minutes > 60 else "live")
    )
    alerts = _build_alerts(snap, total_rain_7d)
    sensor_notice = (
        "Weather-Estimated Advisory Only: Uses live meteorological ET₀ and forecast precipitation; "
        "no physical soil moisture probe readings are connected."
    )

    forecast_out = [
        DailyForecastPointOut(
            date=d.date,
            temp_max_c=d.temp_max_c,
            temp_min_c=d.temp_min_c,
            humidity_pct=d.humidity_pct,
            rain_mm=d.rain_mm,
            precipitation_probability_pct=d.precipitation_probability_pct,
            et0_mm=d.et0_mm,
        )
        for d in snap.forecast_7d
    ]

    now_utc = datetime.now(timezone.utc)
    record_id = uuid.uuid4()
    saved_to_history = False

    # Persist irrigation recommendations only when required agronomic inputs produce a real advisory
    if not required_missing and recommended_water_mm is not None:
        snapshot_payload = {
            "provider_id": snap.provider_id,
            "provider_attribution": snap.attribution,
            "observation_time": snap.observation_time.isoformat(),
            "forecast_generated_at": snap.forecast_generated_at.isoformat(),
            "observation_age_minutes": snap.observation_age_minutes,
            "freshness_status": freshness_status,
            "current_temp_c": snap.current_temp_c,
            "current_humidity_pct": snap.current_humidity_pct,
            "wind_speed_kmh": snap.wind_speed_kmh,
            "weather_condition": snap.weather_condition,
            "soil_type": soil_type,
            "irrigation_type": irrigation_type,
            "missing_inputs": missing_inputs,
            "assumptions": assumptions,
            "alerts": [a.model_dump() for a in alerts],
            "forecast_7d": [f.model_dump() for f in forecast_out],
        }
        record = IrrigationRecommendation(
            user_id=current_user.id,
            farm_id=farm.id if farm else None,
            location_name=location_name,
            latitude=float(latitude),
            longitude=float(longitude),
            crop_type=(crop_type or "Unknown")[:80],
            growth_stage=(growth_stage or "mid_season")[:40],
            weather_provider=snap.provider_label[:40],
            weather_snapshot_json=snapshot_payload,
            forecast_rainfall_7d_mm=total_rain_7d,
            estimated_et0_mm=avg_et0,
            recommended_water_mm=float(recommended_water_mm),
            irrigation_urgency=irrigation_urgency,
            is_sensor_backed=False,
            advisory_notes=advisory_notes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
        now_utc = record.created_at
        saved_to_history = True

    return WeatherIrrigationResponse(
        id=record_id,
        saved_to_history=saved_to_history,
        farm_id=farm.id if farm else None,
        location_name=location_name,
        latitude=float(latitude),
        longitude=float(longitude),
        crop_type=crop_type,
        growth_stage=growth_stage,
        soil_type=soil_type,
        irrigation_type=irrigation_type,
        weather_provider=snap.provider_label,
        provider_attribution=snap.attribution,
        observation_time=snap.observation_time,
        forecast_generated_at=snap.forecast_generated_at,
        observation_age_minutes=snap.observation_age_minutes,
        freshness_status=freshness_status,  # type: ignore[arg-type]
        cache_hit=snap.cache_hit,
        units_summary=_UNITS_SUMMARY,
        current_temp_c=snap.current_temp_c,
        current_humidity_pct=snap.current_humidity_pct,
        wind_speed_kmh=snap.wind_speed_kmh,
        weather_condition=snap.weather_condition,
        forecast_rainfall_7d_mm=total_rain_7d,
        estimated_et0_mm=avg_et0,
        recommended_water_mm=recommended_water_mm,
        schedule_status=schedule_status,  # type: ignore[arg-type]
        irrigation_urgency=irrigation_urgency,  # type: ignore[arg-type]
        is_sensor_backed=False,
        sensor_notice=sensor_notice,
        missing_inputs=missing_inputs,
        assumptions=assumptions,
        advisory_notes=advisory_notes,
        alerts=alerts,
        forecast_7d=forecast_out,
        created_at=now_utc,
        source_mode="live_api",
    )


def list_irrigation_history(
    db: Session,
    current_user: User,
    *,
    limit: int = 10,
) -> list[WeatherIrrigationResponse]:
    rows = db.scalars(
        select(IrrigationRecommendation)
        .where(IrrigationRecommendation.user_id == current_user.id)
        .order_by(IrrigationRecommendation.created_at.desc())
        .limit(limit)
    ).all()

    results: list[WeatherIrrigationResponse] = []
    for row in rows:
        snap = row.weather_snapshot_json or {}
        obs_str = snap.get("observation_time") or row.created_at.isoformat()
        gen_str = snap.get("forecast_generated_at") or row.created_at.isoformat()
        try:
            obs_dt = datetime.fromisoformat(obs_str)
        except ValueError:
            obs_dt = row.created_at
        try:
            gen_dt = datetime.fromisoformat(gen_str)
        except ValueError:
            gen_dt = row.created_at

        results.append(
            WeatherIrrigationResponse(
                id=row.id,
                saved_to_history=True,
                farm_id=row.farm_id,
                location_name=row.location_name,
                latitude=float(row.latitude),
                longitude=float(row.longitude),
                crop_type=row.crop_type,
                growth_stage=row.growth_stage,
                soil_type=snap.get("soil_type"),
                irrigation_type=snap.get("irrigation_type"),
                weather_provider=row.weather_provider,
                provider_attribution=str(
                    snap.get("provider_attribution") or "Open-Meteo / Weather History"
                ),
                observation_time=obs_dt,
                forecast_generated_at=gen_dt,
                observation_age_minutes=int(snap.get("observation_age_minutes") or 0),
                freshness_status="cached",
                cache_hit=True,
                units_summary=_UNITS_SUMMARY,
                current_temp_c=float(snap.get("current_temp_c") or 0.0),
                current_humidity_pct=float(snap.get("current_humidity_pct") or 0.0),
                wind_speed_kmh=float(snap.get("wind_speed_kmh") or 0.0),
                weather_condition=str(snap.get("weather_condition") or "Recorded Advisory"),
                forecast_rainfall_7d_mm=float(row.forecast_rainfall_7d_mm),
                estimated_et0_mm=float(row.estimated_et0_mm),
                recommended_water_mm=float(row.recommended_water_mm),
                schedule_status=(
                    "rainfed_advisory"
                    if snap.get("irrigation_type") == "rainfed"
                    else "computed"
                ),
                irrigation_urgency=row.irrigation_urgency,  # type: ignore[arg-type]
                is_sensor_backed=False,
                sensor_notice="Weather-Estimated Historical Advisory (Not physical soil sensor reading).",
                missing_inputs=list(snap.get("missing_inputs") or []),
                assumptions=list(snap.get("assumptions") or []),
                advisory_notes=row.advisory_notes,
                alerts=[WeatherAlertOut(**a) for a in (snap.get("alerts") or [])],
                forecast_7d=[
                    DailyForecastPointOut(**f) for f in (snap.get("forecast_7d") or [])
                ],
                created_at=row.created_at,
                source_mode="live_api",
            )
        )
    return results
