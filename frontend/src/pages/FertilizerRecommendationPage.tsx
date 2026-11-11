import React, { useEffect, useState } from 'react';
import { AlertCircle, FlaskConical, History, Info, ShieldCheck } from 'lucide-react';
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
import { INDIAN_STATES, SOIL_TYPES, YIELD_CROPS } from '../data/agriCatalog';
import { useToast } from '../context/ToastContext';
import type { Farm, FertilizerResponse } from '../types/api';

function matchSoilOption(farmSoil: string | null): string | null {
  if (!farmSoil) return null;
  const cleaned = farmSoil.trim().toLowerCase();
  const exact = SOIL_TYPES.find((s) => s.toLowerCase() === cleaned);
  if (exact) return exact;
  if (cleaned.includes('black') || cleaned.includes('regur')) return 'Black (Regur)';
  if (cleaned.includes('alluvial')) return 'Alluvial';
  if (cleaned.includes('red')) return 'Red Loamy';
  if (cleaned.includes('laterite')) return 'Laterite';
  if (cleaned.includes('sandy')) return 'Sandy Loam';
  if (cleaned.includes('clay')) return 'Clay Loam';
  return null;
}

export function FertilizerRecommendationPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string>('');
  const [nitrogen, setNitrogen] = useState(35);
  const [phosphorus, setPhosphorus] = useState(25);
  const [potassium, setPotassium] = useState(42);
  const [soilPh, setSoilPh] = useState(6.5);
  const [soilType, setSoilType] = useState<string>(SOIL_TYPES[0]);
  const [cropType, setCropType] = useState<string>('Rice');
  const [location, setLocation] = useState<string>('Tamil Nadu');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FertilizerResponse | null>(null);
  const [history, setHistory] = useState<FertilizerResponse[]>([]);
  const { notify } = useToast();

  useEffect(() => {
    let active = true;
    async function loadInitialContext() {
      try {
        const [farmList, fertHistory] = await Promise.all([
          profileService.listFarms(),
          mlService.getFertilizerHistory(),
        ]);
        if (!active) return;
        setFarms(farmList);
        setHistory(fertHistory);
      } catch {
        // Non-blocking: fertilizer form stays usable even if history/farms fail to load
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
      setSoilPh(farm.soil_ph);
    }
    const matchedSoil = matchSoilOption(farm.soil_type);
    if (matchedSoil) {
      setSoilType(matchedSoil);
    }
    const matchedState = INDIAN_STATES.find(
      (s) => s.toLowerCase() === farm.state.trim().toLowerCase()
    );
    if (matchedState) {
      setLocation(matchedState);
    }
    if (farm.primary_crop) {
      const matchedCrop = YIELD_CROPS.find(
        (c) =>
          c.replace(/\s+/g, ' ').toLowerCase() ===
          farm.primary_crop!.trim().replace(/\s+/g, ' ').toLowerCase()
      );
      if (matchedCrop) {
        setCropType(matchedCrop);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!Number.isFinite(soilPh) || soilPh < 0 || soilPh > 14) {
      setError('Soil pH must be between 0.0 and 14.0.');
      return;
    }
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
      setError('NPK nutrient readings must be finite numbers between 0 and 500.');
      return;
    }

    setLoading(true);
    try {
      const res = await mlService.recommendFertilizer({
        farm_id: selectedFarmId || undefined,
        nitrogen,
        phosphorus,
        potassium,
        soil_ph: soilPh,
        soil_type: soilType,
        crop_type: cropType,
        location,
      });
      setResult(res);
      setHistory((prev) => [res, ...prev.filter((item) => item.id !== res.id)].slice(0, 10));
      notify(`Fertilizer guidance ready for ${cropType}`, 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate recommendation.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      title="Smart Fertilizer Recommendation"
      subtitle="Data-grounded formulation classification paired with conservative ICAR nutrient & pH guardrails."
    >
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-emerald-border bg-emerald-mist/60 px-4 py-3 text-xs text-forest-deep">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-leaf" />
        <p>
          <strong>Zero Fabricated Dosages Policy:</strong> Trained ML classification selects
          among the 7 dataset fertilizer formulations only when ICAR soil-test screening detects a
          macronutrient deficiency. Sufficient soils trigger organic maintenance rules, and exact{' '}
          <code>kg/ha</code> application rates are intentionally omitted pending KVK lab testing.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <h2 className="font-display text-base font-bold text-forest-deep">
            Soil Nutrient & Plot Inputs
          </h2>

          {error && <ErrorAlert message={error} />}

          <div>
            <label htmlFor="fert-farm" className="block text-xs font-semibold text-soil-charcoal">
              Link Saved Farm Plot (Optional)
            </label>
            <select
              id="fert-farm"
              value={selectedFarmId}
              onChange={(e) => handleFarmChange(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
            >
              <option value="">Custom / Unlinked Plot</option>
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name} ({farm.state}
                  {farm.soil_type ? ` · ${farm.soil_type}` : ''})
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="fert-n" className="block text-xs font-semibold text-soil-charcoal">
                Nitrogen (N, kg/ha)
              </label>
              <input
                id="fert-n"
                type="number"
                min={0}
                max={500}
                value={nitrogen}
                onChange={(e) => setNitrogen(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="fert-p" className="block text-xs font-semibold text-soil-charcoal">
                Phosphorus (P, kg/ha)
              </label>
              <input
                id="fert-p"
                type="number"
                min={0}
                max={500}
                value={phosphorus}
                onChange={(e) => setPhosphorus(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="fert-k" className="block text-xs font-semibold text-soil-charcoal">
                Potassium (K, kg/ha)
              </label>
              <input
                id="fert-k"
                type="number"
                min={0}
                max={500}
                value={potassium}
                onChange={(e) => setPotassium(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="fert-ph" className="block text-xs font-semibold text-soil-charcoal">
                Soil pH (0–14)
              </label>
              <input
                id="fert-ph"
                type="number"
                min={0}
                max={14}
                step={0.1}
                value={soilPh}
                onChange={(e) => setSoilPh(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="fert-soil" className="block text-xs font-semibold text-soil-charcoal">
                Soil Type
              </label>
              <select
                id="fert-soil"
                value={soilType}
                onChange={(e) => setSoilType(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              >
                {SOIL_TYPES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="fert-crop" className="block text-xs font-semibold text-soil-charcoal">
                Target Crop
              </label>
              <select
                id="fert-crop"
                value={cropType}
                onChange={(e) => setCropType(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              >
                {YIELD_CROPS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="fert-loc" className="block text-xs font-semibold text-soil-charcoal">
              Location / State
            </label>
            <select
              id="fert-loc"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
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
            <FlaskConical className="h-4 w-4 text-gold-bright" />
            {loading ? 'Evaluating Soil Balance...' : 'Recommend Fertilizer'}
          </button>
        </form>

        <div className="space-y-6 lg:col-span-7">
          {loading ? (
            <LoadingSkeleton rows={6} />
          ) : !result ? (
            <EmptyState
              title="Enter soil test readings"
              description="Provide soil Nitrogen, Phosphorus, Potassium, pH, soil texture, and target crop to receive a structured nutrient plan."
            />
          ) : (
            <div className="space-y-5 rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex flex-wrap items-start justify-between gap-2 border-b border-soil-border pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                    Recommended Formulation
                  </p>
                  <h3 className="font-display text-xl font-bold text-forest-deep">
                    {result.recommended_fertilizer}
                  </h3>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                        result.recommendation_mode === 'agronomic_sufficiency_guardrail'
                          ? 'bg-emerald-mist text-emerald-leaf'
                          : 'bg-gold-soft text-amber-900'
                      }`}
                    >
                      {result.recommendation_mode === 'agronomic_sufficiency_guardrail'
                        ? 'ICAR Sufficiency Guardrail Active'
                        : `ML Grade Classifier (${Math.round(result.confidence * 100)}% confidence)`}
                    </span>
                    <span className="font-mono text-[11px] text-soil-muted">
                      {result.model_version}
                    </span>
                  </div>
                </div>
                <SourceModeBadge mode={result.source_mode} />
              </div>

              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.nutrient_levels}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                    <XAxis dataKey="nutrient" tick={{ fontSize: 12, fill: '#1B241E' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#5A665E' }} />
                    <Tooltip />
                    <Bar dataKey="value" name="Measured (kg/ha)" fill="#123524" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="optimal_min" name="Target Min" fill="#52B788" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {result.nutrient_levels.map((n) => (
                  <div
                    key={n.nutrient}
                    className="rounded-xl border border-soil-border bg-parchment p-3.5"
                  >
                    <p className="text-xs font-semibold text-soil-muted">{n.nutrient}</p>
                    <p className="mt-1 font-mono text-lg font-bold text-forest-deep">{n.value}</p>
                    <span
                      className={`mt-1 inline-block rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase ${
                        n.status === 'optimal'
                          ? 'bg-emerald-mist text-emerald-leaf'
                          : n.status === 'low'
                            ? 'bg-gold-soft text-amber-900'
                            : 'bg-red-50 text-red-700'
                      }`}
                    >
                      {n.status}
                    </span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 rounded-xl border border-emerald-border bg-emerald-mist/50 p-4 text-xs text-soil-charcoal">
                <p>
                  <strong>pH Assessment:</strong> {result.ph_assessment}
                </p>
                <p>
                  <strong>Agronomic Notes:</strong> {result.advisory_notes}
                </p>
              </div>

              {result.dataset_coverage_note && (
                <div className="flex items-start gap-2 rounded-xl border border-soil-border bg-parchment p-3 text-xs text-soil-muted">
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-forest-deep" />
                  <p>{result.dataset_coverage_note}</p>
                </div>
              )}

              <div className="flex items-start gap-2.5 rounded-xl border border-amber-300 bg-amber-50 p-3.5 text-xs text-amber-950">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <p>{result.expert_disclaimer}</p>
              </div>
            </div>
          )}

          {history.length > 0 && (
            <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card">
              <div className="flex items-center justify-between border-b border-soil-border pb-3">
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4 text-forest-deep" />
                  <h3 className="font-display text-sm font-bold text-forest-deep">
                    Recent Fertilizer Plans
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
                          {item.crop_type ? `${item.crop_type}` : 'Plot Assessment'}
                          {item.soil_type ? ` · ${item.soil_type}` : ''}
                          {item.location ? ` (${item.location})` : ''}
                        </p>
                        <p className="text-[11px] font-mono text-soil-muted">
                          {item.nitrogen !== undefined
                            ? `N ${item.nitrogen} · P ${item.phosphorus} · K ${item.potassium} · pH ${item.soil_ph?.toFixed(1)}`
                            : item.ph_assessment.slice(0, 60)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-xs font-bold text-emerald-leaf">
                          {item.recommended_fertilizer}
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
