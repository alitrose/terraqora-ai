import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Clock,
  CloudRain,
  Droplets,
  History,
  Info,
  MapPin,
  ShieldAlert,
  Thermometer,
  Wind,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { profileService, weatherService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import {
  SOIL_TYPES,
  WEATHER_LOCATION_PRESETS,
  YIELD_CROPS,
} from '../data/agriCatalog';
import type {
  Farm,
  WeatherIrrigationRequest,
  WeatherIrrigationResponse,
} from '../types/api';

type StageOption =
  | 'initial'
  | 'development'
  | 'mid_season'
  | 'late_season'
  | 'unknown';
type IrrigationOption =
  | ''
  | 'rainfed'
  | 'drip'
  | 'sprinkler'
  | 'canal'
  | 'borewell'
  | 'mixed';

export function WeatherIrrigationPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState('');
  const [presetIdx, setPresetIdx] = useState(0);
  const [cropType, setCropType] = useState('Rice');
  const [growthStage, setGrowthStage] = useState<StageOption>('mid_season');
  const [soilType, setSoilType] = useState('Alluvial');
  const [irrigationType, setIrrigationType] = useState<IrrigationOption>('canal');
  const [soilMoisturePct, setSoilMoisturePct] = useState('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WeatherIrrigationResponse | null>(null);
  const [history, setHistory] = useState<WeatherIrrigationResponse[]>([]);

  const buildPayload = (
    farmId = selectedFarmId,
    idx = presetIdx,
    crop = cropType,
    stage = growthStage,
    soil = soilType,
    irr = irrigationType,
    moistureStr = soilMoisturePct
  ): WeatherIrrigationRequest => {
    const chosenFarm = farms.find((f) => f.id === farmId) || null;
    const preset = WEATHER_LOCATION_PRESETS[idx];
    const hasFarmCoords =
      chosenFarm?.latitude != null && chosenFarm?.longitude != null;

    const moistureVal =
      moistureStr.trim() !== '' && !Number.isNaN(Number(moistureStr))
        ? Number(moistureStr)
        : null;

    return {
      farm_id: farmId || null,
      location_name: hasFarmCoords
        ? `${chosenFarm!.name} (${chosenFarm!.district}, ${chosenFarm!.state})`
        : preset.name,
      latitude: hasFarmCoords ? chosenFarm!.latitude! : preset.lat,
      longitude: hasFarmCoords ? chosenFarm!.longitude! : preset.lon,
      crop_type: crop || undefined,
      growth_stage: stage,
      soil_type: soil || null,
      irrigation_type: irr || null,
      soil_moisture_pct: moistureVal,
    };
  };

  const fetchForecast = async (overridePayload?: WeatherIrrigationRequest) => {
    const payload = overridePayload ?? buildPayload();
    setLoading(true);
    setError(null);
    try {
      const res = await weatherService.getIrrigationAdvisory(payload);
      setData(res);
      if (res.saved_to_history) {
        const hist = await weatherService.getIrrigationHistory().catch(() => []);
        if (hist.length > 0) setHistory(hist);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Unable to fetch live weather forecast.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    const init = async () => {
      try {
        const [farmList, histList] = await Promise.all([
          profileService.listFarms().catch(() => [] as Farm[]),
          weatherService.getIrrigationHistory().catch(() => [] as WeatherIrrigationResponse[]),
        ]);
        if (!active) return;
        setFarms(farmList);
        setHistory(histList);
        const firstFarm = farmList[0];
        if (firstFarm) {
          setSelectedFarmId(firstFarm.id);
          if (firstFarm.primary_crop) setCropType(firstFarm.primary_crop);
          if (firstFarm.soil_type) setSoilType(firstFarm.soil_type);
          if (firstFarm.irrigation_type) setIrrigationType(firstFarm.irrigation_type);
          await fetchForecast(
            buildPayload(
              firstFarm.id,
              0,
              firstFarm.primary_crop || 'Rice',
              'mid_season',
              firstFarm.soil_type || 'Alluvial',
              firstFarm.irrigation_type || 'canal',
              ''
            )
          );
        } else {
          await fetchForecast();
        }
      } catch {
        if (active) await fetchForecast();
      }
    };
    init();
    return () => {
      active = false;
    };
  }, []);

  const handleSelectFarm = (farmId: string) => {
    setSelectedFarmId(farmId);
    const chosen = farms.find((f) => f.id === farmId);
    if (chosen) {
      if (chosen.primary_crop) setCropType(chosen.primary_crop);
      setSoilType(chosen.soil_type || '');
      setIrrigationType(chosen.irrigation_type || '');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchForecast();
  };

  return (
    <AppShell
      title="Weather & Irrigation Intelligence"
      subtitle="Live meteorological conditions, 7-day ET₀ balance, and transparent farm-aware irrigation timing."
    >
      <form
        onSubmit={handleSubmit}
        className="mb-6 grid gap-4 rounded-2xl border border-soil-border bg-white p-5 shadow-card sm:grid-cols-2 lg:grid-cols-4"
      >
        <div>
          <label htmlFor="wx-farm" className="block text-xs font-semibold text-soil-charcoal">
            Link Farm Plot (Optional)
          </label>
          <select
            id="wx-farm"
            value={selectedFarmId}
            onChange={(e) => handleSelectFarm(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            <option value="">Custom / Station Location</option>
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.district})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="wx-loc" className="block text-xs font-semibold text-soil-charcoal">
            Agricultural Station (Fallback Coords)
          </label>
          <select
            id="wx-loc"
            value={presetIdx}
            onChange={(e) => setPresetIdx(Number(e.target.value))}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            {WEATHER_LOCATION_PRESETS.map((p, idx) => (
              <option key={p.name} value={idx}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="wx-crop" className="block text-xs font-semibold text-soil-charcoal">
            Crop
          </label>
          <select
            id="wx-crop"
            value={cropType}
            onChange={(e) => setCropType(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            <option value="">Missing / Unknown</option>
            {YIELD_CROPS.slice(0, 20).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="wx-stage" className="block text-xs font-semibold text-soil-charcoal">
            Growth Stage (Kc Factor)
          </label>
          <select
            id="wx-stage"
            value={growthStage}
            onChange={(e) => setGrowthStage(e.target.value as StageOption)}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            <option value="initial">Initial Establishment</option>
            <option value="development">Vegetative Development</option>
            <option value="mid_season">Mid-Season Peak Demand</option>
            <option value="late_season">Late Ripening</option>
            <option value="unknown">Unknown / Not Assessed</option>
          </select>
        </div>

        <div>
          <label htmlFor="wx-soil" className="block text-xs font-semibold text-soil-charcoal">
            Soil Type
          </label>
          <select
            id="wx-soil"
            value={soilType}
            onChange={(e) => setSoilType(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            <option value="">Missing / Unknown</option>
            {SOIL_TYPES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="wx-irr" className="block text-xs font-semibold text-soil-charcoal">
            Irrigation System
          </label>
          <select
            id="wx-irr"
            value={irrigationType}
            onChange={(e) => setIrrigationType(e.target.value as IrrigationOption)}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            <option value="">Missing / Unknown</option>
            <option value="drip">Drip Irrigation</option>
            <option value="sprinkler">Sprinkler</option>
            <option value="canal">Canal / Surface</option>
            <option value="borewell">Borewell</option>
            <option value="mixed">Mixed</option>
            <option value="rainfed">Rainfed Only</option>
          </select>
        </div>

        <div>
          <label htmlFor="wx-moisture" className="block text-xs font-semibold text-soil-charcoal">
            Observed Soil Moisture % (Optional)
          </label>
          <input
            id="wx-moisture"
            type="number"
            min={0}
            max={100}
            step={0.5}
            placeholder="Not measured (leave blank)"
            value={soilMoisturePct}
            onChange={(e) => setSoilMoisturePct(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-2.5 text-sm font-semibold text-white hover:bg-forest-hover disabled:opacity-60"
          >
            <CloudRain className="h-4 w-4 text-gold-bright" />
            {loading ? 'Refreshing Forecast...' : 'Update Advisory'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={() => fetchForecast()} />
        </div>
      )}

      {loading && !data ? (
        <LoadingSkeleton rows={6} />
      ) : !data ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-950">
          <p className="font-bold">Live Weather Telemetry Unavailable</p>
          <p className="mt-1 text-xs">
            TerraQora AI never fabricates or substitutes stale historical numbers as live weather. Use the Retry button above once connectivity is restored.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-2 text-xs font-medium text-sky-900">
              <Info className="h-4 w-4 shrink-0 text-sky-700" />
              <span>{data.sensor_notice}</span>
            </div>
            <SourceModeBadge mode={data.source_mode} />
          </div>

          {/* Provider Attribution & Freshness Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-soil-border bg-white px-4 py-3 text-xs shadow-card">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-1.5 font-semibold text-forest-deep">
                <MapPin className="h-3.5 w-3.5 text-emerald-leaf" />
                {data.location_name} ({data.latitude.toFixed(2)}°, {data.longitude.toFixed(2)}°)
              </span>
              <span className="text-soil-muted">
                Provider: <strong className="text-soil-charcoal">{data.weather_provider}</strong>
              </span>
              {data.provider_attribution && (
                <span className="text-[11px] text-soil-muted">
                  ({data.provider_attribution})
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {data.observation_time && (
                <span className="inline-flex items-center gap-1 rounded-lg bg-parchment px-2.5 py-1 font-mono text-[11px] text-soil-charcoal border border-soil-border">
                  <Clock className="h-3 w-3 text-emerald-leaf" />
                  Observed {new Date(data.observation_time).toLocaleString()} (
                  {data.observation_age_minutes ?? 0}m ago)
                </span>
              )}
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase ${
                  data.freshness_status === 'delayed'
                    ? 'bg-amber-100 text-amber-900'
                    : data.freshness_status === 'cached'
                      ? 'bg-sky-100 text-sky-900'
                      : 'bg-emerald-mist text-emerald-leaf'
                }`}
              >
                {data.freshness_status || 'live'}
              </span>
            </div>
          </div>

          {/* Summary KPI Cards */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card">
              <div className="flex items-center justify-between text-xs font-semibold text-soil-muted">
                <span>Current Temperature</span>
                <Thermometer className="h-4 w-4 text-gold-harvest" />
              </div>
              <p className="mt-2 font-mono text-2xl font-bold text-forest-deep">
                {data.current_temp_c}°C
              </p>
              <p className="mt-1 text-xs text-soil-muted">{data.weather_condition}</p>
            </div>

            <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card">
              <div className="flex items-center justify-between text-xs font-semibold text-soil-muted">
                <span>Humidity & Wind</span>
                <Wind className="h-4 w-4 text-emerald-leaf" />
              </div>
              <p className="mt-2 font-mono text-2xl font-bold text-forest-deep">
                {data.current_humidity_pct}% RH
              </p>
              <p className="mt-1 text-xs text-soil-muted">{data.wind_speed_kmh} km/h wind</p>
            </div>

            <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card">
              <div className="flex items-center justify-between text-xs font-semibold text-soil-muted">
                <span>7-Day Rain Forecast</span>
                <CloudRain className="h-4 w-4 text-emerald-leaf" />
              </div>
              <p className="mt-2 font-mono text-2xl font-bold text-forest-deep">
                {data.forecast_rainfall_7d_mm} mm
              </p>
              <p className="mt-1 text-xs text-soil-muted">
                Mean ET₀: {data.estimated_et0_mm} mm/day
              </p>
            </div>

            <div
              className={`rounded-2xl border p-5 shadow-card ${
                data.recommended_water_mm === null
                  ? 'border-amber-300 bg-amber-50/70'
                  : 'border-emerald-border bg-emerald-mist/60'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-semibold text-forest-deep">
                <span>Net Irrigation Estimate</span>
                <Droplets className="h-4 w-4 text-emerald-leaf" />
              </div>
              <p className="mt-2 font-mono text-2xl font-bold text-forest-deep">
                {data.recommended_water_mm === null
                  ? 'Withheld'
                  : `${data.recommended_water_mm} mm`}
              </p>
              <p className="mt-1 text-xs font-semibold uppercase text-emerald-leaf">
                Urgency: {data.irrigation_urgency.replace(/_/g, ' ')}
              </p>
            </div>
          </div>

          {data.alerts.map((al) => (
            <div
              key={al.title}
              className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-gold-soft/70 p-4 text-xs text-amber-950"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-gold-harvest" />
              <div>
                <p className="font-bold">{al.title}</p>
                <p className="mt-0.5">{al.message}</p>
              </div>
            </div>
          ))}

          {/* Missing Inputs & Modeling Assumptions Transparency */}
          {((data.missing_inputs && data.missing_inputs.length > 0) ||
            (data.assumptions && data.assumptions.length > 0)) && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-amber-950">
                  <ShieldAlert className="h-4 w-4 text-amber-700" />
                  Missing / Unverified Field Inputs
                </div>
                {data.missing_inputs && data.missing_inputs.length > 0 ? (
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-amber-900">
                    {data.missing_inputs.map((m) => (
                      <li key={m}>{m.replace(/_/g, ' ')}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1.5 text-amber-900">
                    All required crop/soil/system parameters provided.
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-soil-border bg-white p-4 text-xs">
                <p className="font-bold text-forest-deep">
                  Agronomic Model Assumptions &amp; Units
                </p>
                {data.assumptions && data.assumptions.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-soil-charcoal">
                    {data.assumptions.map((a, idx) => (
                      <li key={idx}>{a}</li>
                    ))}
                  </ul>
                )}
                {data.units_summary && (
                  <p className="mt-2 font-mono text-[11px] text-soil-muted">
                    Units: Temp {data.units_summary.temperature} · Humidity{' '}
                    {data.units_summary.humidity} · Wind {data.units_summary.wind_speed} · Rain{' '}
                    {data.units_summary.precipitation} · ET₀ {data.units_summary.et0}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* 7-Day Forecast Chart + Daily Probability Table */}
          <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
            <h3 className="font-display text-base font-bold text-forest-deep">
              7-Day Rainfall vs. Max Temperature Forecast ({data.location_name})
            </h3>
            <p className="mt-1 text-xs text-soil-muted">{data.advisory_notes}</p>

            <div className="mt-4 h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.forecast_7d}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#5A665E' }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 12, fill: '#5A665E' }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12, fill: '#5A665E' }} />
                  <Tooltip />
                  <Bar
                    yAxisId="left"
                    dataKey="rain_mm"
                    name="Rain Forecast (mm)"
                    fill="#2D6A4F"
                    radius={[6, 6, 0, 0]}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="temp_max_c"
                    name="Max Temp (°C)"
                    stroke="#C9972C"
                    strokeWidth={2.5}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-soil-border text-soil-muted">
                    <th className="py-2 pr-3 font-semibold">Date</th>
                    <th className="py-2 pr-3 font-semibold">Max / Min</th>
                    <th className="py-2 pr-3 font-semibold">Humidity</th>
                    <th className="py-2 pr-3 font-semibold">Rain Prob</th>
                    <th className="py-2 pr-3 font-semibold">Rain (mm)</th>
                    <th className="py-2 font-semibold">ET₀ (mm/day)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-soil-border/60">
                  {data.forecast_7d.map((day) => (
                    <tr key={day.date}>
                      <td className="py-2 pr-3 font-mono font-medium text-forest-deep">
                        {day.date}
                      </td>
                      <td className="py-2 pr-3 font-mono">
                        {day.temp_max_c}°C / {day.temp_min_c}°C
                      </td>
                      <td className="py-2 pr-3 font-mono">{day.humidity_pct}%</td>
                      <td className="py-2 pr-3 font-mono">
                        {day.precipitation_probability_pct != null
                          ? `${day.precipitation_probability_pct}%`
                          : '—'}
                      </td>
                      <td className="py-2 pr-3 font-mono">{day.rain_mm} mm</td>
                      <td className="py-2 font-mono">{day.et0_mm}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {history.length > 0 && (
            <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-emerald-leaf" />
                <h3 className="font-display text-sm font-bold text-forest-deep">
                  Recent Saved Irrigation Advisories
                </h3>
              </div>
              <div className="mt-3 space-y-2">
                {history.slice(0, 5).map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-soil-border bg-parchment/50 px-3.5 py-2.5 text-xs"
                  >
                    <div>
                      <span className="font-semibold text-forest-deep">
                        {item.location_name}
                      </span>{' '}
                      · <span className="text-soil-muted">{item.crop_type}</span>
                    </div>
                    <div className="flex items-center gap-3 font-mono text-[11px]">
                      <span>
                        {item.recommended_water_mm === null
                          ? 'Withheld'
                          : `${item.recommended_water_mm} mm`}
                      </span>
                      <span className="rounded-md bg-white px-2 py-0.5 border border-soil-border uppercase text-emerald-leaf">
                        {item.irrigation_urgency.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
