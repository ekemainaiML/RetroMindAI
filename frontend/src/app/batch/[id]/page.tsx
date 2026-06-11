"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
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
      const res = await fetch(`${API_BASE}/batch/${batchId}`, { headers });
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
        <Card className="border-danger/30 text-danger text-xs">{error}</Card>
        <button onClick={fetchBatch} className="rounded-lg border border-border px-6 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors">Retry</button>
      </div>
    );
  }

  if (!data) return null;

  const succeeded = data.jobs.filter((j) => j.status === "created").length;
  const failed = data.jobs.filter((j) => j.status !== "created").length;
  const pct = data.total > 0 ? Math.round((succeeded / data.total) * 100) : 0;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 animate-fade-in">
      <PageHeader
        title="Batch Dashboard"
        subtitle={data.batch_id}
        actions={<Link href="/batch" className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-colors">New Batch</Link>}
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card><p className="text-xs font-medium text-text-tertiary">Total</p><p className="mt-1 text-2xl font-bold text-text-primary">{data.total}</p></Card>
        <Card className="border-success/30"><p className="text-xs font-medium text-success">Created</p><p className="mt-1 text-2xl font-bold text-success">{succeeded}</p></Card>
        <Card className="border-danger/30"><p className="text-xs font-medium text-danger">Failed</p><p className="mt-1 text-2xl font-bold text-danger">{failed}</p></Card>
        <Card><p className="text-xs font-medium text-text-tertiary">Success Rate</p><p className="mt-1 text-2xl font-bold text-text-primary">{pct}%</p></Card>
      </div>

      <div className="h-2 w-full rounded-full bg-zinc-200 dark:bg-zinc-700">
        <div className="h-2 rounded-full bg-brand transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>

      {data.avg_feasibility !== null && (
        <Card><div className="flex items-center justify-between"><span className="text-sm font-medium text-text-primary">Average Feasibility</span><span className="text-lg font-bold text-brand">{data.avg_feasibility}%</span></div></Card>
      )}

      <Card padding="none">
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
                <td className="px-4 py-3"><Badge variant={j.status === "created" ? "success" : "danger"} size="sm">{j.status}</Badge></td>
                <td className="px-4 py-3">
                  {j.intake_id ? <Link href={`/?job_id=${j.intake_id}`} className="text-xs font-mono text-brand hover:underline">{j.intake_id.slice(0, 8)}…</Link> : <span className="text-xs text-text-tertiary">—</span>}
                </td>
                <td className="px-4 py-3 text-xs text-danger">{j.error ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
