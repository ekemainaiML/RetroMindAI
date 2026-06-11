"use client";

import { useCallback, useState } from "react";
import { API_BASE, getApiKey } from "@/utils/api";
import Link from "next/link";

interface BatchJobEntry {
  vehicle_name: string;
  intake_id: string | null;
  status: string;
  error: string | null;
}

interface BatchResponse {
  batch_id: string;
  total: number;
  jobs: BatchJobEntry[];
}

type Phase = "idle" | "uploading" | "done" | "error";

export default function BatchPage() {
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setPhase("uploading");
    setError(null);

    try {
      const fd = new FormData();
      fd.append("batch_file", file);

      const key = getApiKey();
      const headers: Record<string, string> = {};
      if (key) headers["X-API-Key"] = key;

      const res = await fetch(`${API_BASE}/batch/intake`, {
        method: "POST",
        headers,
        body: fd,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`Upload failed (${res.status}): ${text}`);
      }

      const data: BatchResponse = await res.json();
      setResult(data);
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setPhase("error");
    }
  }, [file]);

  return (
    <div className="flex flex-1 flex-col items-center px-4 py-12">
      <div className="w-full max-w-3xl">
        <div className="mb-8 text-center animate-fade-in">
          <h1 className="text-3xl font-bold tracking-tight text-text-primary">
            Batch Intake
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Upload a ZIP archive with per-vehicle folders to create multiple assessments at once
          </p>
        </div>

        {phase === "idle" && (
          <div className="space-y-6">
            <div className="rounded-xl border-2 border-dashed border-border bg-surface-card p-10 text-center">
              <input
                type="file"
                accept=".zip"
                className="hidden"
                id="zip-input"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <label
                htmlFor="zip-input"
                className="cursor-pointer"
              >
                <svg className="mx-auto h-10 w-10 text-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                <p className="mt-3 text-sm font-medium text-text-primary">
                  {file ? file.name : "Click to select ZIP file"}
                </p>
                <p className="mt-1 text-xs text-text-tertiary">
                  ZIP must contain folders named per vehicle, each with images named left_side_profile.jpg, right_side_profile.jpg, rear_view.jpg, etc.
                </p>
              </label>
            </div>

            <div className="rounded-xl border border-border bg-surface-card p-4 text-xs text-text-secondary space-y-1 leading-relaxed">
              <p className="font-medium text-text-primary">ZIP Structure Example:</p>
              <pre className="bg-surface p-3 rounded-lg text-[11px] leading-relaxed">
{`vehicle_01/
  left_side_profile.jpg
  right_side_profile.jpg
  rear_view.jpg
  front_view.jpg
  engine_bay.jpg
  underbody.jpg
vehicle_02/
  left_side_profile.jpg
  right_side_profile.jpg
  rear_view.jpg`}
              </pre>
            </div>

            <div className="flex justify-center">
              <button
                onClick={handleUpload}
                disabled={!file}
                className="inline-flex items-center gap-2 rounded-xl bg-brand px-8 py-3 text-sm font-medium text-white transition-all hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40"
              >
                Upload &amp; Process Batch
              </button>
            </div>
          </div>
        )}

        {phase === "uploading" && (
          <div className="flex flex-col items-center gap-4 py-20">
            <span className="inline-block h-8 w-8 animate-spin rounded-full border-3 border-border border-t-brand" />
            <p className="text-sm text-text-secondary">Processing batch upload...</p>
          </div>
        )}

        {phase === "error" && (
          <div className="space-y-4">
            <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-200">
              {error}
            </div>
            <div className="flex justify-center">
              <button
                onClick={() => { setPhase("idle"); setFile(null); setResult(null); }}
                className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {phase === "done" && result && (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3">
              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900 dark:text-green-200">
                Batch {result.batch_id.slice(0, 8)}…
              </span>
              <span className="text-sm text-text-secondary">
                {result.jobs.filter((j) => j.status === "created").length} / {result.total} succeeded
              </span>
              <Link
                href={`/batch/${result.batch_id}`}
                className="ml-auto text-sm font-medium text-brand hover:text-brand-dark transition-colors"
              >
                View Dashboard →
              </Link>
            </div>

            <div className="overflow-hidden rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-surface-card text-left text-xs font-semibold text-text-secondary">
                    <th className="px-4 py-3">Vehicle</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Intake ID</th>
                    <th className="px-4 py-3">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {result.jobs.map((j, i) => (
                    <tr key={i} className="hover:bg-surface-hover transition-colors">
                      <td className="px-4 py-3 font-medium text-text-primary">{j.vehicle_name}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          j.status === "created"
                            ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200"
                            : j.status === "validation_failed"
                              ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                              : "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200"
                        }`}>
                          {j.status === "created" && <span className="h-1.5 w-1.5 rounded-full bg-green-500" />}
                          {j.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-text-tertiary font-mono">{j.intake_id?.slice(0, 8) ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-red-500">{j.error ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-center gap-3">
              <button
                onClick={() => { setPhase("idle"); setFile(null); setResult(null); }}
                className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
              >
                New Batch
              </button>
              <Link
                href="/history"
                className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
              >
                View History
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
