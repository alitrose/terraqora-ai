import React from 'react';
import { AlertTriangle, FlaskConical, Inbox, RefreshCw } from 'lucide-react';
import type { DataSourceMode } from '../types/api';

export function StatCard({
  label,
  value,
  hint,
  icon,
  accent = 'forest',
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: React.ReactNode;
  accent?: 'forest' | 'gold' | 'emerald';
}) {
  const accentBg =
    accent === 'gold'
      ? 'bg-gold-soft text-gold-harvest'
      : accent === 'emerald'
        ? 'bg-emerald-mist text-emerald-leaf'
        : 'bg-forest-deep/10 text-forest-deep';

  return (
    <div className="rounded-2xl border border-soil-border bg-white p-5 shadow-card transition-shadow hover:shadow-elevated">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
            {label}
          </p>
          <p className="mt-2 font-display text-2xl font-bold text-soil-charcoal tabular-nums">
            {value}
          </p>
          {hint && <p className="mt-1 text-xs text-soil-muted">{hint}</p>}
        </div>
        {icon && (
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${accentBg}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 rounded-2xl border border-soil-border bg-white p-6" role="status" aria-label="Loading">
      <div className="h-5 w-1/3 animate-pulse rounded-md bg-parchment-muted" />
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-4 w-full animate-pulse rounded-md bg-parchment-muted"
          style={{ width: `${95 - i * 11}%` }}
        />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-soil-border bg-white/70 px-6 py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-mist text-emerald-leaf">
        <Inbox className="h-6 w-6" />
      </div>
      <h3 className="mt-4 font-display text-base font-bold text-soil-charcoal">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-soil-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorAlert({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900"
    >
      <div className="flex items-center gap-2.5">
        <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
        <span>{message}</span>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-100"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      )}
    </div>
  );
}

export function SourceModeBadge({ mode }: { mode: DataSourceMode }) {
  if (mode === 'live_api') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-border bg-emerald-mist px-2.5 py-0.5 text-xs font-semibold text-emerald-leaf">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-leaf" />
        Live FastAPI Inference
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-gold-soft px-2.5 py-0.5 text-xs font-semibold text-amber-900">
      <FlaskConical className="h-3.5 w-3.5 text-gold-harvest" />
      Preview Mode — Synthetic Demo Data
    </span>
  );
}
