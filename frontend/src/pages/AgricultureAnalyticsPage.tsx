import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CloudRain,
  Database,
  Droplets,
  Filter,
  FlaskConical,
  Info,
  MapPin,
  RotateCcw,
  Sprout,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { analyticsService, profileService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
  StatCard,
} from '../components/StatusState';
import { CROP_SEASONS, INDIAN_STATES, YIELD_CROPS } from '../data/agriCatalog';
import type {
  AnalyticsFilter,
  AnalyticsResponse,
  Farm,
  UserOperationalAnalyticsResponse,
} from '../types/api';

export function AgricultureAnalyticsPage() {
  const [activeTab, setActiveTab] = useState<'operations' | 'benchmarks'>('operations');

  // Operational tab states
  const [rangeDays, setRangeDays] = useState<number>(30);
  const [selectedFarmId, setSelectedFarmId] = useState<string>('');
  const [farms, setFarms] = useState<Farm[]>([]);
  const [operationalData, setOperationalData] =
    useState<UserOperationalAnalyticsResponse | null>(null);
  const [opLoading, setOpLoading] = useState<boolean>(true);
  const [opError, setOpError] = useState<string | null>(null);

  // Benchmark tab states
  const [crop, setCrop] = useState('');
  const [state, setState] = useState('');
  const [season, setSeason] = useState('');
  const [yearStart, setYearStart] = useState<number>(2013);
  const [yearEnd, setYearEnd] = useState<number>(2020);
  const [benchLoading, setBenchLoading] = useState(true);
  const [benchError, setBenchError] = useState<string | null>(null);
  const [benchData, setBenchData] = useState<AnalyticsResponse | null>(null);

  // Load farms on mount
  useEffect(() => {
    profileService
      .listFarms()
      .then((fList) => setFarms(fList))
      .catch(() => setFarms([]));
  }, []);

  // Load operational analytics
  const loadOperational = async (days: number, farmId?: string) => {
    setOpLoading(true);
    setOpError(null);
    try {
      const res = await analyticsService.getOperational(days, farmId || undefined);
      setOperationalData(res);
    } catch (err) {
      setOpError(err instanceof Error ? err.message : 'Unable to load operational analytics.');
    } finally {
      setOpLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'operations') {
      loadOperational(rangeDays, selectedFarmId);
    }
  }, [activeTab, rangeDays, selectedFarmId]);

  // Load benchmark dataset analytics
  const loadBenchmarkAnalytics = async (filters: AnalyticsFilter) => {
    setBenchLoading(true);
    setBenchError(null);
    try {
      const res = await analyticsService.getSummary(filters);
      setBenchData(res);
    } catch (err) {
      setBenchError(err instanceof Error ? err.message : 'Unable to load dataset benchmarks.');
    } finally {
      setBenchLoading(false);
    }
  };

  useEffect(() => {
    loadBenchmarkAnalytics({ year_start: 2013, year_end: 2020 });
  }, []);

  const handleBenchmarkApply = (e: React.FormEvent) => {
    e.preventDefault();
    if (yearStart > yearEnd) {
      setBenchError('Start year must be less than or equal to End year.');
      return;
    }
    loadBenchmarkAnalytics({
      crop: crop || undefined,
      state: state || undefined,
      season: season || undefined,
      year_start: yearStart,
      year_end: yearEnd,
    });
  };

  const handleBenchmarkReset = () => {
    setCrop('');
    setState('');
    setSeason('');
    setYearStart(2013);
    setYearEnd(2020);
    loadBenchmarkAnalytics({ year_start: 2013, year_end: 2020 });
  };

  return (
    <AppShell
      title="Agricultural Analytics & Intelligence"
      subtitle="Operational farm activity timeline, diagnostic telemetry, and leak-free national crop benchmarks."
    >
      {/* Primary Tab Navigation */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-soil-border pb-3">
        <div className="flex gap-2">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'operations'}
            onClick={() => setActiveTab('operations')}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
              activeTab === 'operations'
                ? 'bg-forest-deep text-white shadow-sm'
                : 'border border-soil-border bg-white text-soil-charcoal hover:bg-parchment'
            }`}
          >
            <Activity className="h-4 w-4 text-emerald-leaf" />
            <span>Farm Operations & Real Intelligence</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'benchmarks'}
            onClick={() => setActiveTab('benchmarks')}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
              activeTab === 'benchmarks'
                ? 'bg-forest-deep text-white shadow-sm'
                : 'border border-soil-border bg-white text-soil-charcoal hover:bg-parchment'
            }`}
          >
            <Database className="h-4 w-4 text-gold-bright" />
            <span>National Agriculture Benchmarks</span>
          </button>
        </div>

        {activeTab === 'operations' && operationalData && (
          <SourceModeBadge mode={operationalData.source_mode} />
        )}
        {activeTab === 'benchmarks' && benchData && (
          <SourceModeBadge mode={benchData.source_mode} />
        )}
      </div>

      {/* ================= TAB 1: OPERATIONAL INTELLIGENCE ================= */}
      {activeTab === 'operations' && (
        <div className="space-y-6">
          {/* Operational Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-soil-border bg-white p-4 shadow-card">
            {/* Date Range Selector */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-2 inline-flex items-center gap-1.5 text-xs font-semibold text-soil-muted">
                <CalendarDays className="h-3.5 w-3.5" /> Range:
              </span>
              {[
                { label: '7 Days', val: 7 },
                { label: '30 Days', val: 30 },
                { label: '90 Days', val: 90 },
                { label: '1 Year', val: 365 },
                { label: 'All Time', val: 3650 },
              ].map((opt) => (
                <button
                  key={opt.label}
                  type="button"
                  onClick={() => setRangeDays(opt.val)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                    rangeDays === opt.val
                      ? 'bg-forest-deep text-white'
                      : 'border border-soil-border bg-parchment/60 text-soil-charcoal hover:bg-parchment'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Farm Plot Selector */}
            <div className="flex items-center gap-2">
              <label htmlFor="op-farm-select" className="text-xs font-semibold text-soil-muted">
                Farm Plot:
              </label>
              <select
                id="op-farm-select"
                aria-label="Filter by Farm Plot"
                value={selectedFarmId}
                onChange={(e) => setSelectedFarmId(e.target.value)}
                className="rounded-xl border border-soil-border bg-parchment/50 px-3 py-1.5 text-xs font-semibold text-soil-charcoal focus:border-emerald-leaf focus:outline-none"
              >
                <option value="">All Registered Farms ({farms.length})</option>
                {farms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.area_hectares} ha · {f.state})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {opError && (
            <ErrorAlert
              message={opError}
              onRetry={() => loadOperational(rangeDays, selectedFarmId)}
            />
          )}

          {opLoading || !operationalData ? (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <LoadingSkeleton rows={2} />
                <LoadingSkeleton rows={2} />
                <LoadingSkeleton rows={2} />
                <LoadingSkeleton rows={2} />
              </div>
              <LoadingSkeleton rows={6} />
            </div>
          ) : (
            <>
              {/* KPI Strip */}
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  label="Operational Activities"
                  value={operationalData.summary.total_activities}
                  hint={`${operationalData.summary.yield_predictions} yield · ${operationalData.summary.crop_recommendations} crop · ${operationalData.summary.fertilizer_recommendations} fert`}
                  icon={<BarChart3 className="h-5 w-5" />}
                />
                <StatCard
                  label="Active Farm Plots"
                  value={operationalData.summary.active_farms_count}
                  hint={`${operationalData.summary.total_hectares_managed.toFixed(1)} ha actively managed`}
                  accent="emerald"
                  icon={<MapPin className="h-5 w-5" />}
                />
                <StatCard
                  label="Plant Disease Scans"
                  value={operationalData.summary.disease_detections}
                  hint="Computer Vision leaf diagnostic screenings"
                  accent="gold"
                  icon={<Sprout className="h-5 w-5" />}
                />
                <StatCard
                  label="Irrigation & AI Advisories"
                  value={
                    operationalData.summary.irrigation_advisories +
                    operationalData.summary.ai_chat_sessions
                  }
                  hint={`${operationalData.summary.irrigation_advisories} irrigation · ${operationalData.summary.ai_chat_sessions} AI consults`}
                  icon={<Droplets className="h-5 w-5" />}
                />
              </div>

              {operationalData.summary.total_activities === 0 ? (
                <EmptyState
                  title="No operational records found for this period"
                  description="Use the Yield, Crop Recommendation, Fertilizer, or Plant Disease modules to generate operational records for this farm."
                />
              ) : (
                <>
                  {/* Activity Timeline Chart */}
                  <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h2 className="font-display text-base font-bold text-forest-deep">
                          Daily Intelligence Activity Timeline
                        </h2>
                        <p className="text-xs text-soil-muted">
                          Distribution of AI inferences and agronomic recommendations over time
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={operationalData.timeline}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#5A665E' }} />
                          <YAxis tick={{ fontSize: 11, fill: '#5A665E' }} />
                          <Tooltip />
                          <Legend wrapperStyle={{ fontSize: '12px' }} />
                          <Bar
                            dataKey="yield_predictions"
                            name="Yield Predictions"
                            fill="#123524"
                            stackId="a"
                          />
                          <Bar
                            dataKey="crop_recommendations"
                            name="Crop Suitability"
                            fill="#2D6A4F"
                            stackId="a"
                          />
                          <Bar
                            dataKey="fertilizer_recommendations"
                            name="Fertilizer Plans"
                            fill="#52B788"
                            stackId="a"
                          />
                          <Bar
                            dataKey="disease_detections"
                            name="Disease Vision"
                            fill="#C9972C"
                            stackId="a"
                          />
                          <Bar
                            dataKey="irrigation_advisories"
                            name="Irrigation"
                            fill="#4A90E2"
                            stackId="a"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Operational Breakdowns Grid */}
                  <div className="grid gap-6 lg:grid-cols-2">
                    {/* Top Crops Analyzed */}
                    <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                      <h2 className="font-display text-base font-bold text-forest-deep">
                        Crops Forecasted & Recommended
                      </h2>
                      <p className="text-xs text-soil-muted">
                        Operational frequency and mean forecasted yield by crop
                      </p>
                      <div className="mt-4 space-y-3">
                        {operationalData.top_crops.length === 0 ? (
                          <p className="text-xs text-soil-muted">No crop data recorded yet.</p>
                        ) : (
                          operationalData.top_crops.map((c) => (
                            <div
                              key={c.crop}
                              className="flex items-center justify-between rounded-xl border border-soil-border bg-parchment/40 px-3.5 py-2.5"
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-xs text-soil-charcoal">
                                  {c.crop}
                                </span>
                                <span className="rounded-full bg-forest-deep/10 px-2 py-0.5 text-[10px] font-bold text-forest-deep">
                                  {c.count} run{c.count > 1 ? 's' : ''}
                                </span>
                              </div>
                              <span className="font-mono text-xs font-bold text-emerald-leaf">
                                {c.avg_yield ? `${c.avg_yield} ${c.yield_unit}` : 'Suitability only'}
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Plant Disease CV Findings */}
                    <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                      <h2 className="font-display text-base font-bold text-forest-deep">
                        Leaf Pathology Detections
                      </h2>
                      <p className="text-xs text-soil-muted">
                        Identified leaf conditions and mean confidence
                      </p>
                      <div className="mt-4 space-y-3">
                        {operationalData.disease_findings.length === 0 ? (
                          <p className="text-xs text-soil-muted">
                            No plant disease screenings performed yet.
                          </p>
                        ) : (
                          operationalData.disease_findings.map((d) => (
                            <div
                              key={d.label}
                              className="flex items-center justify-between rounded-xl border border-soil-border bg-parchment/40 px-3.5 py-2.5"
                            >
                              <div>
                                <div className="flex items-center gap-1.5">
                                  <span className="font-semibold text-xs text-forest-deep">
                                    {d.crop_name}
                                  </span>
                                  <span className="text-xs text-soil-muted">· {d.disease_name}</span>
                                </div>
                                <span className="text-[10px] text-soil-muted">
                                  {d.count} diagnosis · {(d.avg_confidence * 100).toFixed(1)}% conf
                                </span>
                              </div>
                              {d.uncertain_count > 0 ? (
                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                                  <AlertTriangle className="h-3 w-3" />
                                  {d.uncertain_count} flagged
                                </span>
                              ) : (
                                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                                  Verified
                                </span>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Farm-Level Breakdown Table */}
                  <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                    <h2 className="font-display text-base font-bold text-forest-deep">
                      Farm Plot Utilization Summary
                    </h2>
                    <p className="text-xs text-soil-muted">
                      Telemetry summary aggregated across your registered agricultural land holdings
                    </p>
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full min-w-[560px] text-left text-xs">
                        <thead>
                          <tr className="border-b border-soil-border uppercase text-soil-muted">
                            <th className="py-2.5 pr-4 font-semibold">Farm Plot</th>
                            <th className="py-2.5 pr-4 font-semibold">Location</th>
                            <th className="py-2.5 pr-4 font-semibold">Acreage</th>
                            <th className="py-2.5 pr-4 font-semibold">Activities</th>
                            <th className="py-2.5 font-semibold">Last Recorded Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-soil-border">
                          {operationalData.farm_breakdown.map((fb) => (
                            <tr key={fb.farm_id} className="hover:bg-parchment/40">
                              <td className="py-3 pr-4 font-semibold text-forest-deep">
                                {fb.farm_name}
                              </td>
                              <td className="py-3 pr-4 text-soil-charcoal">{fb.state}</td>
                              <td className="py-3 pr-4 font-mono">{fb.area_hectares} ha</td>
                              <td className="py-3 pr-4 font-mono font-bold text-forest-deep">
                                {fb.total_activities}
                              </td>
                              <td className="py-3 text-soil-muted">
                                {fb.last_activity
                                  ? new Date(fb.last_activity).toLocaleDateString()
                                  : 'No activity'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}

      {/* ================= TAB 2: NATIONAL BENCHMARKS ================= */}
      {activeTab === 'benchmarks' && (
        <div className="space-y-6">
          {/* Benchmark Filters Form */}
          <form
            onSubmit={handleBenchmarkApply}
            className="grid gap-3 rounded-2xl border border-soil-border bg-white p-5 shadow-card sm:grid-cols-2 lg:grid-cols-6"
          >
            <div>
              <label htmlFor="an-crop" className="block text-xs font-semibold text-soil-charcoal">
                Crop Filter
              </label>
              <select
                id="an-crop"
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                <option value="">All 55 Crops</option>
                {YIELD_CROPS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="an-state" className="block text-xs font-semibold text-soil-charcoal">
                State Filter
              </label>
              <select
                id="an-state"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                <option value="">All 30 States</option>
                {INDIAN_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="an-season" className="block text-xs font-semibold text-soil-charcoal">
                Season
              </label>
              <select
                id="an-season"
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                <option value="">All Seasons</option>
                {CROP_SEASONS.map((se) => (
                  <option key={se} value={se}>
                    {se}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="an-y1" className="block text-xs font-semibold text-soil-charcoal">
                Year Start
              </label>
              <input
                id="an-y1"
                type="number"
                min={1997}
                max={2020}
                value={yearStart}
                onChange={(e) => setYearStart(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="an-y2" className="block text-xs font-semibold text-soil-charcoal">
                Year End
              </label>
              <input
                id="an-y2"
                type="number"
                min={1997}
                max={2020}
                value={yearEnd}
                onChange={(e) => setYearEnd(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div className="flex items-end gap-2">
              <button
                type="submit"
                disabled={benchLoading}
                className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-forest-deep px-3 py-2.5 text-xs font-semibold text-white hover:bg-forest-hover disabled:opacity-50"
              >
                <Filter className="h-3.5 w-3.5 text-gold-bright" />
                Apply
              </button>
              <button
                type="button"
                onClick={handleBenchmarkReset}
                aria-label="Reset Filters"
                className="inline-flex items-center justify-center rounded-xl border border-soil-border bg-parchment px-3 py-2.5 text-xs font-semibold text-soil-charcoal hover:bg-parchment-muted"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            </div>
          </form>

          {benchError && (
            <ErrorAlert
              message={benchError}
              onRetry={() => loadBenchmarkAnalytics({ year_start: 2013, year_end: 2020 })}
            />
          )}

          {benchLoading || !benchData ? (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <LoadingSkeleton rows={2} />
                <LoadingSkeleton rows={2} />
                <LoadingSkeleton rows={2} />
                <LoadingSkeleton rows={2} />
              </div>
              <LoadingSkeleton rows={6} />
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="inline-flex items-center gap-2 text-xs text-soil-muted">
                  <Info className="h-4 w-4 text-emerald-leaf" />
                  <span>
                    Filtered View: <strong>{benchData.unique_crops}</strong> crop(s) across{' '}
                    <strong>{benchData.unique_states}</strong> state(s). Coconut is isolated in{' '}
                    <strong>nuts/ha</strong> where selected.
                  </span>
                </div>
                <SourceModeBadge mode={benchData.source_mode} />
              </div>

              {/* KPI Strip */}
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  label="Dataset Records"
                  value={benchData.total_records.toLocaleString()}
                  hint="Filtered crop_yield.csv observations"
                  icon={<BarChart3 className="h-5 w-5" />}
                />
                <StatCard
                  label="Mean Yield Rate"
                  value={`${benchData.avg_yield.toFixed(2)} ${crop === 'Coconut' ? 'nuts/ha' : 't/ha'}`}
                  hint="Aggregated historical unit productivity"
                  accent="emerald"
                  icon={<Sprout className="h-5 w-5" />}
                />
                <StatCard
                  label="Mean Annual Rainfall"
                  value={`${benchData.avg_rainfall_mm.toFixed(1)} mm`}
                  hint="Observed precipitation across slice"
                  accent="gold"
                  icon={<CloudRain className="h-5 w-5" />}
                />
                <StatCard
                  label="Total Input Volume"
                  value={`${benchData.total_fertilizer_tonnes.toLocaleString()} t`}
                  hint={`${benchData.total_pesticide_tonnes.toLocaleString()} t pesticide total`}
                  icon={<FlaskConical className="h-5 w-5" />}
                />
              </div>

              {/* Charts Row 1 */}
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    Crop Record Distribution
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Record count vs. average unit yield across top dataset crops
                  </p>
                  <div className="mt-4 h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={benchData.crop_distribution}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#1B241E' }} />
                        <YAxis tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '12px' }} />
                        <Bar
                          dataKey="records"
                          name="Dataset Records"
                          fill="#123524"
                          radius={[6, 6, 0, 0]}
                        />
                        <Bar
                          dataKey="avg_yield"
                          name="Avg Yield"
                          fill="#C9972C"
                          radius={[6, 6, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    State-wise Production Volume (MT)
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Cumulative regional output across major agricultural states
                  </p>
                  <div className="mt-4 h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={benchData.state_production} layout="vertical" margin={{ left: 24 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                        <XAxis type="number" tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <YAxis
                          type="category"
                          dataKey="state"
                          width={110}
                          tick={{ fontSize: 11, fill: '#1B241E' }}
                        />
                        <Tooltip />
                        <Bar
                          dataKey="production_mt"
                          name="Production (Million Tonnes)"
                          fill="#2D6A4F"
                          radius={[0, 6, 6, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Charts Row 2 */}
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    Annual Rainfall vs. Mean Yield Trend
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Year-over-year precipitation variability alongside productivity trajectory
                  </p>
                  <div className="mt-4 h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={benchData.annual_trends}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                        <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          tick={{ fontSize: 11, fill: '#5A665E' }}
                        />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '12px' }} />
                        <Bar
                          yAxisId="left"
                          dataKey="avg_rainfall"
                          name="Avg Rainfall (mm)"
                          fill="#52B788"
                          radius={[6, 6, 0, 0]}
                        />
                        <Line
                          yAxisId="right"
                          type="monotone"
                          dataKey="avg_yield"
                          name="Avg Yield (t/ha)"
                          stroke="#123524"
                          strokeWidth={2.5}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    Fertilizer & Pesticide Intensity Index
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Indexed chemical input trajectory across recent cropping years
                  </p>
                  <div className="mt-4 h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={benchData.annual_trends}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                        <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <YAxis tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '12px' }} />
                        <Bar
                          dataKey="fertilizer_index"
                          name="Fertilizer Index"
                          fill="#2D6A4F"
                          radius={[6, 6, 0, 0]}
                        />
                        <Line
                          type="monotone"
                          dataKey="pesticide_index"
                          name="Pesticide Index"
                          stroke="#C9972C"
                          strokeWidth={2.5}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Charts Row 3: Seasonal Yield Comparison + Correlation Matrix */}
              <div className="grid gap-6 lg:grid-cols-12">
                <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-7">
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    Crop-wise Seasonal Yield Comparison
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Mean yield comparison across Kharif, Rabi, and Whole Year plantings
                  </p>
                  <div className="mt-4 h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={benchData.yield_comparison}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                        <XAxis dataKey="crop" tick={{ fontSize: 12, fill: '#1B241E' }} />
                        <YAxis tick={{ fontSize: 11, fill: '#5A665E' }} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '12px' }} />
                        <Bar dataKey="kharif" name="Kharif" fill="#123524" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="rabi" name="Rabi" fill="#52B788" radius={[4, 4, 0, 0]} />
                        <Bar
                          dataKey="whole_year"
                          name="Whole Year"
                          fill="#C9972C"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5">
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    Feature Correlation Matrix
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Key Pearson correlations (post-harvest <code>Production</code> excluded to prevent leakage)
                  </p>
                  <div className="mt-4 space-y-2.5">
                    {benchData.correlation_matrix.map((row) => {
                      const absVal = Math.abs(row.correlation);
                      const badgeCls =
                        absVal >= 0.7
                          ? 'bg-emerald-mist text-forest-deep border-emerald-border'
                          : absVal >= 0.3
                            ? 'bg-gold-soft text-amber-900 border-amber-200'
                            : 'bg-parchment text-soil-muted border-soil-border';
                      return (
                        <div
                          key={`${row.feature_x}-${row.feature_y}`}
                          className="flex items-center justify-between rounded-xl border border-soil-border bg-parchment/50 px-3.5 py-2.5"
                        >
                          <span className="text-xs font-semibold text-soil-charcoal">
                            {row.feature_x} ↔ {row.feature_y}
                          </span>
                          <span
                            className={`rounded-lg border px-2.5 py-0.5 font-mono text-xs font-bold ${badgeCls}`}
                          >
                            r = {row.correlation.toFixed(2)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
