"use client";

import { useCallback, useState } from "react";
import { API_BASE, getApiKey } from "@/utils/api";
import Link from "next/link";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";

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
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 animate-fade-in">
      <PageHeader title="Batch Intake" subtitle="Upload a ZIP archive to create multiple assessments at once" />

      {phase === "idle" && (
        <div className="space-y-6">
          <div className="rounded-xl border-2 border-dashed border-border bg-surface-card p-10 text-center">
            <input type="file" accept=".zip" className="hidden" id="zip-input" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <label htmlFor="zip-input" className="cursor-pointer">
              <svg className="mx-auto h-10 w-10 text-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
              <p className="mt-3 text-sm font-medium text-text-primary">{file ? file.name : "Click to select ZIP file"}</p>
              <p className="mt-1 text-xs text-text-tertiary">ZIP must contain folders named per vehicle, each with images named left_side_profile.jpg, right_side_profile.jpg, rear_view.jpg, etc.</p>
            </label>
          </div>

          <Card className="text-xs space-y-1 leading-relaxed">
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
          </Card>

          <div className="flex justify-center">
            <button
              onClick={handleUpload}
              disabled={!file}
              className="inline-flex items-center gap-2 rounded-xl bg-brand px-8 py-3 text-sm font-medium text-white transition-all hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40"
            >
              Upload & Process Batch
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
          <Card className="border-danger/30">
            <p className="text-xs text-danger">{error}</p>
          </Card>
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
            <Badge variant="success" size="sm">Batch {result.batch_id.slice(0, 8)}…</Badge>
            <span className="text-sm text-text-secondary">{result.jobs.filter((j) => j.status === "created").length} / {result.total} succeeded</span>
            <Link href={`/batch/${result.batch_id}`} className="ml-auto text-sm font-medium text-brand hover:text-brand-dark transition-colors">View Dashboard →</Link>
          </div>

          <Card padding="none">
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
                      <Badge variant={j.status === "created" ? "success" : j.status === "validation_failed" ? "danger" : "warning"} size="sm">{j.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-text-tertiary font-mono">{j.intake_id?.slice(0, 8) ?? "\u2014"}</td>
                    <td className="px-4 py-3 text-xs text-danger">{j.error ?? "\u2014"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="flex justify-center gap-3">
            <button onClick={() => { setPhase("idle"); setFile(null); setResult(null); }} className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors">New Batch</button>
            <Link href="/history" className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors">View History</Link>
          </div>
        </div>
      )}
    </div>
  );
}
