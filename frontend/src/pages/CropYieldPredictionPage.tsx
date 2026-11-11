import React, { useEffect, useState } from 'react';
import { History, Info, ShieldCheck, Sprout, TrendingUp } from 'lucide-react';
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
import { mlService, profileService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { CROP_SEASONS, INDIAN_STATES, YIELD_CROPS } from '../data/agriCatalog';
import { useToast } from '../context/ToastContext';
import type { CropYieldResponse, Farm } from '../types/api';

export function CropYieldPredictionPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string>('');
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
  const [history, setHistory] = useState<CropYieldResponse[]>([]);
  const { notify } = useToast();

  useEffect(() => {
    let active = true;
    async function loadInitialContext() {
      try {
        const [farmList, predHistory] = await Promise.all([
          profileService.listFarms(),
          mlService.getYieldHistory(),
        ]);
        if (!active) return;
        setFarms(farmList);
        setHistory(predHistory);
      } catch {
        // Non-blocking: prediction form remains usable even if history/farms fail to load
      }
    }
    loadInitialContext();
    return () => {
      active = false;
    };
  }, []);

  const handleFarmChange = (farmId: string) => {
    setSelectedFarmId(farmId);
    if (!farmId) return;
    const farm = farms.find((f) => f.id === farmId);
    if (!farm) return;

    const matchedState = INDIAN_STATES.find(
      (s) => s.toLowerCase() === farm.state.trim().toLowerCase()
    );
    if (matchedState) {
      setState(matchedState);
    }
    setArea(farm.area_hectares);

    if (farm.primary_crop) {
      const matchedCrop = YIELD_CROPS.find(
        (c) =>
          c.replace(/\s+/g, ' ').toLowerCase() ===
          farm.primary_crop!.trim().replace(/\s+/g, ' ').toLowerCase()
      );
      if (matchedCrop) {
        setCrop(matchedCrop);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!Number.isFinite(cropYear) || cropYear < 1990 || cropYear > 2100) {
      setError('Target year must be between 1990 and 2100.');
      return;
    }
    if (!Number.isFinite(area) || area <= 0 || area > 1000000) {
      setError('Area must be greater than 0 and up to 1,000,000 hectares.');
      return;
    }
    if (
      !Number.isFinite(rainfall) ||
      !Number.isFinite(fertilizer) ||
      !Number.isFinite(pesticide) ||
      rainfall < 0 ||
      fertilizer < 0 ||
      pesticide < 0
    ) {
      setError('Rainfall, fertilizer, and pesticide values must be non-negative finite numbers.');
      return;
    }

    setLoading(true);
    try {
      const prediction = await mlService.predictYield({
        farm_id: selectedFarmId || undefined,
        crop,
        crop_year: Math.round(cropYear),
        season,
        state,
        area_hectares: area,
        annual_rainfall_mm: rainfall,
        fertilizer_kg: fertilizer,
        pesticide_kg: pesticide,
      });
      setResult(prediction);
      setHistory((prev) =>
        [prediction, ...prev.filter((item) => item.id !== prediction.id)].slice(0, 10)
      );
      notify(`Yield forecast computed for ${prediction.crop} (${prediction.state})`, 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed.');
    } finally {
      setLoading(false);
    }
  };

  const fertilizerPerHa = area > 0 && Number.isFinite(area) ? fertilizer / area : 0;
  const pesticidePerHa = area > 0 && Number.isFinite(area) ? pesticide / area : 0;

  return (
    <AppShell
      title="AI Crop Yield Prediction"
      subtitle="Leak-free pre-harvest yield estimation trained on scale-invariant agronomic intensities."
    >
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-emerald-border bg-emerald-mist/60 px-4 py-3 text-xs text-forest-deep">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-leaf" />
        <p>
          <strong>Model Integrity Enforced:</strong> Post-harvest <code>Production</code> is
          intentionally excluded as an input feature to eliminate target leakage. Coconut yields
          are modeled separately in <strong>nuts/hectare</strong>; all other 54 crops are modeled in{' '}
          <strong>tonnes/hectare</strong>.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Form Panel */}
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <div className="flex items-center justify-between">
            <h2 className="font-display text-base font-bold text-forest-deep">
              Field & Seasonal Parameters
            </h2>
            <Sprout className="h-4 w-4 text-emerald-leaf" />
          </div>

          {error && <ErrorAlert message={error} />}

          <div>
            <label htmlFor="yield-farm" className="block text-xs font-semibold text-soil-charcoal">
              Link Saved Farm Plot (Optional)
            </label>
            <select
              id="yield-farm"
              value={selectedFarmId}
              onChange={(e) => handleFarmChange(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
            >
              <option value="">Custom / Unlinked Plot</option>
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name} ({farm.state} · {farm.area_hectares} ha)
                </option>
              ))}
            </select>
          </div>

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
                min={1990}
                max={2100}
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

          <div className="rounded-xl border border-soil-border bg-parchment/70 px-3.5 py-2.5 text-xs text-soil-muted">
            Computed agronomic rates:{' '}
            <strong className="font-mono text-soil-charcoal">
              {fertilizerPerHa.toFixed(1)} kg/ha
            </strong>{' '}
            fertilizer ·{' '}
            <strong className="font-mono text-soil-charcoal">
              {pesticidePerHa.toFixed(2)} kg/ha
            </strong>{' '}
            pesticide
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
              description="Select your crop, state, season, and input quantities on the left to inspect predicted yield per hectare and SHAP feature drivers."
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
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                    Feature Driver Attribution (%)
                  </h4>
                  <div className="flex items-center gap-3 text-[11px] text-soil-muted">
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-sm bg-emerald-leaf" />
                      Positive Push
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-sm bg-gold-harvest" />
                      Downward Push
                    </span>
                  </div>
                </div>
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
                        width={175}
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
                  <p className="mt-0.5 leading-relaxed">{result.advisory_note}</p>
                </div>
              </div>
            </div>
          )}

          {history.length > 0 && (
            <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card">
              <div className="flex items-center justify-between border-b border-soil-border pb-3">
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4 text-forest-deep" />
                  <h3 className="font-display text-sm font-bold text-forest-deep">
                    Recent Yield Forecasts
                  </h3>
                </div>
                <span className="text-xs text-soil-muted">{history.length} saved</span>
              </div>
              <ul className="mt-3 divide-y divide-soil-border">
                {history.slice(0, 5).map((item) => (
                  <li key={item.id} className="py-2.5">
                    <button
                      type="button"
                      onClick={() => setResult(item)}
                      className="flex w-full flex-wrap items-center justify-between gap-2 rounded-lg px-2 py-1 text-left transition-colors hover:bg-parchment"
                    >
                      <div>
                        <p className="text-xs font-semibold text-forest-deep">
                          {item.crop} · {item.state} ({item.season}, {item.crop_year})
                        </p>
                        <p className="text-[11px] text-soil-muted">
                          {item.area_hectares} ha · Est.{' '}
                          {item.estimated_total_production.toLocaleString()} {item.production_unit}
                        </p>
                      </div>
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-sm font-bold text-emerald-leaf">
                          {item.predicted_yield} {item.yield_unit}
                        </span>
                        <SourceModeBadge mode={item.source_mode} />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
