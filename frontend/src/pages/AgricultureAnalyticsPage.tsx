import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  CloudRain,
  Filter,
  FlaskConical,
  Info,
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
import { analyticsService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
  StatCard,
} from '../components/StatusState';
import { CROP_SEASONS, INDIAN_STATES, YIELD_CROPS } from '../data/agriCatalog';
import type { AnalyticsFilter, AnalyticsResponse } from '../types/api';

export function AgricultureAnalyticsPage() {
  const [crop, setCrop] = useState('');
  const [state, setState] = useState('');
  const [season, setSeason] = useState('');
  const [yearStart, setYearStart] = useState<number>(2013);
  const [yearEnd, setYearEnd] = useState<number>(2020);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyticsResponse | null>(null);

  const loadAnalytics = async (filters: AnalyticsFilter) => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyticsService.getSummary(filters);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics({ year_start: 2013, year_end: 2020 });
  }, []);

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    if (yearStart > yearEnd) {
      setError('Start year must be less than or equal to End year.');
      return;
    }
    loadAnalytics({
      crop: crop || undefined,
      state: state || undefined,
      season: season || undefined,
      year_start: yearStart,
      year_end: yearEnd,
    });
  };

  const handleReset = () => {
    setCrop('');
    setState('');
    setSeason('');
    setYearStart(2013);
    setYearEnd(2020);
    loadAnalytics({ year_start: 2013, year_end: 2020 });
  };

  return (
    <AppShell
      title="Agriculture Dataset Analytics"
      subtitle="Exploratory trends, seasonal yield benchmarks, input intensity, and leak-free feature correlations."
    >
      {/* Filter Bar */}
      <form
        onSubmit={handleApply}
        className="mb-6 grid gap-3 rounded-2xl border border-soil-border bg-white p-5 shadow-card sm:grid-cols-2 lg:grid-cols-6"
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
            disabled={loading}
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-forest-deep px-3 py-2.5 text-xs font-semibold text-white hover:bg-forest-hover disabled:opacity-50"
          >
            <Filter className="h-3.5 w-3.5 text-gold-bright" />
            Apply
          </button>
          <button
            type="button"
            onClick={handleReset}
            aria-label="Reset Filters"
            className="inline-flex items-center justify-center rounded-xl border border-soil-border bg-parchment px-3 py-2.5 text-xs font-semibold text-soil-charcoal hover:bg-parchment-muted"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={() => loadAnalytics({})} />
        </div>
      )}

      {loading || !data ? (
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
                Filtered View: <strong>{data.unique_crops}</strong> crop(s) across{' '}
                <strong>{data.unique_states}</strong> state(s). Coconut is isolated in{' '}
                <strong>nuts/ha</strong> where selected.
              </span>
            </div>
            <SourceModeBadge mode={data.source_mode} />
          </div>

          {/* KPI Strip */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Dataset Records"
              value={data.total_records.toLocaleString()}
              hint="Filtered crop_yield.csv observations"
              icon={<BarChart3 className="h-5 w-5" />}
            />
            <StatCard
              label="Mean Yield Rate"
              value={`${data.avg_yield.toFixed(2)} ${crop === 'Coconut' ? 'nuts/ha' : 't/ha'}`}
              hint="Aggregated historical unit productivity"
              accent="emerald"
              icon={<Sprout className="h-5 w-5" />}
            />
            <StatCard
              label="Mean Annual Rainfall"
              value={`${data.avg_rainfall_mm.toFixed(1)} mm`}
              hint="Observed precipitation across slice"
              accent="gold"
              icon={<CloudRain className="h-5 w-5" />}
            />
            <StatCard
              label="Total Input Volume"
              value={`${data.total_fertilizer_tonnes.toLocaleString()} t`}
              hint={`${data.total_pesticide_tonnes.toLocaleString()} t pesticide total`}
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
                  <BarChart data={data.crop_distribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#1B241E' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#5A665E' }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Bar dataKey="records" name="Dataset Records" fill="#123524" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="avg_yield" name="Avg Yield" fill="#C9972C" radius={[6, 6, 0, 0]} />
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
                  <BarChart data={data.state_production} layout="vertical" margin={{ left: 24 }}>
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
                  <ComposedChart data={data.annual_trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                    <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#5A665E' }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#5A665E' }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#5A665E' }} />
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
                  <ComposedChart data={data.annual_trends}>
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
                  <BarChart data={data.yield_comparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                    <XAxis dataKey="crop" tick={{ fontSize: 12, fill: '#1B241E' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#5A665E' }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Bar dataKey="kharif" name="Kharif" fill="#123524" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="rabi" name="Rabi" fill="#52B788" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="whole_year" name="Whole Year" fill="#C9972C" radius={[4, 4, 0, 0]} />
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
                {data.correlation_matrix.map((row) => {
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
    </AppShell>
  );
}
