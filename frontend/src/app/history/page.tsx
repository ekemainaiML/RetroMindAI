"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/utils/api";
import Card, { CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";
import HelpBubble from "@/components/HelpBubble";

interface HistoryItem {
  job_id: string;
  intake_id: string;
  workshop_id: string;
  status: string;
  vehicle_type: string | null;
  compliance_state: string | null;
  confidence_score: number | null;
  feasibility_label: string | null;
  view_count: number;
  created_at: string;
  updated_at: string;
}

interface HistoryResponse {
  items: HistoryItem[];
  total: number;
}

const STATUS_BADGE: Record<string, { variant: "success" | "warning" | "info" | "danger" | "default"; label: string }> = {
  completed: { variant: "success", label: "Completed" },
  partial_complete: { variant: "warning", label: "Partial" },
  running: { variant: "info", label: "Running" },
  failed: { variant: "danger", label: "Failed" },
  timed_out: { variant: "danger", label: "Timed Out" },
  queued: { variant: "default", label: "Queued" },
};

const COMPLIANCE_COLORS: Record<string, string> = {
  pass: "text-success",
  pass_with_caveats: "text-accent",
  fail: "text-danger",
  insufficient_evidence: "text-accent",
};

function formatDate(iso: string): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function HistoryPage() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const fetchHistory = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const result = await apiGet<HistoryResponse>("/history");
      setData(result);
    } catch (err) {
      if (!silent) setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(() => fetchHistory(true), 10_000);
    const onVisibility = () => { if (document.visibilityState === "visible") fetchHistory(true); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [fetchHistory]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 animate-fade-in">
      <PageHeader
        title="Assessment History"
        subtitle={data ? `${data.total} assessment${data.total !== 1 ? "s" : ""} recorded` : "Loading..."}
        actions={
          <div className="flex items-center gap-2">
            <Button onClick={() => fetchHistory(true)} variant="secondary" size="sm" loading={refreshing}>
              Refresh
            </Button>
            <Link
              href={selected.size >= 2 ? `/compare?jobs=${Array.from(selected).join(",")}` : "#"}
              onClick={(e) => { if (selected.size < 2) e.preventDefault(); }}
            >
              <Button
                variant="brand"
                size="sm"
                disabled={selected.size < 2}
              >
                Compare ({selected.size})
              </Button>
            </Link>
            <Link href="/">
              <Button variant="primary" size="sm">
                New Assessment
              </Button>
            </Link>
          </div>
        }
      />

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
            <p className="text-xs text-text-tertiary">Loading history...</p>
          </div>
        </div>
      )}

      {error && (
        <Card className="border-danger/30">
          <p className="text-sm text-danger">{error}</p>
          <Button onClick={() => fetchHistory()} variant="ghost" size="sm" className="mt-2">Retry</Button>
        </Card>
      )}

      {data && data.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="mb-6 flex items-center gap-2 rounded-full border border-border bg-surface-muted px-4 py-1.5">
            {[1, 2, 3, 4, 5].map((n) => (
              <span key={n} className="flex h-6 w-6 items-center justify-center rounded-full bg-border text-[10px] font-bold text-text-tertiary">
                {n}
              </span>
            ))}
            <span className="ml-1 text-[10px] text-text-tertiary">5 steps</span>
          </div>
          <p className="text-sm font-medium text-text-primary">No assessments yet</p>
          <p className="mt-1 max-w-xs text-center text-xs text-text-tertiary">
            Start your first EV retrofit assessment to build your knowledge graph.
          </p>
          <Link href="/" className="mt-5">
            <Button variant="brand">Start Assessment</Button>
          </Link>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div>
          <p className="mb-2 text-right text-[10px] text-text-tertiary">Auto-refreshes every 10s</p>
          <Card padding="none">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                  <th className="w-10 px-2 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={data.items.length > 0 && selected.size === data.items.length}
                      onChange={() => {
                        if (selected.size === data.items.length) setSelected(new Set());
                        else setSelected(new Set(data.items.map((i) => i.job_id)));
                      }}
                      className="h-3.5 w-3.5 accent-brand"
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">Vehicle</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Compliance</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Feasibility</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.items.map((item) => {
                  const sb = STATUS_BADGE[item.status] || { variant: "default" as const, label: item.status.replace(/_/g, " ") };
                  return (
                    <tr
                      key={item.job_id}
                      className={`group hover:bg-surface-hover transition-colors ${selected.has(item.job_id) ? "bg-brand/5" : ""}`}
                    >
                      <td className="px-2 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={selected.has(item.job_id)}
                          onChange={() => {
                            const next = new Set(selected);
                            if (next.has(item.job_id)) next.delete(item.job_id);
                            else next.add(item.job_id);
                            setSelected(next);
                          }}
                          className="h-3.5 w-3.5 accent-brand"
                        />
                      </td>
                      <td className="px-4 py-3 font-medium text-text-primary">
                        {item.vehicle_type ? item.vehicle_type.replace(/_/g, " ") : "-"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={sb.variant} size="sm">{sb.label}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        {item.compliance_state && (
                          <span className={`text-xs font-medium capitalize ${COMPLIANCE_COLORS[item.compliance_state] || "text-text-tertiary"}`}>
                            {item.compliance_state.replace(/_/g, " ")}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-text-secondary">
                        {item.confidence_score != null ? `${item.confidence_score}%` : "-"}
                      </td>
                      <td className="px-4 py-3 text-xs text-text-secondary">
                        {item.feasibility_label ? item.feasibility_label.replace(/_/g, " ") : "-"}
                      </td>
                      <td className="px-4 py-3 text-xs text-text-tertiary">
                        {formatDate(item.updated_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Link href={`/?job_id=${item.job_id}`} className="rounded px-2 py-1 text-[10px] font-medium text-brand hover:bg-brand/5 transition-colors">
                            View
                          </Link>
                          <Link href={`/reports/${item.job_id}`} className="rounded px-2 py-1 text-[10px] font-medium text-text-secondary hover:bg-surface-hover transition-colors">
                            Report
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </div>
      )}
      <HelpBubble />
    </div>
  );
}
