import React, { useEffect, useState } from 'react';
import { AlertTriangle, CloudRain, Droplets, Info, Thermometer, Wind } from 'lucide-react';
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
import { weatherService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { WEATHER_LOCATION_PRESETS, YIELD_CROPS } from '../data/agriCatalog';
import type { WeatherIrrigationResponse } from '../types/api';

export function WeatherIrrigationPage() {
  const [presetIdx, setPresetIdx] = useState(0);
  const [cropType, setCropType] = useState('Rice');
  const [growthStage, setGrowthStage] = useState<
    'initial' | 'development' | 'mid_season' | 'late_season'
  >('mid_season');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WeatherIrrigationResponse | null>(null);

  const fetchForecast = async (
    idx = presetIdx,
    crop = cropType,
    stage = growthStage
  ) => {
    const loc = WEATHER_LOCATION_PRESETS[idx];
    setLoading(true);
    setError(null);
    try {
      const res = await weatherService.getIrrigationAdvisory({
        location_name: loc.name,
        latitude: loc.lat,
        longitude: loc.lon,
        crop_type: crop,
        growth_stage: stage,
      });
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to fetch weather forecast.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchForecast(presetIdx, cropType, growthStage);
  };

  return (
    <AppShell
      title="Weather & Irrigation Intelligence"
      subtitle="7-day rainfall forecast, evapotranspiration (ET₀) modeling, and crop-stage irrigation timing."
    >
      <form
        onSubmit={handleSubmit}
        className="mb-6 grid gap-4 rounded-2xl border border-soil-border bg-white p-5 shadow-card sm:grid-cols-2 lg:grid-cols-4"
      >
        <div>
          <label htmlFor="wx-loc" className="block text-xs font-semibold text-soil-charcoal">
            Agricultural Station
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
            onChange={(e) =>
              setGrowthStage(
                e.target.value as 'initial' | 'development' | 'mid_season' | 'late_season'
              )
            }
            className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
          >
            <option value="initial">Initial Establishment</option>
            <option value="development">Vegetative Development</option>
            <option value="mid_season">Mid-Season Peak Demand</option>
            <option value="late_season">Late Ripening</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-2.5 text-sm font-semibold text-white hover:bg-forest-hover disabled:opacity-60"
          >
            <CloudRain className="h-4 w-4 text-gold-bright" />
            Update Advisory
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={() => fetchForecast()} />
        </div>
      )}

      {loading || !data ? (
        <LoadingSkeleton rows={6} />
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-2 text-xs font-medium text-sky-900">
              <Info className="h-4 w-4 shrink-0 text-sky-700" />
              <span>{data.sensor_notice}</span>
            </div>
            <SourceModeBadge mode={data.source_mode} />
          </div>

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

            <div className="rounded-2xl border border-emerald-border bg-emerald-mist/60 p-5 shadow-card">
              <div className="flex items-center justify-between text-xs font-semibold text-forest-deep">
                <span>Net Irrigation Estimate</span>
                <Droplets className="h-4 w-4 text-emerald-leaf" />
              </div>
              <p className="mt-2 font-mono text-2xl font-bold text-forest-deep">
                {data.recommended_water_mm} mm
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
          </div>
        </div>
      )}
    </AppShell>
  );
}
