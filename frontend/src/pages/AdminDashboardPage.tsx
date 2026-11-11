import { useEffect, useState } from 'react';
import {
  Activity,
  Bot,
  Cpu,
  MapPin,
  Search,
  Server,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { API_BASE_URL } from '../api/client';
import { adminService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
  StatCard,
} from '../components/StatusState';
import type { AdminOverviewResponse } from '../types/api';

export function AdminDashboardPage() {
  const [overview, setOverview] = useState<AdminOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'farmer' | 'admin'>('all');

  const loadOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminService.getOverview();
      setOverview(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load admin telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const filteredUsers = (overview?.users || []).filter((u) => {
    const matchesRole = roleFilter === 'all' || u.role === roleFilter;
    const q = searchTerm.trim().toLowerCase();
    const matchesSearch =
      !q ||
      u.full_name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q);
    return matchesRole && matchesSearch;
  });

  return (
    <AppShell
      title="Admin & Model Registry Console"
      subtitle="Platform usage diagnostics, ML/CV deployment budgets, and registered user directory."
    >
      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={loadOverview} />
        </div>
      )}

      {loading || !overview ? (
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
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-forest-deep">
              <ShieldCheck className="h-4 w-4 text-emerald-leaf" />
              Role-Restricted Administration View
            </div>
            <SourceModeBadge mode={overview.source_mode} />
          </div>

          {/* KPI Strip */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Registered Users"
              value={overview.total_users}
              hint="Active farmer & agronomist accounts"
              icon={<Users className="h-5 w-5" />}
            />
            <StatCard
              label="Active Farm Plots"
              value={overview.active_farms}
              hint="Verified plot geometries & soil records"
              accent="emerald"
              icon={<MapPin className="h-5 w-5" />}
            />
            <StatCard
              label="ML & Vision Runs"
              value={overview.total_predictions + overview.total_disease_scans}
              hint={`${overview.total_predictions} tabular · ${overview.total_disease_scans} leaf scans`}
              accent="gold"
              icon={<Activity className="h-5 w-5" />}
            />
            <StatCard
              label="AI Advisor Turns"
              value={overview.total_ai_chats}
              hint="Multilingual Gemini RAG interactions"
              icon={<Bot className="h-5 w-5" />}
            />
          </div>

          {/* ML & CV Model Registry */}
          <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Cpu className="h-5 w-5 text-forest-deep" />
                <div>
                  <h2 className="font-display text-base font-bold text-forest-deep">
                    ML & Computer Vision Model Registry
                  </h2>
                  <p className="text-xs text-soil-muted">
                    Honest pipeline status and Render 512 MB free-tier memory footprint targets
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table aria-label="ML Model Registry" className="w-full min-w-[640px] text-left text-xs">
                <thead>
                  <tr className="border-b border-soil-border text-soil-muted uppercase">
                    <th className="py-2.5 pr-4 font-semibold">Module</th>
                    <th className="py-2.5 pr-4 font-semibold">Algorithm / Architecture</th>
                    <th className="py-2.5 pr-4 font-semibold">Status</th>
                    <th className="py-2.5 pr-4 font-semibold">Primary Metric</th>
                    <th className="py-2.5 font-semibold">Artifact Target</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-soil-border">
                  {overview.models.map((m) => (
                    <tr key={m.module} className="hover:bg-parchment/50">
                      <td className="py-3 pr-4 font-semibold text-forest-deep">{m.module}</td>
                      <td className="py-3 pr-4 text-soil-charcoal">{m.algorithm}</td>
                      <td className="py-3 pr-4">
                        <span className="rounded-full bg-gold-soft px-2.5 py-0.5 text-[11px] font-semibold text-amber-900">
                          {m.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-mono text-soil-charcoal">
                        {m.metric_label}: {m.metric_value}
                      </td>
                      <td className="py-3 font-mono text-emerald-leaf">{m.artifact_size}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* User Directory */}
          <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-base font-bold text-forest-deep">
                  Platform Users Directory
                </h2>
                <p className="text-xs text-soil-muted">
                  Filter accounts by role or search by name and email
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-soil-muted" />
                  <input
                    type="search"
                    aria-label="Search users"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search name or email..."
                    className="rounded-xl border border-soil-border bg-parchment/50 py-1.5 pl-8 pr-3 text-xs focus:border-emerald-leaf focus:bg-white focus:outline-none"
                  />
                </div>
                <select
                  aria-label="Filter users by role"
                  value={roleFilter}
                  onChange={(e) =>
                    setRoleFilter(e.target.value as 'all' | 'farmer' | 'admin')
                  }
                  className="rounded-xl border border-soil-border bg-parchment/50 px-3 py-1.5 text-xs font-semibold text-forest-deep"
                >
                  <option value="all">All Roles</option>
                  <option value="farmer">Farmer Only</option>
                  <option value="admin">Admin Only</option>
                </select>
              </div>
            </div>

            {filteredUsers.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  title="No matching user accounts"
                  description="Clear the search term or select All Roles to inspect all users."
                />
              </div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table aria-label="Platform Users Directory" className="w-full min-w-[640px] text-left text-xs">
                  <thead>
                    <tr className="border-b border-soil-border text-soil-muted uppercase">
                      <th className="py-2.5 pr-4 font-semibold">Name</th>
                      <th className="py-2.5 pr-4 font-semibold">Email</th>
                      <th className="py-2.5 pr-4 font-semibold">Role</th>
                      <th className="py-2.5 pr-4 font-semibold">Language</th>
                      <th className="py-2.5 pr-4 font-semibold">Farms</th>
                      <th className="py-2.5 pr-4 font-semibold">Predictions</th>
                      <th className="py-2.5 font-semibold">State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-soil-border">
                    {filteredUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-parchment/50">
                        <td className="py-3 pr-4 font-semibold text-forest-deep">{u.full_name}</td>
                        <td className="py-3 pr-4 font-mono text-soil-charcoal">{u.email}</td>
                        <td className="py-3 pr-4 uppercase font-semibold">{u.role}</td>
                        <td className="py-3 pr-4 uppercase">{u.preferred_language}</td>
                        <td className="py-3 pr-4 font-mono">{u.farms_count}</td>
                        <td className="py-3 pr-4 font-mono">{u.predictions_count}</td>
                        <td className="py-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                              u.is_active
                                ? 'bg-emerald-mist text-emerald-leaf'
                                : 'bg-red-50 text-red-700'
                            }`}
                          >
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* System Diagnostics Footer */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-soil-border bg-white px-5 py-4 text-xs text-soil-muted shadow-card">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-emerald-leaf" />
              <span>
                Configured Backend API Endpoint: <code className="text-forest-deep">{API_BASE_URL}</code>
              </span>
            </div>
            <span>Database Schema: 11 PostgreSQL Tables Ready · FastAPI Wired in Phase 4</span>
          </div>
        </div>
      )}
    </AppShell>
  );
}
