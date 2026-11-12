from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import math
import threading
import time
from typing import Any

import httpx

logger = logging.getLogger("terraqora.weather.provider")

_WMO_WEATHER_DESCRIPTIONS: dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}


class WeatherProviderError(RuntimeError):
    """Structured non-leaking exception raised by live weather adapters."""

    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class DailyWeatherPoint:
    date: str
    temp_max_c: float
    temp_min_c: float
    humidity_pct: float
    rain_mm: float
    precipitation_probability_pct: int | None
    et0_mm: float


@dataclass(frozen=True)
class LiveWeatherSnapshot:
    provider_id: str
    provider_label: str
    attribution: str
    observation_time: datetime
    forecast_generated_at: datetime
    observation_age_minutes: int
    current_temp_c: float
    current_humidity_pct: float
    wind_speed_kmh: float
    weather_condition: str
    forecast_7d: tuple[DailyWeatherPoint, ...]
    cache_hit: bool = False


class WeatherProvider(ABC):
    @abstractmethod
    def fetch_forecast(
        self, *, latitude: float, longitude: float
    ) -> LiveWeatherSnapshot:
        """Fetch live current weather + 7-day daily forecast for coordinates."""


def _redact_secret(text: str, secret: str | None) -> str:
    if secret and len(secret) >= 4:
        return text.replace(secret, "[REDACTED]")
    return text


def _safe_float(val: Any, field: str) -> float:
    try:
        num = float(val)
    except (TypeError, ValueError) as exc:
        raise WeatherProviderError(
            "invalid_response",
            f"Weather provider returned non-numeric value for '{field}'.",
            status_code=502,
        ) from exc
    if not math.isfinite(num):
        raise WeatherProviderError(
            "invalid_response",
            f"Weather provider returned invalid finite range for '{field}'.",
            status_code=502,
        )
    return num


def _parse_iso_timestamp(raw: Any, utc_offset_seconds: int = 0) -> datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise WeatherProviderError(
            "invalid_response",
            "Weather provider omitted observation timestamp.",
            status_code=502,
        )
    normalized = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WeatherProviderError(
            "invalid_response",
            "Weather provider returned malformed observation timestamp.",
            status_code=502,
        ) from exc

    if parsed.tzinfo is None:
        tz = timezone(timedelta(seconds=utc_offset_seconds))
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(timezone.utc)


