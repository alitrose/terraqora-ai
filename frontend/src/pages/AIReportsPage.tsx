import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  Layers,
  Leaf,
  Printer,
  Sparkles,
  Sprout,
  SunMedium,
} from 'lucide-react';
import { API_BASE_URL, getStoredToken } from '../api/client';
import { profileService, reportsService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  CROP_SEASONS,
  INDIAN_STATES,
  LANGUAGE_OPTIONS,
  YIELD_CROPS,
} from '../data/agriCatalog';
import type {
  Farm,
  GeneratedReport,
  ReportType,
  SupportedLanguage,
} from '../types/api';

const REPORT_TYPE_LABELS: Record<ReportType, { label: string; icon: typeof FileText }> = {
  combined_intelligence: {
    label: 'Combined Farm Intelligence Audit',
    icon: Layers,
  },
  crop_yield: {
    label: 'Crop Yield Prediction Report',
    icon: FileSpreadsheet,
  },
  crop_recommendation: {
    label: 'Crop Suitability & Recommendation',
    icon: Sprout,
  },
  fertilizer_recommendation: {
    label: 'Fertilizer & Soil Nutrient Plan',
    icon: Sparkles,
  },
  disease_detection: {
    label: 'Plant Disease Screening Report',
    icon: Leaf,
  },
  weather_irrigation: {
    label: 'Weather & Irrigation Advisory',
    icon: SunMedium,
  },
};

