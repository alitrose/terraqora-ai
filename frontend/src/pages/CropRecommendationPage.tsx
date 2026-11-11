import React, { useEffect, useState } from 'react';
import { History, ShieldCheck, Sprout } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
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
import { CROP_SEASONS, INDIAN_STATES } from '../data/agriCatalog';
import { useToast } from '../context/ToastContext';
import type { CropRecommendationResponse, Farm } from '../types/api';

export function CropRecommendationPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string>('');
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
  const [history, setHistory] = useState<CropRecommendationResponse[]>([]);
  const { notify } = useToast();

  useEffect(() => {
    let active = true;
    async function loadInitialContext() {
      try {
        const [farmList, recHistory] = await Promise.all([
          profileService.listFarms(),
          mlService.getCropRecHistory(),
        ]);
        if (!active) return;
        setFarms(farmList);
        setHistory(recHistory);
      } catch {
        // Non-blocking: recommendation form remains usable even if history/farms fail to load
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

    if (farm.soil_ph !== null && Number.isFinite(farm.soil_ph)) {
      setPh(farm.soil_ph);
    }
    const matchedState = INDIAN_STATES.find(
      (s) => s.toLowerCase() === farm.state.trim().toLowerCase()
    );
    if (matchedState) {
      setRegion(matchedState);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (
      !Number.isFinite(nitrogen) ||
      !Number.isFinite(phosphorus) ||
      !Number.isFinite(potassium) ||
      nitrogen < 0 ||
      nitrogen > 500 ||
      phosphorus < 0 ||
      phosphorus > 500 ||
      potassium < 0 ||
      potassium > 500
    ) {
      setError('NPK values must be finite numbers between 0 and 500.');
      return;
    }
    if (!Number.isFinite(ph) || ph < 0 || ph > 14) {
      setError('Soil pH must be between 0.0 and 14.0.');
      return;
    }
    if (!Number.isFinite(humidity) || humidity < 0 || humidity > 100) {
      setError('Humidity must be between 0% and 100%.');
      return;
    }
    if (!Number.isFinite(temperature) || temperature < -10 || temperature > 60) {
      setError('Temperature must be between -10°C and 60°C.');
      return;
    }
    if (!Number.isFinite(rainfall) || rainfall < 0 || rainfall > 5000) {
      setError('Rainfall must be between 0 and 5,000 mm.');
      return;
    }

    setLoading(true);
    try {
      const res = await mlService.recommendCrop({
        farm_id: selectedFarmId || undefined,
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
      setHistory((prev) => [res, ...prev.filter((item) => item.id !== res.id)].slice(0, 10));
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
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-emerald-border bg-emerald-mist/60 px-4 py-3 text-xs text-forest-deep">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-leaf" />
        <p>
          <strong>Dataset Feature Scope:</strong> Crop probabilities are ranked strictly from the
          7 validated soil & climate measurements (<code>N, P, K, temperature, humidity, pH, rainfall</code>)
          in <code>Crop_recommendation.csv</code> (22 crops). Season and Region are captured as
          plot context without altering model scores.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <h2 className="font-display text-base font-bold text-forest-deep">
            Soil & Climate Profile
          </h2>

          {error && <ErrorAlert message={error} />}

          <div>
            <label htmlFor="cr-farm" className="block text-xs font-semibold text-soil-charcoal">
              Link Saved Farm Plot (Optional)
            </label>
            <select
              id="cr-farm"
              value={selectedFarmId}
              onChange={(e) => handleFarmChange(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
            >
              <option value="">Custom / Unlinked Plot</option>
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name} ({farm.state}
                  {farm.soil_ph !== null ? ` · pH ${farm.soil_ph}` : ''})
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="cr-n" className="block text-xs font-semibold text-soil-charcoal">
                Nitrogen (N)
              </label>
              <input
                id="cr-n"
                type="number"
                min={0}
                max={500}
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
                max={500}
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
                max={500}
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
                min={-10}
                max={60}
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
                max={5000}
                value={rainfall}
                onChange={(e) => setRainfall(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="cr-season" className="block text-xs font-semibold text-soil-charcoal">
                Season (Context)
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
              Region / State (Context)
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
                  <p className="mt-0.5 text-[11px] font-mono text-soil-muted">
                    Gaussian Naive Bayes · {result.model_version}
                  </p>
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

              <p className="text-xs leading-relaxed text-soil-muted">
                {result.soil_climate_summary}
              </p>
            </div>
          )}

          {history.length > 0 && (
            <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card">
              <div className="flex items-center justify-between border-b border-soil-border pb-3">
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4 text-forest-deep" />
                  <h3 className="font-display text-sm font-bold text-forest-deep">
                    Recent Crop Suitability Matches
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
                        <p className="text-xs font-semibold capitalize text-forest-deep">
                          {item.recommended_crop}
                          {item.region ? ` · ${item.region}` : ''}
                          {item.season ? ` (${item.season})` : ''}
                        </p>
                        <p className="text-[11px] font-mono text-soil-muted">
                          {item.soil_ph !== undefined
                            ? `NPK ${item.nitrogen}-${item.phosphorus}-${item.potassium} · pH ${item.soil_ph.toFixed(1)} · ${item.rainfall_mm} mm`
                            : item.soil_climate_summary.slice(0, 64)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2.5">
                        {item.top_candidates[0] && (
                          <span className="font-mono text-sm font-bold text-emerald-leaf">
                            {(item.top_candidates[0].probability * 100).toFixed(0)}%
                          </span>
                        )}
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
