import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  History,
  ImagePlus,
  Info,
  Leaf,
  ShieldAlert,
  Trash2,
} from 'lucide-react';
import { mlService, profileService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { useToast } from '../context/ToastContext';
import type { DiseaseDetectionResponse, Farm } from '../types/api';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

const SUPPORTED_CROP_HINTS = [
  'Auto-detect',
  'Tomato',
  'Potato',
  'Corn (Maize)',
  'Apple',
  'Grape',
  'Bell Pepper',
  'Peach',
  'Cherry',
  'Strawberry',
  'Orange (Citrus)',
  'Squash',
  'Soybean',
  'Blueberry',
  'Raspberry',
];

const UNSUPPORTED_CROP_OPTIONS = ['Rice', 'Wheat', 'Cotton', 'Sugarcane', 'Coconut'];

export function PlantDiseaseDetectionPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cropHint, setCropHint] = useState('Tomato');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiseaseDetectionResponse | null>(null);
  const [history, setHistory] = useState<DiseaseDetectionResponse[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const { notify } = useToast();

  useEffect(() => {
    let active = true;
    Promise.all([
      profileService.listFarms().catch(() => [] as Farm[]),
      mlService.getDiseaseHistory().catch(() => [] as DiseaseDetectionResponse[]),
    ]).then(([farmRows, histRows]) => {
      if (!active) return;
      setFarms(farmRows);
      setHistory(histRows);
      setHistoryLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const handleFarmChange = (farmId: string) => {
    setSelectedFarmId(farmId);
    const chosen = farms.find((f) => f.id === farmId);
    if (chosen?.primary_crop) {
      setCropHint(chosen.primary_crop);
    }
  };

  const handleFileChange = (file: File | undefined) => {
    setError(null);
    setResult(null);
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Unsupported file format. Upload a JPG, PNG, or WebP leaf image.');
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      setError('Image exceeds the 5 MB limit. Please upload a smaller leaf photograph.');
      return;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const clearSelection = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a leaf image before running detection.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const effectiveHint = cropHint === 'Auto-detect' ? '' : cropHint;
      const detection = await mlService.detectDisease(
        selectedFile,
        effectiveHint,
        selectedFarmId || null
      );
      setResult(detection);
      setHistory((prev) => [detection, ...prev.filter((item) => item.id !== detection.id)].slice(0, 10));
      notify(
        detection.is_uncertain
          ? 'Screening flagged uncertain — verify sample cleanly'
          : 'Leaf image screening complete',
        detection.is_uncertain ? 'info' : 'success'
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Image analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const isUnsupportedSelected = UNSUPPORTED_CROP_OPTIONS.some(
    (c) => c.toLowerCase() === cropHint.trim().toLowerCase()
  );

  return (
    <AppShell
      title="Plant Disease Detection"
      subtitle="Upload single-leaf photographs for calibrated CNN screening, abstention safety checks, and non-dosage IPM guidance."
    >
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Upload & Preview Column */}
        <form
          onSubmit={handleAnalyze}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-display text-base font-bold text-forest-deep">
              Leaf Image Screening
            </h2>
            <span className="rounded-full border border-emerald-border bg-emerald-mist px-2.5 py-0.5 text-[11px] font-semibold text-forest-deep">
              14 PlantVillage Crops
            </span>
          </div>

          {error && <ErrorAlert message={error} />}

          {farms.length > 0 && (
            <div>
              <label
                htmlFor="disease-farm-select"
                className="block text-xs font-semibold text-soil-charcoal"
              >
                Link Saved Farm Plot (Optional)
              </label>
              <select
                id="disease-farm-select"
                value={selectedFarmId}
                onChange={(e) => handleFarmChange(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
              >
                <option value="">Standalone scan (no plot linked)</option>
                {farms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.district || f.state}
                    {f.primary_crop ? ` · ${f.primary_crop}` : ''})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label htmlFor="disease-crop-hint" className="block text-xs font-semibold text-soil-charcoal">
              Expected Crop Species (Optional Context)
            </label>
            <select
              id="disease-crop-hint"
              value={cropHint}
              onChange={(e) => setCropHint(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
            >
              <optgroup label="Supported PlantVillage Species (38 Classes)">
                {SUPPORTED_CROP_HINTS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Unsupported Field Crops (Triggers Abstention Notice)">
                {UNSUPPORTED_CROP_OPTIONS.map((c) => (
                  <option key={c} value={c}>
                    {c} (Outside Vision Catalog)
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          {isUnsupportedSelected && (
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
              <p>
                <strong>{cropHint}</strong> is not included in the PlantVillage 38-class dataset. Running a scan will explicitly flag an out-of-scope uncertainty warning rather than guessing a diagnosis.
              </p>
            </div>
          )}

          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFileChange(e.dataTransfer.files?.[0]);
            }}
            className="rounded-2xl border-2 border-dashed border-emerald-border bg-parchment/60 p-5 text-center transition-colors hover:border-emerald-leaf"
          >
            <input
              ref={fileInputRef}
              id="leaf-file-input"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => handleFileChange(e.target.files?.[0])}
              className="sr-only"
            />

            {previewUrl && selectedFile ? (
              <div className="space-y-3">
                <img
                  src={previewUrl}
                  alt="Uploaded leaf preview"
                  className="mx-auto max-h-60 rounded-xl border border-soil-border bg-white object-contain"
                />
                <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2 text-xs">
                  <span className="truncate font-medium text-soil-charcoal">
                    {selectedFile.name}
                  </span>
                  <span className="shrink-0 font-mono text-soil-muted">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </span>
                </div>
                <button
                  type="button"
                  onClick={clearSelection}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-700 hover:underline"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove Image
                </button>
              </div>
            ) : (
              <label
                htmlFor="leaf-file-input"
                className="flex cursor-pointer flex-col items-center py-6"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-mist text-forest-deep">
                  <ImagePlus className="h-6 w-6" />
                </div>
                <p className="mt-3 text-sm font-semibold text-forest-deep">
                  Click to choose or drag & drop leaf image
                </p>
                <p className="mt-1 text-xs text-soil-muted">
                  Supports JPG, PNG, WebP · Maximum 5 MB · Clear single-leaf daylight view
                </p>
              </label>
            )}
          </div>

          <div className="rounded-xl border border-soil-border bg-parchment/60 p-3 text-[11px] leading-relaxed text-soil-muted">
            <strong className="text-soil-charcoal">Calibration Guardrail:</strong> Outputs below{' '}
            <span className="font-mono">65%</span> calibrated confidence, with narrow top-2 margin (
            <span className="font-mono">&lt; 15%</span>), blank texture, or unsupported crop hints
            automatically abstain from diagnosis.
          </div>

          <button
            type="submit"
            disabled={loading || !selectedFile}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-3 text-sm font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-50"
          >
            <Leaf className="h-4 w-4 text-gold-bright" />
            {loading ? 'Analyzing Leaf Tissue...' : 'Detect Plant Disease'}
          </button>
        </form>

        {/* Results & History Column */}
        <div className="space-y-6 lg:col-span-7">
          {loading ? (
            <LoadingSkeleton rows={6} />
          ) : !result ? (
            <EmptyState
              title="No leaf image screened yet"
              description="Upload a clear single-leaf photograph on the left. Low-confidence outputs (< 65%) or unsupported crops automatically trigger an uncertain screening warning."
            />
          ) : (
            <div className="space-y-5 rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-soil-border pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                    Pathology Screening Output
                  </p>
                  <h3 className="font-display text-xl font-bold text-forest-deep">
                    {result.disease_name}
                  </h3>
                  <p className="text-xs text-soil-muted">
                    Crop: {result.crop_name} · Class ID: <code>{result.predicted_label}</code>
                  </p>
                </div>
                <SourceModeBadge mode={result.source_mode} />
              </div>

              {result.is_uncertain && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950"
                >
                  <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
                  <div>
                    <p className="font-bold">
                      Uncertain Screening Notice — Abstaining from Definitive Diagnosis
                    </p>
                    <p className="mt-1 leading-relaxed">{result.uncertainty_reason}</p>
                  </div>
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-soil-border bg-parchment p-4">
                  <p className="text-xs text-soil-muted">Calibrated Confidence</p>
                  <div className="mt-1 flex items-baseline justify-between">
                    <p className="font-mono text-2xl font-bold text-forest-deep">
                      {(result.confidence * 100).toFixed(1)}%
                    </p>
                    {result.top2_margin !== undefined && result.top2_margin !== null && (
                      <span className="font-mono text-[11px] text-soil-muted">
                        Margin: {(result.top2_margin * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-soil-border">
                    <div
                      className={`h-full rounded-full ${
                        result.is_uncertain ? 'bg-gold-harvest' : 'bg-emerald-leaf'
                      }`}
                      style={{ width: `${Math.round(result.confidence * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-soil-border bg-parchment p-4">
                  <p className="text-xs text-soil-muted">Screening Status</p>
                  <div className="mt-1.5 flex items-center gap-2">
                    {result.is_uncertain ? (
                      <>
                        <ShieldAlert className="h-5 w-5 text-amber-700" />
                        <span className="font-display text-lg font-bold text-amber-900">
                          Verification Needed
                        </span>
                      </>
                    ) : result.is_healthy ? (
                      <>
                        <CheckCircle2 className="h-5 w-5 text-emerald-leaf" />
                        <span className="font-display text-lg font-bold text-emerald-leaf">
                          Healthy Foliage
                        </span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="h-5 w-5 text-gold-harvest" />
                        <span className="font-display text-lg font-bold text-soil-charcoal">
                          Attention Advised
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Top-3 Class Probabilities */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                  Top Candidate Classes
                </h4>
                <div className="mt-2.5 space-y-2">
                  {result.top_predictions.map((cand) => (
                    <div key={cand.label} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-soil-charcoal">{cand.label}</span>
                        <span className="font-mono text-soil-muted">
                          {(cand.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-parchment-muted">
                        <div
                          className="h-full rounded-full bg-forest-deep"
                          style={{ width: `${Math.round(cand.confidence * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Treatment & Prevention */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-emerald-border bg-emerald-mist/50 p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-forest-deep">
                    Management & Field Guidance
                  </h4>
                  <p className="mt-1.5 text-xs leading-relaxed text-soil-charcoal">
                    {result.treatment_summary}
                  </p>
                </div>
                <div className="rounded-xl border border-soil-border bg-parchment p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-forest-deep">
                    Prevention Best Practices
                  </h4>
                  <p className="mt-1.5 text-xs leading-relaxed text-soil-charcoal">
                    {result.prevention_notes}
                  </p>
                </div>
              </div>

              {result.next_steps && result.next_steps.length > 0 && (
                <div className="rounded-xl border border-soil-border bg-white p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-forest-deep">
                    Recommended Next Steps
                  </h4>
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-soil-charcoal">
                    {result.next_steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(result.supported_scope_note || (result.limitations && result.limitations.length > 0)) && (
                <div className="flex items-start gap-2.5 rounded-xl border border-soil-border bg-parchment/70 p-3.5 text-[11px] leading-relaxed text-soil-muted">
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-forest-deep" />
                  <div className="space-y-1">
                    {result.supported_scope_note && <p>{result.supported_scope_note}</p>}
                    {result.limitations?.map((lim) => (
                      <p key={lim}>• {lim}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-soil-border pt-3">
                <p className="text-[11px] text-soil-muted">
                  Pipeline: {result.model_version} · File: {result.image_filename}
                </p>
                <Link
                  to="/assistant"
                  className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-border bg-emerald-mist/60 px-3 py-1.5 text-xs font-semibold text-forest-deep transition-colors hover:bg-emerald-mist"
                >
                  <Bot className="h-3.5 w-3.5" />
                  Discuss Screening in AI Assistant
                </Link>
              </div>
            </div>
          )}

          {/* Saved Screening History */}
          <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-forest-deep" />
                <h3 className="font-display text-sm font-bold text-forest-deep">
                  Recent Saved Leaf Screenings
                </h3>
              </div>
              <span className="text-[11px] text-soil-muted">{history.length} records</span>
            </div>

            {historyLoading ? (
              <p className="mt-3 text-xs text-soil-muted">Loading screening history...</p>
            ) : history.length === 0 ? (
              <p className="mt-3 text-xs text-soil-muted">
                No saved scans yet. Run a leaf check on the left to record it to your farm history.
              </p>
            ) : (
              <div className="mt-3 divide-y divide-soil-border">
                {history.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setResult(item)}
                    className="flex w-full items-center justify-between gap-3 py-2.5 text-left transition-colors hover:bg-parchment/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-forest-deep">
                        {item.disease_name}
                      </p>
                      <p className="truncate text-[11px] text-soil-muted">
                        {item.crop_name} · {item.image_filename} ·{' '}
                        {new Date(item.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 font-mono text-[11px] font-semibold ${
                        item.is_uncertain
                          ? 'bg-amber-100 text-amber-900'
                          : item.is_healthy
                            ? 'bg-emerald-mist text-forest-deep'
                            : 'bg-parchment-muted text-soil-charcoal'
                      }`}
                    >
                      {(item.confidence * 100).toFixed(1)}%
                      {item.is_uncertain ? ' · Uncertain' : ''}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
