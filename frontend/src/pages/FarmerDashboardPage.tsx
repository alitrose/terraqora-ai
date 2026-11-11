import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpRight,
  Bot,
  CloudRain,
  FileText,
  FlaskConical,
  Leaf,
  MapPin,
  Sprout,
  TrendingUp,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { analyticsService, profileService, reportsService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
  StatCard,
} from '../components/StatusState';
import { useAuth } from '../context/AuthContext';
import type { AnalyticsResponse, Farm, GeneratedReport } from '../types/api';

const QUICK_MODULES = [
  {
    to: '/yield-prediction',
    label: 'Predict Crop Yield',
    desc: 'Leak-free regression estimate',
    icon: <TrendingUp className="h-4 w-4" />,
  },
  {
    to: '/disease-detection',
    label: 'Scan Leaf Disease',
    desc: 'Upload leaf photo for screening',
    icon: <Leaf className="h-4 w-4" />,
  },
  {
    to: '/fertilizer',
    label: 'Fertilizer Plan',
    desc: 'NPK & soil pH guidance',
    icon: <FlaskConical className="h-4 w-4" />,
  },
  {
    to: '/weather-irrigation',
    label: 'Irrigation Forecast',
    desc: '7-day ET₀ & rain schedule',
    icon: <CloudRain className="h-4 w-4" />,
  },
  {
    to: '/crop-recommendation',
    label: 'Crop Suitability',
    desc: '22-crop NPK climate match',
    icon: <Sprout className="h-4 w-4" />,
  },
  {
    to: '/assistant',
    label: 'GenAI Advisor',
    desc: '5-language grounded chat',
    icon: <Bot className="h-4 w-4" />,
  },
];