def _validate_freshness(
    *,
    observation_time: datetime,
    now_utc: datetime,
    stale_max_age_minutes: int,
) -> int:
    age_minutes = max(0, int((now_utc - observation_time).total_seconds() // 60))
    if age_minutes > stale_max_age_minutes:
        raise WeatherProviderError(
            "stale_data",
            (
                f"Live weather observation is stale ({age_minutes} minutes old, "
                f"exceeding the {stale_max_age_minutes}-minute freshness limit). "
                "Refresh later rather than relying on outdated conditions."
            ),
            status_code=503,
        )
    return age_minutes


class OpenMeteoProvider(WeatherProvider):
    provider_id = "open_meteo"
    provider_label = "Open-Meteo Live Forecast API"
    attribution = "Weather data by Open-Meteo.com (CC BY 4.0 non-commercial open API)"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        stale_max_age_minutes: int = 180,
        http_get: Callable[..., httpx.Response] | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.stale_max_age_minutes = max(15, int(stale_max_age_minutes))
        self._http_get = http_get
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def fetch_forecast(
        self, *, latitude: float, longitude: float
    ) -> LiveWeatherSnapshot:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": round(float(latitude), 4),
            "longitude": round(float(longitude), 4),
            "current": (
                "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                "weather_code,precipitation"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "precipitation_probability_max,et0_fao_evapotranspiration,"
                "relative_humidity_2m_mean"
            ),
            "forecast_days": 7,
            "timezone": "auto",
        }

        try:
            if self._http_get is not None:
                resp = self._http_get(
                    url, params=params, timeout=self.timeout_seconds
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise WeatherProviderError(
                "timeout",
                "Live weather provider timed out before returning forecast data. Please retry.",
                status_code=504,
            ) from exc
        except httpx.HTTPError as exc:
            raise WeatherProviderError(
                "upstream_unreachable",
                "Unable to reach live weather provider right now. Check connectivity and retry.",
                status_code=503,
            ) from exc

        if resp.status_code == 429:
            raise WeatherProviderError(
                "rate_limited",
                "Weather API rate limit reached temporarily. Please retry in a few minutes.",
                status_code=429,
            )
        if resp.status_code >= 400:
            raise WeatherProviderError(
                "upstream_error",
                "Live weather provider returned an upstream error response.",
                status_code=502,
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise WeatherProviderError(
                "invalid_response",
                "Weather provider returned malformed non-JSON payload.",
                status_code=502,
            ) from exc

        if not isinstance(payload, dict):
            raise WeatherProviderError(
                "invalid_response",
                "Weather provider returned unexpected response structure.",
                status_code=502,
            )

        current = payload.get("current")
        daily = payload.get("daily")
        if not isinstance(current, dict) or not isinstance(daily, dict):
            raise WeatherProviderError(
                "invalid_response",
                "Weather provider response is missing required 'current' or 'daily' blocks.",
                status_code=502,
            )

        utc_offset = int(payload.get("utc_offset_seconds") or 0)
        now_utc = self._now_fn()
        obs_time = _parse_iso_timestamp(current.get("time"), utc_offset)
        age_minutes = _validate_freshness(
            observation_time=obs_time,
            now_utc=now_utc,
            stale_max_age_minutes=self.stale_max_age_minutes,
        )

        temp_c = _safe_float(current.get("temperature_2m"), "temperature_2m")
        hum_pct = max(
            0.0,
            min(
                100.0,
                _safe_float(current.get("relative_humidity_2m"), "relative_humidity_2m"),
            ),
        )
        wind_kmh = max(
            0.0, _safe_float(current.get("wind_speed_10m"), "wind_speed_10m")
        )
        wmo_code = int(_safe_float(current.get("weather_code", 0), "weather_code"))
        condition = _WMO_WEATHER_DESCRIPTIONS.get(
            wmo_code, f"Meteorological Code {wmo_code}"
        )

        dates = daily.get("time") or []
        t_max = daily.get("temperature_2m_max") or []
        t_min = daily.get("temperature_2m_min") or []
        rain_sums = daily.get("precipitation_sum") or []
        rain_probs = daily.get("precipitation_probability_max") or []
        et0_vals = daily.get("et0_fao_evapotranspiration") or []
        hum_means = daily.get("relative_humidity_2m_mean") or []

        n_days = min(
            len(dates), len(t_max), len(t_min), len(rain_sums), len(et0_vals)
        )
        if n_days == 0:
            raise WeatherProviderError(
                "invalid_response",
                "Weather provider returned zero daily forecast entries.",
                status_code=502,
            )

        points: list[DailyWeatherPoint] = []
        for idx in range(n_days):
            prob_raw = rain_probs[idx] if idx < len(rain_probs) else None
            prob_val = (
                max(0, min(100, int(prob_raw))) if prob_raw is not None else None
            )
            hum_mean_raw = hum_means[idx] if idx < len(hum_means) else hum_pct
            points.append(
                DailyWeatherPoint(
                    date=str(dates[idx]),
                    temp_max_c=round(_safe_float(t_max[idx], "temperature_2m_max"), 1),
                    temp_min_c=round(_safe_float(t_min[idx], "temperature_2m_min"), 1),
                    humidity_pct=round(
                        max(0.0, min(100.0, float(hum_mean_raw))), 1
                    ),
                    rain_mm=round(
                        max(0.0, _safe_float(rain_sums[idx], "precipitation_sum")), 1
                    ),
                    precipitation_probability_pct=prob_val,
                    et0_mm=round(
                        max(
                            0.0,
                            _safe_float(
                                et0_vals[idx], "et0_fao_evapotranspiration"
                            ),
                        ),
                        2,
                    ),
                )
            )

        return LiveWeatherSnapshot(
            provider_id=self.provider_id,
            provider_label=self.provider_label,
            attribution=self.attribution,
            observation_time=obs_time,
            forecast_generated_at=now_utc,
            observation_age_minutes=age_minutes,
            current_temp_c=round(temp_c, 1),
            current_humidity_pct=round(hum_pct, 1),
            wind_speed_kmh=round(wind_kmh, 1),
            weather_condition=condition,
            forecast_7d=tuple(points),
            cache_hit=False,
        )


class OpenWeatherProvider(WeatherProvider):
    """Optional authenticated OpenWeatherMap adapter (5-day/3-hour forecast)."""

    provider_id = "openweather"
    provider_label = "OpenWeatherMap Forecast API"
    attribution = "Weather data by OpenWeatherMap"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 10.0,
        stale_max_age_minutes: int = 180,
        http_get: Callable[..., httpx.Response] | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.stale_max_age_minutes = max(15, int(stale_max_age_minutes))
        self._http_get = http_get
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def fetch_forecast(
        self, *, latitude: float, longitude: float
    ) -> LiveWeatherSnapshot:
        if not self._api_key:
            raise WeatherProviderError(
                "missing_key",
                "OpenWeatherMap API key is not configured on the backend server. Configure OPENWEATHER_API_KEY or switch WEATHER_PROVIDER=open_meteo.",
                status_code=503,
            )

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": round(float(latitude), 4),
            "lon": round(float(longitude), 4),
            "appid": self._api_key,
            "units": "metric",
        }
        try:
            if self._http_get is not None:
                resp = self._http_get(
                    url, params=params, timeout=self.timeout_seconds
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise WeatherProviderError(
                "timeout",
                "OpenWeatherMap timed out while fetching live forecast.",
                status_code=504,
            ) from exc
        except httpx.HTTPError as exc:
            msg = _redact_secret(str(exc), self._api_key)
            logger.warning("OpenWeatherMap request failed: %s", msg)
            raise WeatherProviderError(
                "upstream_unreachable",
                "Unable to connect to OpenWeatherMap service.",
                status_code=503,
            ) from exc

        if resp.status_code in (401, 403):
            raise WeatherProviderError(
                "invalid_credentials",
                "OpenWeatherMap API credentials could not be verified.",
                status_code=503,
            )
        if resp.status_code == 429:
            raise WeatherProviderError(
                "rate_limited",
                "OpenWeatherMap rate limit reached temporarily.",
                status_code=429,
            )
        if resp.status_code >= 400:
            raise WeatherProviderError(
                "upstream_error",
                "OpenWeatherMap returned an upstream error.",
                status_code=502,
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise WeatherProviderError(
                "invalid_response",
                "OpenWeatherMap returned invalid JSON payload.",
                status_code=502,
            ) from exc

        items = payload.get("list") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            raise WeatherProviderError(
                "invalid_response",
                "OpenWeatherMap response contained no forecast slices.",
                status_code=502,
            )

        now_utc = self._now_fn()
        first = items[0]
        dt_unix = _safe_float(first.get("dt"), "dt")
        obs_time = datetime.fromtimestamp(dt_unix, tz=timezone.utc)
        age_minutes = _validate_freshness(
            observation_time=obs_time,
            now_utc=now_utc,
            stale_max_age_minutes=self.stale_max_age_minutes,
        )

        main = first.get("main") or {}
        wind = first.get("wind") or {}
        weather_list = first.get("weather") or [{}]
        temp_c = _safe_float(main.get("temp"), "main.temp")
        hum_pct = _safe_float(main.get("humidity"), "main.humidity")
        wind_ms = _safe_float(wind.get("speed", 0.0), "wind.speed")
        cond = str(weather_list[0].get("description") or "Forecast Conditions").title()

        daily_buckets: dict[str, dict[str, Any]] = {}
        for entry in items:
            dt_str = datetime.fromtimestamp(
                _safe_float(entry.get("dt"), "dt"), tz=timezone.utc
            ).strftime("%Y-%m-%d")
            m = entry.get("main") or {}
            rain_3h = float((entry.get("rain") or {}).get("3h") or 0.0)
            pop = entry.get("pop")
            b = daily_buckets.setdefault(
                dt_str,
                {
                    "tmax": [],
                    "tmin": [],
                    "hum": [],
                    "rain": 0.0,
                    "pop": [],
                },
            )
            b["tmax"].append(_safe_float(m.get("temp_max", m.get("temp")), "temp_max"))
            b["tmin"].append(_safe_float(m.get("temp_min", m.get("temp")), "temp_min"))
            b["hum"].append(_safe_float(m.get("humidity", hum_pct), "humidity"))
            b["rain"] += rain_3h
            if pop is not None:
                b["pop"].append(int(round(float(pop) * 100)))

        points: list[DailyWeatherPoint] = []
        for date_key in sorted(daily_buckets)[:7]:
            b = daily_buckets[date_key]
            tmax = max(b["tmax"])
            tmin = min(b["tmin"])
            tmean = (tmax + tmin) / 2.0
            # Hargreaves-Samani simplified reference ET0 when provider omits ET0
            doy = datetime.strptime(date_key, "%Y-%m-%d").timetuple().tm_yday
            lat_rad = math.radians(latitude)
            dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * doy / 365.0)
            decl = 0.409 * math.sin(2.0 * math.pi * doy / 365.0 - 1.39)
            ws = math.acos(
                max(-1.0, min(1.0, -math.tan(lat_rad) * math.tan(decl)))
            )
            ra = (
                (24.0 * 60.0 / math.pi)
                * 0.0820
                * dr
                * (
                    ws * math.sin(lat_rad) * math.sin(decl)
                    + math.cos(lat_rad) * math.cos(decl) * math.sin(ws)
                )
            )
            ra_mm = ra * 0.408
            et0_est = max(
                0.5, 0.0023 * (tmean + 17.8) * math.sqrt(max(0.5, tmax - tmin)) * ra_mm
            )
            points.append(
                DailyWeatherPoint(
                    date=date_key,
                    temp_max_c=round(tmax, 1),
                    temp_min_c=round(tmin, 1),
                    humidity_pct=round(sum(b["hum"]) / len(b["hum"]), 1),
                    rain_mm=round(max(0.0, b["rain"]), 1),
                    precipitation_probability_pct=max(b["pop"]) if b["pop"] else None,
                    et0_mm=round(et0_est, 2),
                )
            )

        return LiveWeatherSnapshot(
            provider_id=self.provider_id,
            provider_label=self.provider_label,
            attribution=self.attribution,
            observation_time=obs_time,
            forecast_generated_at=now_utc,
            observation_age_minutes=age_minutes,
            current_temp_c=round(temp_c, 1),
            current_humidity_pct=round(hum_pct, 1),
            wind_speed_kmh=round(wind_ms * 3.6, 1),
            weather_condition=cond,
            forecast_7d=tuple(points),
            cache_hit=False,
        )


_CACHE_LOCK = threading.Lock()
_WEATHER_CACHE: dict[tuple[str, float, float], tuple[float, LiveWeatherSnapshot]] = {}
_PROVIDER_FACTORY_OVERRIDE: Callable[[Any], WeatherProvider] | None = None


def set_provider_factory_for_testing(
    factory: Callable[[Any], WeatherProvider] | None,
) -> None:
    global _PROVIDER_FACTORY_OVERRIDE
    _PROVIDER_FACTORY_OVERRIDE = factory


def reset_weather_cache() -> None:
    with _CACHE_LOCK:
        _WEATHER_CACHE.clear()


def build_weather_provider(settings: Any) -> WeatherProvider:
    if _PROVIDER_FACTORY_OVERRIDE is not None:
        return _PROVIDER_FACTORY_OVERRIDE(settings)

    provider_name = getattr(settings, "WEATHER_PROVIDER", "open_meteo")
    timeout = float(getattr(settings, "WEATHER_TIMEOUT_SECONDS", 10.0))
    stale_mins = int(getattr(settings, "WEATHER_STALE_MAX_AGE_MINUTES", 180))

    if provider_name == "openweather":
        return OpenWeatherProvider(
            api_key=getattr(settings, "resolved_openweather_api_key", ""),
            timeout_seconds=timeout,
            stale_max_age_minutes=stale_mins,
        )

    return OpenMeteoProvider(
        timeout_seconds=timeout,
        stale_max_age_minutes=stale_mins,
    )


def get_cached_or_live_weather(
    *,
    settings: Any,
    latitude: float,
    longitude: float,
) -> LiveWeatherSnapshot:
    provider = build_weather_provider(settings)
    provider_id = getattr(provider, "provider_id", getattr(settings, "WEATHER_PROVIDER", "open_meteo"))
    ttl = max(0, int(getattr(settings, "WEATHER_CACHE_TTL_SECONDS", 900)))
    cache_key = (str(provider_id), round(float(latitude), 3), round(float(longitude), 3))

    now_mono = time.monotonic()
    stale_limit_sec = max(60, int(getattr(settings, "WEATHER_STALE_MAX_AGE_MINUTES", 180)) * 60)

    if ttl > 0:
        with _CACHE_LOCK:
            cached = _WEATHER_CACHE.get(cache_key)
            if cached is not None:
                cached_at, snap = cached
                cache_age = now_mono - cached_at
                if cache_age <= ttl and (snap.observation_age_minutes * 60 + cache_age) <= stale_limit_sec:
                    return LiveWeatherSnapshot(
                        provider_id=snap.provider_id,
                        provider_label=snap.provider_label,
                        attribution=snap.attribution,
                        observation_time=snap.observation_time,
                        forecast_generated_at=snap.forecast_generated_at,
                        observation_age_minutes=snap.observation_age_minutes + int(cache_age // 60),
                        current_temp_c=snap.current_temp_c,
                        current_humidity_pct=snap.current_humidity_pct,
                        wind_speed_kmh=snap.wind_speed_kmh,
                        weather_condition=snap.weather_condition,
                        forecast_7d=snap.forecast_7d,
                        cache_hit=True,
                    )
                _WEATHER_CACHE.pop(cache_key, None)

    fresh = provider.fetch_forecast(latitude=latitude, longitude=longitude)
    if ttl > 0:
        with _CACHE_LOCK:
            _WEATHER_CACHE[cache_key] = (now_mono, fresh)
    return fresh
