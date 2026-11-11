import React, { useState } from 'react';
import { Info, ShieldCheck, TrendingUp } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
import { CROP_SEASONS, INDIAN_STATES, YIELD_CROPS } from '../data/agriCatalog';
import { useToast } from '../context/ToastContext';
import type { CropYieldResponse } from '../types/api';

export function CropYieldPredictionPage() {
  const [crop, setCrop] = useState<string>('Rice');
  const [state, setState] = useState<string>('Tamil Nadu');
  const [season, setSeason] = useState<string>('Kharif');
  const [cropYear, setCropYear] = useState<number>(2025);
  const [area, setArea] = useState<number>(5.0);
  const [rainfall, setRainfall] = useState<number>(1150);
  const [fertilizer, setFertilizer] = useState<number>(650);
  const [pesticide, setPesticide] = useState<number>(18);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CropYieldResponse | null>(null);
  const { notify } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (area <= 0 || area > 1000000) {
      setError('Area must be greater than 0 and up to 1,000,000 hectares.');
      return;
    }
    if (rainfall < 0 || fertilizer < 0 || pesticide < 0) {
      setError('Rainfall, fertilizer, and pesticide values cannot be negative.');
      return;
    }

    setLoading(true);
    try {
      const prediction = await mlService.predictYield({
        crop,
        crop_year: cropYear,
        season,
        state,
        area_hectares: area,
        annual_rainfall_mm: rainfall,
        fertilizer_kg: fertilizer,
        pesticide_kg: pesticide,
      });
      setResult(prediction);
      notify(`Yield forecast computed for ${crop} (${state})`, 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      title="AI Crop Yield Prediction"
      subtitle="Leak-free pre-harvest yield estimation powered by agricultural inputs and historical regional baselines."
    >
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-emerald-border bg-emerald-mist/60 px-4 py-3 text-xs text-forest-deep">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-leaf" />
        <p>
          <strong>Model Integrity Enforced:</strong> Post-harvest <code>Production</code> is
          intentionally excluded as an input feature to eliminate target leakage. Coconut yields
          are reported in <strong>nuts/hectare</strong>; all other crops are reported in{' '}
          <strong>tonnes/hectare</strong>.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Form Panel */}
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <h2 className="font-display text-base font-bold text-forest-deep">
            Field & Seasonal Parameters
          </h2>

          {error && <ErrorAlert message={error} />}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="yield-crop" className="block text-xs font-semibold text-soil-charcoal">
                Crop (55 Dataset Crops)
              </label>
              <select
                id="yield-crop"
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              >
                {YIELD_CROPS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="yield-state" className="block text-xs font-semibold text-soil-charcoal">
                State (30 Regions)
              </label>
              <select
                id="yield-state"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              >
                {INDIAN_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="yield-season" className="block text-xs font-semibold text-soil-charcoal">
                Cropping Season
              </label>
              <select
                id="yield-season"
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              >
                {CROP_SEASONS.map((se) => (
                  <option key={se} value={se}>
                    {se}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="yield-year" className="block text-xs font-semibold text-soil-charcoal">
                Target Year
              </label>
              <input
                id="yield-year"
                type="number"
                min={1997}
                max={2035}
                value={cropYear}
                onChange={(e) => setCropYear(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="yield-area" className="block text-xs font-semibold text-soil-charcoal">
                Cultivated Area (ha)
              </label>
              <input
                id="yield-area"
                type="number"
                min={0.1}
                step={0.1}
                value={area}
                onChange={(e) => setArea(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="yield-rain" className="block text-xs font-semibold text-soil-charcoal">
                Annual Rainfall (mm)
              </label>
              <input
                id="yield-rain"
                type="number"
                min={0}
                step={10}
                value={rainfall}
                onChange={(e) => setRainfall(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="yield-fert" className="block text-xs font-semibold text-soil-charcoal">
                Total Fertilizer (kg)
              </label>
              <input
                id="yield-fert"
                type="number"
                min={0}
                step={10}
                value={fertilizer}
                onChange={(e) => setFertilizer(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="yield-pest" className="block text-xs font-semibold text-soil-charcoal">
                Total Pesticide (kg)
              </label>
              <input
                id="yield-pest"
                type="number"
                min={0}
                step={1}
                value={pesticide}
                onChange={(e) => setPesticide(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-3 text-sm font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-60"
          >
            <TrendingUp className="h-4 w-4 text-gold-bright" />
            {loading ? 'Running Yield Pipeline...' : 'Predict Crop Yield'}
          </button>
        </form>

        {/* Results Panel */}
        <div className="space-y-6 lg:col-span-7">
          {loading ? (
            <LoadingSkeleton rows={6} />
          ) : !result ? (
            <EmptyState
              title="Ready to forecast acreage yield"
              description="Select your crop, state, season, and input quantities on the left to inspect predicted yield per hectare and feature drivers."
            />
          ) : (
            <div className="space-y-5 rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-soil-border pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                    Prediction Output
                  </p>
                  <h3 className="font-display text-lg font-bold text-forest-deep">
                    {result.crop} · {result.state} ({result.season})
                  </h3>
                </div>
                <SourceModeBadge mode={result.source_mode} />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-emerald-border bg-emerald-mist/60 p-5">
                  <p className="text-xs font-semibold text-emerald-leaf">Predicted Unit Yield</p>
                  <p className="mt-1 font-mono text-3xl font-bold text-forest-deep tabular-nums">
                    {result.predicted_yield}{' '}
                    <span className="text-sm font-semibold text-soil-muted">
                      {result.yield_unit}
                    </span>
                  </p>
                </div>

                <div className="rounded-2xl border border-soil-border bg-parchment p-5">
                  <p className="text-xs font-semibold text-soil-muted">
                    Estimated Total Harvest ({result.area_hectares} ha)
                  </p>
                  <p className="mt-1 font-mono text-3xl font-bold text-gold-harvest tabular-nums">
                    {result.estimated_total_production.toLocaleString()}{' '}
                    <span className="text-sm font-semibold text-soil-muted">
                      {result.production_unit}
                    </span>
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                  Feature Driver Attribution (%)
                </h4>
                <div className="mt-3 h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={result.feature_drivers}
                      layout="vertical"
                      margin={{ left: 20, right: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                      <XAxis type="number" unit="%" tick={{ fontSize: 11, fill: '#5A665E' }} />
                      <YAxis
                        type="category"
                        dataKey="feature"
                        width={165}
                        tick={{ fontSize: 11, fill: '#1B241E' }}
                      />
                      <Tooltip />
                      <Bar dataKey="impact_pct" name="Contribution %" radius={[0, 6, 6, 0]}>
                        {result.feature_drivers.map((entry, idx) => (
                          <Cell
                            key={entry.feature}
                            fill={
                              entry.direction === 'negative'
                                ? '#C9972C'
                                : idx === 0
                                  ? '#123524'
                                  : '#2D6A4F'
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="flex items-start gap-2.5 rounded-xl border border-soil-border bg-parchment p-3.5 text-xs text-soil-muted">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-forest-deep" />
                <div>
                  <p className="font-semibold text-soil-charcoal">
                    {result.model_name} ({result.model_version})
                  </p>
                  <p className="mt-0.5">{result.advisory_note}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