export function AIReportsPage() {
  const { user, isDemoSession } = useAuth();
  const { notify } = useToast();

  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const [reportType, setReportType] = useState<ReportType>('combined_intelligence');
  const [title, setTitle] = useState('Seasonal Acreage & Input Advisory Report');
  const [farmId, setFarmId] = useState('');
  const [crop, setCrop] = useState('Rice');
  const [state, setState] = useState('Tamil Nadu');
  const [season, setSeason] = useState('Kharif');
  const [area, setArea] = useState(4.0);
  const [predictedYield, setPredictedYield] = useState(3.65);
  const [fertilizerRec, setFertilizerRec] = useState(
    'Split Urea + DAP basal application (verify via local Soil Health Card)'
  );
  const [irrigationSummary, setIrrigationSummary] = useState(
    'Moderate ~18 mm supplemental irrigation over 7 days (weather-estimated)'
  );
  const [language, setLanguage] = useState<SupportedLanguage>(
    user?.preferred_language || 'en'
  );

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const [repList, farmList] = await Promise.all([
        reportsService.list(),
        profileService.listFarms(),
      ]);
      setReports(repList);
      setFarms(farmList);
      if (repList.length > 0) {
        setSelectedReportId(repList[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleSelectFarm = (nextFarmId: string) => {
    setFarmId(nextFarmId);
    const chosen = farms.find((f) => f.id === nextFarmId);
    if (chosen) {
      setState(chosen.state);
      setArea(chosen.area_hectares);
      if (chosen.primary_crop) setCrop(chosen.primary_crop);
      setTitle(`${chosen.name} — ${chosen.primary_crop || crop} Advisory Report`);
    }
  };

  const handleReportTypeChange = (nextType: ReportType) => {
    setReportType(nextType);
    const chosenFarm = farms.find((f) => f.id === farmId);
    const farmPrefix = chosenFarm ? `${chosenFarm.name} — ` : '';
    switch (nextType) {
      case 'crop_yield':
        setTitle(`${farmPrefix}${crop} Yield Forecast Report`);
        break;
      case 'crop_recommendation':
        setTitle(`${farmPrefix}Crop Suitability & Diversity Assessment`);
        break;
      case 'fertilizer_recommendation':
        setTitle(`${farmPrefix}${crop} Nutrient & Fertilizer Prescription Plan`);
        break;
      case 'disease_detection':
        setTitle(`${farmPrefix}${crop} Leaf Pathology Screening Report`);
        break;
      case 'weather_irrigation':
        setTitle(`${farmPrefix}7-Day Microclimate & Irrigation Advisory`);
        break;
      case 'combined_intelligence':
      default:
        setTitle(`${farmPrefix}${crop || 'Acreage'} Full Farm Intelligence Audit`);
        break;
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (title.trim().length < 4) {
      setError('Report title must be at least 4 characters long.');
      return;
    }
    if (area <= 0) {
      setError('Area must be greater than 0 hectares.');
      return;
    }
    if (predictedYield < 0) {
      setError('Predicted yield cannot be negative.');
      return;
    }

    const yieldUnit = crop === 'Coconut' ? 'nuts/hectare' : 'tonnes/hectare';
    setCreating(true);
    try {
      const created = await reportsService.create({
        title: title.trim(),
        report_type: reportType,
        farm_id: farmId || null,
        crop,
        state,
        season,
        area_hectares: area,
        predicted_yield: predictedYield,
        yield_unit: yieldUnit,
        fertilizer_recommendation: fertilizerRec.trim(),
        irrigation_summary: irrigationSummary.trim(),
        language,
      });
      setReports((prev) => [created, ...prev]);
      setSelectedReportId(created.id);
      notify('AI executive report generated with PDF download ready', 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create report.');
    } finally {
      setCreating(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleServerPdfDownload = async (report: GeneratedReport) => {
    setDownloading(true);
    const token = getStoredToken();
    try {
      const res = await fetch(`${API_BASE_URL}/reports/${report.id}/download`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        throw new Error(`Download failed with status ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = report.pdf_filename || `TerraQora_Report_${report.id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notify('Official publication-quality PDF report downloaded', 'success');
    } catch {
      if (isDemoSession || report.source_mode === 'demo_preview') {
        notify('Demo session: opening browser print export instead.', 'info');
        window.print();
      } else {
        notify('Could not stream PDF from server. Using browser print export instead.', 'info');
        window.print();
      }
    } finally {
      setDownloading(false);
    }
  };

  const activeReport =
    reports.find((r) => r.id === selectedReportId) || reports[0] || null;

  return (
    <AppShell
      title="AI Farm Reports & PDF Export"
      subtitle="Compile crop forecasts, nutrient prescriptions, and microclimate advisories into executive publication-quality PDF reports."
    >
      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={loadReports} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Builder Form */}
        <form
          onSubmit={handleGenerate}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <div className="flex items-center justify-between">
            <h2 className="font-display text-base font-bold text-forest-deep">
              Report Architect
            </h2>
            <span className="rounded-full bg-forest-deep/10 px-2.5 py-0.5 text-[11px] font-bold text-forest-deep">
              ReportLab Engine
            </span>
          </div>

          {/* Report Type Selector */}
          <div>
            <label htmlFor="rep-type" className="block text-xs font-semibold text-soil-charcoal">
              Report Category
            </label>
            <select
              id="rep-type"
              value={reportType}
              onChange={(e) => handleReportTypeChange(e.target.value as ReportType)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-xs font-bold text-forest-deep focus:border-emerald-leaf focus:bg-white focus:outline-none"
            >
              {(Object.keys(REPORT_TYPE_LABELS) as ReportType[]).map((t) => (
                <option key={t} value={t}>
                  {REPORT_TYPE_LABELS[t].label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="rep-title" className="block text-xs font-semibold text-soil-charcoal">
              Report Title
            </label>
            <input
              id="rep-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
            />
          </div>

          {farms.length > 0 && (
            <div>
              <label htmlFor="rep-farm" className="block text-xs font-semibold text-soil-charcoal">
                Link Registered Farm (Auto-fills Acreage)
              </label>
              <select
                id="rep-farm"
                value={farmId}
                onChange={(e) => handleSelectFarm(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                <option value="">Custom Plot / Manual Inputs</option>
                {farms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.area_hectares} ha · {f.state})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="rep-crop" className="block text-xs font-semibold text-soil-charcoal">
                Crop
              </label>
              <select
                id="rep-crop"
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                {YIELD_CROPS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="rep-state" className="block text-xs font-semibold text-soil-charcoal">
                State
              </label>
              <select
                id="rep-state"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                {INDIAN_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="rep-season" className="block text-xs font-semibold text-soil-charcoal">
                Season
              </label>
              <select
                id="rep-season"
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                {CROP_SEASONS.map((se) => (
                  <option key={se} value={se}>
                    {se}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="rep-lang" className="block text-xs font-semibold text-soil-charcoal">
                Summary Language
              </label>
              <select
                id="rep-lang"
                value={language}
                onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                {LANGUAGE_OPTIONS.map((opt) => (
                  <option key={opt.code} value={opt.code}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="rep-area" className="block text-xs font-semibold text-soil-charcoal">
                Area (ha)
              </label>
              <input
                id="rep-area"
                type="number"
                min={0.1}
                step={0.1}
                value={area}
                onChange={(e) => setArea(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label htmlFor="rep-yield" className="block text-xs font-semibold text-soil-charcoal">
                Predicted Yield ({crop === 'Coconut' ? 'nuts/ha' : 't/ha'})
              </label>
              <input
                id="rep-yield"
                type="number"
                min={0}
                step={0.05}
                value={predictedYield}
                onChange={(e) => setPredictedYield(Number(e.target.value))}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
              />
            </div>
          </div>

          <div>
            <label htmlFor="rep-fert" className="block text-xs font-semibold text-soil-charcoal">
              Fertilizer Plan Summary
            </label>
            <input
              id="rep-fert"
              type="text"
              value={fertilizerRec}
              onChange={(e) => setFertilizerRec(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label htmlFor="rep-irr" className="block text-xs font-semibold text-soil-charcoal">
              Weather & Irrigation Summary
            </label>
            <input
              id="rep-irr"
              type="text"
              value={irrigationSummary}
              onChange={(e) => setIrrigationSummary(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={creating}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-3 text-sm font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-60"
          >
            <Sparkles className="h-4 w-4 text-gold-bright" />
            {creating ? 'Compiling Report & PDF...' : 'Generate AI Report'}
          </button>
        </form>

        {/* Saved Reports & Executive Document Preview */}
        <div className="space-y-5 lg:col-span-7">
          {loading ? (
            <LoadingSkeleton rows={6} />
          ) : reports.length === 0 ? (
            <EmptyState
              title="No saved reports yet"
              description="Fill in the report builder on the left to compile a structured TerraQora AI farm report."
            />
          ) : (
            <>
              {/* Saved Reports Selector Strip */}
              <div className="flex flex-wrap items-center gap-2">
                {reports.map((rep) => {
                  const active = rep.id === activeReport?.id;
                  const repTypeKey = (rep.report_type || 'combined_intelligence') as ReportType;
                  const TypeIcon = REPORT_TYPE_LABELS[repTypeKey]?.icon || FileText;
                  return (
                    <button
                      key={rep.id}
                      type="button"
                      onClick={() => setSelectedReportId(rep.id)}
                      className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-colors ${
                        active
                          ? 'border-forest-deep bg-forest-deep text-white shadow-sm'
                          : 'border-soil-border bg-white text-soil-charcoal hover:bg-parchment'
                      }`}
                    >
                      <TypeIcon className="h-3.5 w-3.5" />
                      <span className="max-w-[180px] truncate">{rep.title}</span>
                    </button>
                  );
                })}
              </div>

              {activeReport && (
                <article className="space-y-5 rounded-2xl border border-soil-border bg-white p-6 shadow-card">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-soil-border pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-leaf">
                          TerraQora AI · Agronomic Intelligence Report
                        </p>
                        <span className="rounded-full bg-forest-deep/10 px-2 py-0.5 text-[10px] font-bold text-forest-deep uppercase">
                          {activeReport.report_type?.replace(/_/g, ' ') || 'Combined Report'}
                        </span>
                      </div>
                      <h3 className="mt-1 font-display text-xl font-bold text-forest-deep">
                        {activeReport.title}
                      </h3>
                      <p className="mt-1 text-xs text-soil-muted">
                        File: <code>{activeReport.pdf_filename}</code> · Generated{' '}
                        {new Date(activeReport.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <SourceModeBadge mode={activeReport.source_mode} />
                  </div>

                  {/* Parameter Summary Grid */}
                  <div className="grid gap-3 sm:grid-cols-4">
                    <div className="rounded-xl border border-soil-border bg-parchment p-3">
                      <p className="text-[11px] text-soil-muted">Crop</p>
                      <p className="font-display text-sm font-bold text-forest-deep">
                        {activeReport.crop}
                      </p>
                    </div>
                    <div className="rounded-xl border border-soil-border bg-parchment p-3">
                      <p className="text-[11px] text-soil-muted">State & Season</p>
                      <p className="font-display text-sm font-bold text-forest-deep">
                        {activeReport.state} ({activeReport.season})
                      </p>
                    </div>
                    <div className="rounded-xl border border-soil-border bg-parchment p-3">
                      <p className="text-[11px] text-soil-muted">Acreage</p>
                      <p className="font-mono text-sm font-bold text-soil-charcoal">
                        {activeReport.area_hectares} ha
                      </p>
                    </div>
                    <div className="rounded-xl border border-emerald-border bg-emerald-mist/60 p-3">
                      <p className="text-[11px] text-emerald-leaf">Predicted Yield</p>
                      <p className="font-mono text-sm font-bold text-forest-deep">
                        {activeReport.predicted_yield} {activeReport.yield_unit}
                      </p>
                    </div>
                  </div>

                  {/* Observations */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-soil-muted">
                      Key Agricultural Observations
                    </h4>
                    <ul className="mt-2 space-y-1.5 text-sm text-soil-charcoal">
                      {activeReport.agricultural_observations.map((obs) => (
                        <li key={obs} className="flex items-start gap-2">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-leaf" />
                          <span>{obs}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Nutrient & Irrigation Block */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-xl border border-soil-border bg-parchment/70 p-4">
                      <p className="text-xs font-bold uppercase text-forest-deep">
                        Nutrient Recommendation
                      </p>
                      <p className="mt-1 text-xs leading-relaxed text-soil-charcoal">
                        {activeReport.fertilizer_recommendation}
                      </p>
                    </div>
                    <div className="rounded-xl border border-soil-border bg-parchment/70 p-4">
                      <p className="text-xs font-bold uppercase text-forest-deep">
                        Irrigation Guidance
                      </p>
                      <p className="mt-1 text-xs leading-relaxed text-soil-charcoal">
                        {activeReport.irrigation_summary}
                      </p>
                    </div>
                  </div>

                  {/* AI Executive Summary & Explanation */}
                  <div className="rounded-xl border border-emerald-border bg-emerald-mist/50 p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-forest-deep">
                      AI Executive Summary
                    </p>
                    <p className="mt-1.5 text-sm leading-relaxed text-soil-charcoal">
                      {activeReport.ai_summary}
                    </p>
                    <p className="mt-2 text-xs text-soil-muted">
                      <strong>Methodology Note:</strong> {activeReport.model_explanation}
                    </p>
                  </div>

                  {/* Uncertainty & Safety Callout */}
                  <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700" />
                    <span>
                      <strong>Agronomic Decision-Support Notice:</strong> This AI-generated report is
                      intended for advisory and field planning purposes only. Real-world crop yields
                      and nutrient uptake are influenced by microclimatic fluctuations, soil compaction,
                      water salinity, and pest outbreaks. Conduct manual field moisture checks and soil
                      testing before executing major operational interventions.
                    </span>
                  </div>

                  {/* Export Action Row */}
                  <div className="flex flex-wrap items-center justify-end gap-2.5 border-t border-soil-border pt-4">
                    <button
                      type="button"
                      onClick={handlePrint}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-soil-border bg-white px-4 py-2 text-xs font-semibold text-forest-deep hover:bg-parchment"
                    >
                      <Printer className="h-3.5 w-3.5" />
                      Print / Save as PDF
                    </button>
                    <button
                      type="button"
                      disabled={downloading}
                      onClick={() => handleServerPdfDownload(activeReport)}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-forest-deep px-4 py-2 text-xs font-semibold text-white hover:bg-forest-hover disabled:opacity-60"
                    >
                      <Download className="h-3.5 w-3.5 text-gold-bright" />
                      {downloading ? 'Preparing PDF...' : 'Download Server PDF'}
                    </button>
                  </div>
                </article>
              )}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
