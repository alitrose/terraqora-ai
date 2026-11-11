import React, { useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ImagePlus,
  Leaf,
  ShieldAlert,
  Trash2,
} from 'lucide-react';
import { mlService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { useToast } from '../context/ToastContext';
import type { DiseaseDetectionResponse } from '../types/api';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export function PlantDiseaseDetectionPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cropHint, setCropHint] = useState('Tomato');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiseaseDetectionResponse | null>(null);
  const { notify } = useToast();

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
      const detection = await mlService.detectDisease(selectedFile, cropHint);
      setResult(detection);
      notify('Leaf image screening complete', 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Image analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      title="Plant Disease Detection"
      subtitle="Upload crop leaf photos for automated quality checks, CNN screening, and treatment guidance."
    >
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Upload & Preview Column */}
        <form
          onSubmit={handleAnalyze}
          className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
        >
          <h2 className="font-display text-base font-bold text-forest-deep">
            Leaf Image Upload
          </h2>

          {error && <ErrorAlert message={error} />}

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
              {['Tomato', 'Potato', 'Maize / Corn', 'Rice', 'Apple', 'Grape', 'Pepper'].map(
                (c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                )
              )}
            </select>
          </div>

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
                  className="mx-auto max-h-60 rounded-xl border border-soil-border object-contain bg-white"
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

          <button
            type="submit"
            disabled={loading || !selectedFile}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-3 text-sm font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-50"
          >
            <Leaf className="h-4 w-4 text-gold-bright" />
            {loading ? 'Analyzing Leaf Tissue...' : 'Detect Plant Disease'}
          </button>
        </form>

        {/* Results Panel */}
        <div className="space-y-6 lg:col-span-7">
          {loading ? (
            <LoadingSkeleton rows={6} />
          ) : !result ? (
            <EmptyState
              title="No leaf image screened yet"
              description="Upload a clear leaf photograph on the left. Low-confidence outputs (< 65%) automatically trigger an uncertain-result caution notice."
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
                    Crop: {result.crop_name} · Label: <code>{result.predicted_label}</code>
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
                    <p className="font-bold">Uncertain Classification Warning (Low Confidence)</p>
                    <p className="mt-1 leading-relaxed">{result.uncertainty_reason}</p>
                  </div>
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-soil-border bg-parchment p-4">
                  <p className="text-xs text-soil-muted">Model Confidence</p>
                  <p className="mt-1 font-mono text-2xl font-bold text-forest-deep">
                    {(result.confidence * 100).toFixed(1)}%
                  </p>
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
                  <p className="text-xs text-soil-muted">Health Status</p>
                  <div className="mt-1.5 flex items-center gap-2">
                    {result.is_healthy ? (
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
                    Management & Treatment
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

              <p className="text-[11px] text-soil-muted">
                Pipeline: {result.model_version}
              </p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
