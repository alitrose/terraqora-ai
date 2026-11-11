import React, { useState } from 'react';
import { Sprout } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { mlService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { CROP_SEASONS, INDIAN_STATES } from '../data/agriCatalog';
import { useToast } from '../context/ToastContext';
import type { CropRecommendationResponse } from '../types/api';

export function CropRecommendationPage() {
  const [nitrogen, setNitrogen] = useState(85);
  const [phosphorus, setPhosphorus] = useState(50);
  const [potassium, setPotassium] = useState(42);
  const [temperature, setTemperature] = useState(24.5);
  const [humidity, setHumidity] = useState(80);
  const [ph, setPh] = useState(6.6);
  const [rainfall, setRainfall] = useState(210);
  const [season, setSeason] = useState<string>('Kharif');
  const [region, setRegion] = useState<string>('Tamil Nadu');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CropRecommendationResponse | null>(null);
  const { notify } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (ph < 0 || ph > 14 || humidity < 0 || humidity > 100) {
      setError('Soil pH must be 0–14 and humidity must be 0–100%.');
      return;
    }

    setLoading(true);
    try {
      const res = await mlService.recommendCrop({
        nitrogen,
        phosphorus,
        potassium,
        temperature_c: temperature,
        humidity_pct: humidity,
        soil_ph: ph,
        rainfall_mm: rainfall,
        season,
        region,
      });
      setResult(res);
      notify(`Top crop match: ${res.recommended_crop}`, 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recommendation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      title="Crop Recommendation"
      subtitle="Soil nutrient & climate compatibility ranking across 22 curated crops."
    >
      <div className="grid gap-6 lg:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <h2 className="font-display text-base font-bold text-forest-deep">
            Soil & Climate Profile
          </h2>

          {error && <ErrorAlert message={error} />}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="cr-n" className="block text-xs font-semibold text-soil-charcoal">
                Nitrogen (N)
              </label>
              <input
                id="cr-n"
                type="number"
                min={0}
                value={nitrogen}
                onChange={(e) => setNitrogen(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-p" className="block text-xs font-semibold text-soil-charcoal">
                Phosphorus (P)
              </label>
              <input
                id="cr-p"
                type="number"
                min={0}
                value={phosphorus}
                onChange={(e) => setPhosphorus(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-k" className="block text-xs font-semibold text-soil-charcoal">
                Potassium (K)
              </label>
              <input
                id="cr-k"
                type="number"
                min={0}
                value={potassium}
                onChange={(e) => setPotassium(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-ph" className="block text-xs font-semibold text-soil-charcoal">
                Soil pH
              </label>
              <input
                id="cr-ph"
                type="number"
                min={0}
                max={14}
                step={0.1}
                value={ph}
                onChange={(e) => setPh(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-temp" className="block text-xs font-semibold text-soil-charcoal">
                Temperature (°C)
              </label>
              <input
                id="cr-temp"
                type="number"
                step={0.5}
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-hum" className="block text-xs font-semibold text-soil-charcoal">
                Humidity (%)
              </label>
              <input
                id="cr-hum"
                type="number"
                min={0}
                max={100}
                value={humidity}
                onChange={(e) => setHumidity(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-rain" className="block text-xs font-semibold text-soil-charcoal">
                Seasonal Rainfall (mm)
              </label>
              <input
                id="cr-rain"
                type="number"
                min={0}
                value={rainfall}
                onChange={(e) => setRainfall(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-season" className="block text-xs font-semibold text-soil-charcoal">
                Season
              </label>
              <select
                id="cr-season"
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                {CROP_SEASONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="cr-region" className="block text-xs font-semibold text-soil-charcoal">
              Region / State
            </label>
            <select
              id="cr-region"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
            >
              {INDIAN_STATES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-3 text-sm font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-60"
          >
            <Sprout className="h-4 w-4 text-gold-bright" />
            {loading ? 'Matching Crop Profiles...' : 'Find Best Suitable Crops'}
          </button>
        </form>

        <div className="space-y-6 lg:col-span-7">
          {loading ? (
            <LoadingSkeleton rows={6} />
          ) : !result ? (
            <EmptyState
              title="Ready for crop suitability matching"
              description="Submit soil nutrients, temperature, humidity, pH, and seasonal rainfall to inspect the top 3 crop candidates."
            />
          ) : (
            <div className="space-y-5 rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-soil-border pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                    Primary Crop Match
                  </p>
                  <h3 className="font-display text-2xl font-bold capitalize text-forest-deep">
                    {result.recommended_crop}
                  </h3>
                </div>
                <SourceModeBadge mode={result.source_mode} />
              </div>

              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={result.top_candidates.map((c) => ({
                      crop: c.crop.toUpperCase(),
                      score: Math.round(c.probability * 100),
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                    <XAxis dataKey="crop" tick={{ fontSize: 12, fill: '#1B241E' }} />
                    <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 12, fill: '#5A665E' }} />
                    <Tooltip />
                    <Bar dataKey="score" name="Suitability Score %" fill="#2D6A4F" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-3">
                {result.top_candidates.map((cand, index) => (
                  <div
                    key={cand.crop}
                    className={`rounded-xl border p-4 ${
                      index === 0
                        ? 'border-emerald-border bg-emerald-mist/60'
                        : 'border-soil-border bg-parchment/60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-display text-base font-bold capitalize text-forest-deep">
                        #{index + 1} {cand.crop}
                      </p>
                      <span className="font-mono text-sm font-bold text-emerald-leaf">
                        {(cand.probability * 100).toFixed(0)}% match
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-soil-muted">{cand.fit_reason}</p>
                  </div>
                ))}
              </div>

              <p className="text-xs text-soil-muted">{result.soil_climate_summary}</p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
