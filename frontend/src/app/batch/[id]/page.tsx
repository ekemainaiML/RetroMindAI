"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getApiKey } from "@/utils/api";
import Link from "next/link";

interface BatchJobEntry {
  vehicle_name: string;
  intake_id: string | null;
  status: string;
  error: string | null;
}

interface BatchDetail {
  batch_id: string;
  total: number;
  completed: number;
  failed: number;
  avg_feasibility: number | null;
  jobs: BatchJobEntry[];
}

export default function BatchDashboardPage() {
  const params = useParams();
  const batchId = params.id as string;
  const [data, setData] = useState<BatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBatch = useCallback(async () => {
    if (!batchId) return;
    setLoading(true);
    try {
      const key = getApiKey();
      const headers: Record<string, string> = {};
      if (key) headers["X-API-Key"] = key;
      const res = await fetch(
        `http://localhost:8000/api/v1/batch/${batchId}`,
        { headers }
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`Fetch failed (${res.status}): ${text}`);
      }
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    fetchBatch();
    const interval = setInterval(fetchBatch, 5000);
    return () => clearInterval(interval);
  }, [fetchBatch]);

  if (loading && !data) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <span className="inline-block h-8 w-8 animate-spin rounded-full border-3 border-border border-t-brand" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 px-4">
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
        <button
          onClick={fetchBatch}
          className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const succeeded = data.jobs.filter((j) => j.status === "created").length;
  const failed = data.jobs.filter((j) => j.status !== "created").length;
  const pct = data.total > 0 ? Math.round((succeeded / data.total) * 100) : 0;

  return (
    <div className="flex flex-1 flex-col items-center px-4 py-12">
      <div className="w-full max-w-3xl space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Batch Dashboard
            </h1>
            <p className="mt-1 text-xs text-text-tertiary font-mono">
              {data.batch_id}
            </p>
          </div>
          <Link
            href="/batch"
            className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-colors"
          >
            New Batch
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-border bg-surface-card p-4">
            <p className="text-xs font-medium text-text-tertiary">Total</p>
            <p className="mt-1 text-2xl font-bold text-text-primary">{data.total}</p>
          </div>
          <div className="rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
            <p className="text-xs font-medium text-green-600 dark:text-green-400">Created</p>
            <p className="mt-1 text-2xl font-bold text-green-700 dark:text-green-200">{succeeded}</p>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950">
            <p className="text-xs font-medium text-red-600 dark:text-red-400">Failed</p>
            <p className="mt-1 text-2xl font-bold text-red-700 dark:text-red-200">{failed}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface-card p-4">
            <p className="text-xs font-medium text-text-tertiary">Success Rate</p>
            <p className="mt-1 text-2xl font-bold text-text-primary">{pct}%</p>
          </div>
        </div>

        <div className="h-2 w-full rounded-full bg-zinc-200 dark:bg-zinc-700">
          <div
            className="h-2 rounded-full bg-brand transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>

        {data.avg_feasibility !== null && (
          <div className="rounded-xl border border-border bg-surface-card p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-primary">Average Feasibility</span>
              <span className="text-lg font-bold text-brand">{data.avg_feasibility}%</span>
            </div>
          </div>
        )}

        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-card text-left text-xs font-semibold text-text-secondary">
                <th className="px-4 py-3">Vehicle</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Intake</th>
                <th className="px-4 py-3">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.jobs.map((j, i) => (
                <tr key={i} className="hover:bg-surface-hover transition-colors">
                  <td className="px-4 py-3 font-medium text-text-primary">{j.vehicle_name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      j.status === "created"
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200"
                        : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                    }`}>
                      {j.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {j.intake_id ? (
                      <Link
                        href={`/?job_id=${j.intake_id}`}
                        className="text-xs font-mono text-brand hover:underline"
                      >
                        {j.intake_id.slice(0, 8)}…
                      </Link>
                    ) : (
                      <span className="text-xs text-text-tertiary">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-red-500">{j.error ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