export function FarmerDashboardPage() {
  const { user } = useAuth();
  const [farms, setFarms] = useState<Farm[]>([]);
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [farmList, reportList, analyticsSummary] = await Promise.all([
        profileService.listFarms(),
        reportsService.list(),
        analyticsService.getSummary({}),
      ]);
      setFarms(farmList);
      setReports(reportList);
      setAnalytics(analyticsSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const totalHectares = farms.reduce((sum, f) => sum + f.area_hectares, 0);

  return (
    <AppShell
      title={`Welcome, ${user?.full_name?.split(' ')[0] || 'Farmer'}`}
      subtitle="Operational overview of your registered acreage, forecasts, and recent AI advisories."
    >
      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={loadDashboard} />
        </div>
      )}

      {loading ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <LoadingSkeleton rows={2} />
            <LoadingSkeleton rows={2} />
            <LoadingSkeleton rows={2} />
            <LoadingSkeleton rows={2} />
          </div>
          <LoadingSkeleton rows={5} />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
              Farm Telemetry Summary
            </p>
            {analytics && <SourceModeBadge mode={analytics.source_mode} />}
          </div>

          {/* KPI Strip */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Registered Farms"
              value={farms.length}
              hint={`${totalHectares.toFixed(1)} ha total managed area`}
              icon={<MapPin className="h-5 w-5" />}
            />
            <StatCard
              label="Benchmark Yield Avg"
              value={`${analytics?.avg_yield.toFixed(2) ?? '0.00'} t/ha`}
              hint="Non-coconut historical mean"
              accent="emerald"
              icon={<TrendingUp className="h-5 w-5" />}
            />
            <StatCard
              label="Mean Annual Rainfall"
              value={`${analytics?.avg_rainfall_mm.toFixed(0) ?? '0'} mm`}
              hint="National agro-climatic baseline"
              accent="gold"
              icon={<CloudRain className="h-5 w-5" />}
            />
            <StatCard
              label="Saved AI Reports"
              value={reports.length}
              hint="Ready for PDF summary export"
              icon={<FileText className="h-5 w-5" />}
            />
          </div>

          {/* Quick Actions & Trend Chart */}
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-7">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    Multi-Year Yield & Rainfall Index
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Historical trajectory across 19,689 Indian agricultural records
                  </p>
                </div>
                <Link
                  to="/analytics"
                  className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-leaf hover:underline"
                >
                  Full Analytics
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>

              <div className="mt-4 h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={analytics?.annual_trends || []}>
                    <defs>
                      <linearGradient id="yieldGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2D6A4F" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#2D6A4F" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E8E1" />
                    <XAxis dataKey="year" tick={{ fontSize: 12, fill: '#5A665E' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#5A665E' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E4E8E1',
                        borderRadius: '12px',
                        fontSize: '12px',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="avg_yield"
                      name="Avg Yield (t/ha)"
                      stroke="#123524"
                      strokeWidth={2}
                      fill="url(#yieldGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Quick Module Launchers */}
            <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5">
              <h2 className="font-display text-base font-bold text-forest-deep">
                Intelligence Workflows
              </h2>
              <p className="text-xs text-soil-muted">
                Launch any TerraQora AI decision tool directly
              </p>

              <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-1">
                {QUICK_MODULES.map((m) => (
                  <Link
                    key={m.to}
                    to={m.to}
                    className="flex items-center justify-between rounded-xl border border-soil-border bg-parchment/60 px-3.5 py-2.5 transition-colors hover:border-emerald-border hover:bg-emerald-mist/50"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-forest-deep shadow-xs">
                        {m.icon}
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-soil-charcoal">{m.label}</p>
                        <p className="text-xs text-soil-muted">{m.desc}</p>
                      </div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-soil-muted" />
                  </Link>
                ))}
              </div>
            </div>
          </div>

          {/* Farms & Recent Reports */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-base font-bold text-forest-deep">
                  Your Registered Farms
                </h2>
                <Link
                  to="/profile"
                  className="text-xs font-semibold text-emerald-leaf hover:underline"
                >
                  Manage Plots
                </Link>
              </div>

              {farms.length === 0 ? (
                <div className="mt-4">
                  <EmptyState
                    title="No farms registered yet"
                    description="Add your farm plot coordinates, soil pH, and acreage in Profile & Farms."
                    action={
                      <Link
                        to="/profile"
                        className="rounded-xl bg-forest-deep px-4 py-2 text-xs font-semibold text-white"
                      >
                        Add First Farm
                      </Link>
                    }
                  />
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  {farms.map((farm) => (
                    <div
                      key={farm.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-soil-border bg-parchment/60 p-4"
                    >
                      <div>
                        <p className="text-sm font-bold text-forest-deep">{farm.name}</p>
                        <p className="text-xs text-soil-muted">
                          {farm.district ? `${farm.district}, ` : ''}
                          {farm.state} · {farm.soil_type || 'Soil pending'} (pH{' '}
                          {farm.soil_ph ?? '—'})
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-sm font-bold text-soil-charcoal">
                          {farm.area_hectares} ha
                        </p>
                        <p className="text-[11px] font-medium text-emerald-leaf">
                          {farm.primary_crop || 'Multi-crop'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-base font-bold text-forest-deep">
                  Recent AI Reports
                </h2>
                <Link
                  to="/reports"
                  className="text-xs font-semibold text-emerald-leaf hover:underline"
                >
                  Generate New
                </Link>
              </div>

              {reports.length === 0 ? (
                <div className="mt-4">
                  <EmptyState
                    title="No generated reports"
                    description="Create a combined yield, fertilizer, and irrigation summary PDF in AI Reports."
                  />
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  {reports.slice(0, 4).map((r) => (
                    <div
                      key={r.id}
                      className="rounded-xl border border-soil-border bg-parchment/60 p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-forest-deep">{r.title}</p>
                        <span className="shrink-0 rounded-md bg-emerald-mist px-2 py-0.5 font-mono text-[11px] font-semibold text-emerald-leaf">
                          {r.predicted_yield} {r.yield_unit}
                        </span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs text-soil-muted">{r.ai_summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
