"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiGet, apiPost, getApiKey } from "@/utils/api";
import DnaGraph from "@/components/DnaGraph";

interface ReportSection {
  id: string;
  title: string;
  content: Record<string, unknown>;
}

interface ComplianceReport {
  report_id: string;
  job_id: string;
  intake_id: string;
  generated_at: string;
  job_status: string;
  sections: ReportSection[];
}

function formatValue(v: unknown): string {
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (typeof v === "object" && v !== null) {
    if (Array.isArray(v)) {
      return v.map(formatValue).join(", ");
    }
    return Object.entries(v)
      .map(([k, val]) => `${k.replace(/_/g, " ")}: ${formatValue(val)}`)
      .join(", ");
  }
  return String(v);
}

function ValueDisplay({ value, label }: { value: unknown; label: string }) {
  if (value == null) return null;
  let display: string;
  if (typeof value === "boolean") {
    display = value ? "Yes" : "No";
  } else if (Array.isArray(value)) {
    display = value
      .map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v)))
      .join(", ");
  } else if (typeof value === "object") {
    display = formatValue(value);
  } else {
    display = String(value);
  }
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="shrink-0 text-xs font-medium text-text-secondary">
        {label}
      </span>
      <span className="break-all text-right text-xs font-semibold text-text-primary">
        {display}
      </span>
    </div>
  );
}

function Card({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="no-break rounded-xl border border-border bg-surface-card">
      <div className="border-b border-border px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono uppercase tracking-wider text-text-tertiary">
            {id.replace(/_/g, " ")}
          </span>
          <span className="text-[10px] text-border-light">/</span>
          <h2 className="text-sm font-semibold text-text-primary">
            {title}
          </h2>
        </div>
      </div>
      <div className="space-y-1 px-5 py-4">{children}</div>
    </div>
  );
}

function SectionRenderer({ section }: { section: ReportSection }) {
  const { content } = section;

  if (section.id === "recommendations_overview") {
    const recs = (content.recommendations as Array<Record<string, unknown>>) ?? [];
    return (
      <Card id={section.id} title={section.title}>
        <ValueDisplay value={content.total_recommendations} label="Total" />
        <ValueDisplay value={content.essential_count} label="Essential" />
        <ValueDisplay value={content.recommended_count} label="Recommended" />
        {recs.length > 0 && (
          <div className="mt-3 space-y-2">
            {recs.map((r, i) => (
              <div
                key={i}
                className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                    {r.title as string}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      r.priority === "essential"
                        ? "bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-200"
                        : r.priority === "recommended"
                          ? "bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-200"
                          : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                    }`}
                  >
                    {r.priority as string}
                  </span>
                </div>
                <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  {r.description as string}
                </p>
                {Boolean(r.blocking) && (
                  <p className="mt-1 text-[10px] font-medium text-red-500">
                    Blocking — must be resolved
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    );
  }

  if (section.id === "deviations" || section.id === "deviation_summary") {
    const devs = (content.deviations as Array<Record<string, unknown>>) ?? [];
    return (
      <Card id={section.id} title={section.title}>
        <ValueDisplay value={content.anomalies_detected} label="Anomalies" />
        <ValueDisplay value={content.severity} label="Severity" />
        <ValueDisplay value={content.salvage_potential} label="Salvage Potential" />
        {devs.length > 0 && (
          <div className="mt-3 space-y-1">
            {(content.top_issues as string[] ?? []).map((issue, i) => (
              <p key={i} className="text-xs text-zinc-600 dark:text-zinc-400">
                • {issue}
              </p>
            ))}
          </div>
        )}
      </Card>
    );
  }

  if (section.id === "cost_estimation") {
    const cost = content.estimated_total_cost_inr as Record<string, unknown> ?? {};
    return (
      <Card id={section.id} title={section.title}>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-900">
            <p className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400">
              Low
            </p>
            <p className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
              ₹{Number(cost.low ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-900">
            <p className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400">
              Mid
            </p>
            <p className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
              ₹{Number(cost.mid ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-900">
            <p className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400">
              High
            </p>
            <p className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
              ₹{Number(cost.high ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
        </div>
        <ValueDisplay value={content.estimated_days} label="Estimated Days" />
      </Card>
    );
  }

  if (section.id === "infrastructure_degradation") {
    const degs = (content.degradations as Array<Record<string, unknown>>) ?? [];
    const svc = (content.service_status as Record<string, string>) ?? {};
    const allOperational = content.all_operational as boolean ?? true;
    const hasEntries = Object.keys(svc).length > 0 || degs.length > 0;
    if (!hasEntries || (allOperational && degs.length === 0)) {
      return (
        <Card id={section.id} title={section.title}>
          <div className="space-y-2">
            {Object.entries(svc).length > 0 ? (
              Object.entries(svc).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-2 dark:border-green-800 dark:bg-green-950"
                >
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-xs font-medium text-green-800 dark:text-green-200">
                    {name}
                  </span>
                  <span className="ml-auto text-[10px] text-green-600 dark:text-green-400">
                    {status}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-green-600 dark:text-green-400">
                All services operational
              </p>
            )}
          </div>
        </Card>
      );
    }
    return (
      <Card id={section.id} title={section.title}>
        <div className="space-y-2">
          {Object.entries(svc).map(([name, status]) => {
            const isHealthy = status === "connected";
            return (
              <div
                key={name}
                className={`flex items-center gap-2 rounded-lg border p-2 ${
                  isHealthy
                    ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
                    : "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    isHealthy ? "bg-green-500" : "bg-yellow-500"
                  }`}
                />
                <span
                  className={`text-xs font-medium ${
                    isHealthy
                      ? "text-green-800 dark:text-green-200"
                      : "text-yellow-800 dark:text-yellow-200"
                  }`}
                >
                  {name}
                </span>
                <span
                  className={`ml-auto text-[10px] ${
                    isHealthy
                      ? "text-green-600 dark:text-green-400"
                      : "text-yellow-700 dark:text-yellow-300"
                  }`}
                >
                  {status}
                </span>
              </div>
            );
          })}
          {degs.map((d, i) => (
            <div
              key={i}
              className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-950"
            >
              <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200">
                {d.service as string}
              </p>
              {Boolean(d.message) && (
                <p className="mt-0.5 text-[10px] text-yellow-700 dark:text-yellow-300">
                  {String(d.message)}
                </p>
              )}
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (section.id === "retrofit_dna") {
    const matches = (content.matches as Array<Record<string, unknown>>) ?? [];
    return (
      <Card id={section.id} title={section.title}>
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <div className="flex-1">
            <ValueDisplay value={content.matches_found} label="Similar Matches" />
            {matches.length > 0 && (
              <div className="mt-3 space-y-2">
                {matches.map((m, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-zinc-100 px-3 py-2 dark:border-zinc-800"
                  >
                    <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      {m.vehicle_id as string}
                    </span>
                    <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                      {(m.type as string)?.replace(/_/g, " ")} · {(m.confidence as number) != null ? `${((m.confidence as number) * 100).toFixed(0)}%` : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {matches.length === 0 && (
              <div className="mt-3 rounded-lg border border-dashed border-indigo-200 bg-indigo-50/50 p-4 text-center dark:border-indigo-800 dark:bg-indigo-950/20">
                <p className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                  New Pattern
                </p>
                <p className="mt-1 text-[10px] text-zinc-500 dark:text-zinc-400">
                  No similar retrofit patterns found in the knowledge graph.
                </p>
              </div>
            )}
          </div>
          <div className="flex-1">
            <DnaGraph
              currentLabel={content.current_vehicle_label as string ?? "Current"}
              currentType={content.current_vehicle_type as string ?? "unknown"}
              matches={
                (content.matches as Array<{
                  vehicle_id: string;
                  type: string;
                  matching_deviations: number;
                  confidence: number;
                }>) ?? []
              }
            />
          </div>
        </div>
      </Card>
    );
  }

  if (section.id === "battery_placement") {
    const recs = (content.battery_recommendations as Array<Record<string, unknown>>) ?? [];
    const batteryZones = content.battery_zones as Record<string, unknown> | null;
    const zones = (batteryZones?.zones as Array<Record<string, unknown>>) ?? [];
    return (
      <Card id={section.id} title={section.title}>
        <p className="mb-3 text-[11px] text-zinc-500">
          Optimised battery placement zones and recommendations based on vehicle geometry and detected deviations.
        </p>

        {batteryZones && zones.length > 0 && (
          <div className="mb-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                Computed Zones
              </span>
              {(!!batteryZones.recommended_zone) && (
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-[9px] font-medium text-green-700 dark:bg-green-900 dark:text-green-200">
                  Recommended: {batteryZones.recommended_zone as string}
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(zones as Array<Record<string, unknown>>).slice(0, 6).map((z, i) => (
                <div
                  key={i}
                  className={`rounded-lg border p-3 ${
                    (z.id as string) === (batteryZones.recommended_zone as string)
                      ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-950"
                      : "border-zinc-100 dark:border-zinc-800"
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <span className="text-[11px] font-semibold text-zinc-800 dark:text-zinc-200">
                      {z.label as string}
                    </span>
                    {(!!z.id && z.id === batteryZones.recommended_zone) && (
                      <span className="shrink-0 text-[10px] text-green-600 dark:text-green-400">★ Best</span>
                    )}
                  </div>
                  {(!!z.max_dimensions_mm) && (
                    <p className="mt-1 text-[10px] text-zinc-500">
                      {(z.max_dimensions_mm as Record<string, number>).length ?? "?"} × {(z.max_dimensions_mm as Record<string, number>).width ?? "?"} × {(z.max_dimensions_mm as Record<string, number>).height ?? "?"} mm
                    </p>
                  )}
                  {((z.warnings as string[])?.length ?? 0) > 0 && (
                    <p className="mt-1 text-[10px] text-amber-600 dark:text-amber-400">
                      ⚠ {(z.warnings as string[]).join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {recs.length === 0 && zones.length === 0 && (
          <p className="text-xs text-zinc-400">No battery placement recommendations available.</p>
        )}
        {recs.map((r, i) => (
          <div
            key={i}
            className="mb-2 rounded-lg border border-zinc-100 p-3 last:mb-0 dark:border-zinc-800"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                {r.title as string}
              </span>
              {(r.priority as string) && (
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-medium ${
                  r.priority === "critical"
                    ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                    : r.priority === "recommended"
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200"
                      : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                }`}>
                  {r.priority as string}
                </span>
              )}
            </div>
            {(r.description as string) && (
              <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">
                {r.description as string}
              </p>
            )}
          </div>
        ))}
      </Card>
    );
  }

  if (section.id === "wiring_guidance") {
    const recs = (content.wiring_recommendations as Array<Record<string, unknown>>) ?? [];
    return (
      <Card id={section.id} title={section.title}>
        <p className="mb-3 text-[11px] text-zinc-500">
          Wiring routing guidance accounting for deviation-triggered caution zones and spatial constraints.
        </p>
        {recs.length === 0 && (
          <p className="text-xs text-zinc-400">No wiring recommendations available.</p>
        )}
        {recs.map((r, i) => (
          <div
            key={i}
            className="mb-2 rounded-lg border border-zinc-100 p-3 last:mb-0 dark:border-zinc-800"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                {r.title as string}
              </span>
              {(r.priority as string) && (
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-medium ${
                  r.priority === "critical"
                    ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                    : r.priority === "recommended"
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200"
                      : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                }`}>
                  {r.priority as string}
                </span>
              )}
            </div>
            {(r.description as string) && (
              <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">
                {r.description as string}
              </p>
            )}
          </div>
        ))}
      </Card>
    );
  }

  const skipKeys = new Set([
    "deviations", "top_issues", "recommendations",
    "estimated_total_cost_inr", "degradations", "matches",
    "current_vehicle_type", "current_vehicle_label", "current_intake_id", "matches_found",
    "battery_recommendations", "wiring_recommendations",
  ]);

  const entries = Object.entries(content).filter(
    ([k, v]) => !skipKeys.has(k) && v != null
  );

  return (
    <Card id={section.id} title={section.title}>
      {entries.length === 0 && (
        <p className="text-xs text-zinc-400">No data available</p>
      )}
      {entries.map(([key, value]) => (
        <ValueDisplay
          key={key}
          label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          value={value}
        />
      ))}
    </Card>
  );
}

function ReportContent({ report }: { report: ComplianceReport }) {
  return (
    <div className="space-y-4">
      {report.sections.map((section) => (
        <SectionRenderer key={section.id} section={section} />
      ))}
    </div>
  );
}

function ReportHeader({
  report,
  onExport,
  onPdfDownload,
  onCadDownload,
  onPortalShare,
  cadLoading,
  portalLoading,
  jobStatus,
}: {
  report: ComplianceReport;
  onExport: () => void;
  onPdfDownload: () => void;
  onCadDownload: (format: "step" | "stl") => void;
  onPortalShare: () => void;
  cadLoading: string | null;
  portalLoading: boolean;
  jobStatus: string;
}) {
  return (
    <div className="mb-8 flex items-start justify-between no-print">
      <div>
        <div className="flex items-center gap-3">
          <Link href="/history" className="text-xs text-text-tertiary hover:text-text-secondary transition-colors">
            &larr; Back to history
          </Link>
          <span className="text-text-tertiary">/</span>
          <h1 className="text-lg font-bold text-text-primary">Compliance Report</h1>
        </div>
        <p className="mt-1 text-xs text-text-secondary">
          Job {report.job_id.slice(0, 8)} &middot; Generated {new Date(report.generated_at).toLocaleString("en-IN")}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onPortalShare}
          disabled={portalLoading || jobStatus !== "completed"}
          title={jobStatus !== "completed" ? `Assessment must be completed first (current: ${jobStatus})` : ""}
          className="inline-flex items-center justify-center rounded-lg border border-purple-300 bg-purple-50 px-3 py-2 text-xs font-medium text-purple-700 hover:bg-purple-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {portalLoading ? "..." : "Share with Customer"}
        </button>
        <button
          type="button"
          disabled={cadLoading !== null}
          onClick={() => onCadDownload("step")}
          className="inline-flex items-center justify-center rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100 transition-all disabled:opacity-40"
        >
          {cadLoading === "step" ? "..." : "STEP"}
        </button>
        <button
          type="button"
          disabled={cadLoading !== null}
          onClick={() => onCadDownload("stl")}
          className="inline-flex items-center justify-center rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100 transition-all disabled:opacity-40"
        >
          {cadLoading === "stl" ? "..." : "STL"}
        </button>
        <button
          type="button"
          onClick={onExport}
          className="inline-flex items-center justify-center rounded-lg bg-brand px-4 py-2 text-xs font-medium text-white hover:bg-brand-dark transition-all"
        >
          Export JSON
        </button>
        <button
          type="button"
          onClick={onPdfDownload}
          className="inline-flex items-center justify-center rounded-lg border border-border bg-surface px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-all"
        >
          Export PDF
        </button>
      </div>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("");
  const [cadLoading, setCadLoading] = useState<string | null>(null);
  const [portalSessions, setPortalSessions] = useState<Array<{
    id: string; customer_email: string; customer_name: string | null;
    status: string; created_at: string; approved_at: string | null;
    rejection_reason: string | null;
  }>>([]);
  const [portalLoading, setPortalLoading] = useState(false);
  const [portalLink, setPortalLink] = useState<string | null>(null);
  const [portalViewOpen, setPortalViewOpen] = useState(false);
  const [portalFormOpen, setPortalFormOpen] = useState(false);
  const [portalEmail, setPortalEmail] = useState("");
  const [portalName, setPortalName] = useState("");
  const [portalError, setPortalError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  const fetchReportAndSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [result, sessions] = await Promise.all([
        apiGet<ComplianceReport>(`/reports/${jobId}`),
        apiGet<Array<{
          id: string; customer_email: string; customer_name: string | null;
          status: string; created_at: string; approved_at: string | null;
          rejection_reason: string | null;
        }>>(`/portal/sessions?job_id=${jobId}`).catch(() => []),
      ]);
      setReport(result);
      setJobStatus(result.job_status);
      setPortalSessions(sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchReportAndSessions();
  }, [fetchReportAndSessions]);

  const handleCadDownload = async (format: "step" | "stl") => {
    setCadLoading(format);
    try {
      const key = getApiKey();
      const res = await fetch(
        `http://localhost:8000/api/v1/cad/export/${jobId}?format=${format}`,
        { headers: key ? { "X-API-Key": key } : {} }
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        alert(`CAD export failed (${res.status}): ${text}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${jobId.slice(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`CAD export failed: ${err instanceof Error ? err.message : err}`);
    } finally {
      setCadLoading(null);
    }
  };

  const handleExportJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `retromind-report-${jobId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPdf = async () => {
    const key = getApiKey();
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/reports/${jobId}/pdf`,
        { headers: key ? { "X-API-Key": key } : {} }
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`PDF export failed (${res.status}): ${text}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `assessment_report_${jobId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "PDF export failed");
    }
  };

  const handlePortalShare = () => {
    setPortalFormOpen(true);
    setPortalError(null);
    setPortalEmail("");
    setPortalName("");
  };

  const handlePortalGenerate = async () => {
    if (!portalEmail.trim()) {
      setPortalError("Customer email is required");
      return;
    }
    setPortalLoading(true);
    setPortalError(null);
    try {
      const link = await apiPost<{ portal_url: string; token: string }>("/portal/share", {
        job_id: jobId,
        customer_email: portalEmail.trim(),
        customer_name: portalName.trim() || null,
      });
      setPortalLink(link.portal_url);
      setPortalFormOpen(false);
      setPortalViewOpen(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("must be completed")) {
        setPortalError("This assessment is not in a completed state. Only completed assessments can be shared.");
      } else if (msg.includes("400")) {
        setPortalError("Unable to share. The assessment may not be in a shareable state.");
      } else {
        setPortalError(msg || "Failed to create portal link");
      }
    } finally {
      setPortalLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!portalLink) return;
    try {
      await navigator.clipboard.writeText(portalLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const input = document.getElementById("portal-link-input") as HTMLInputElement;
      if (input) { input.select(); document.execCommand("copy"); }
    }
  };

  return (
      <div className="mx-auto max-w-4xl px-4 py-8 animate-fade-in">
      <style>{`
@media print {
  header, .fixed, [class*="z-4"], [class*="z-5"], [class*="help"],
  .help-bubble, button[class*="fixed"] {
    display: none !important;
  }
  body { background: white; color: black; }
  @page { margin: 1.5cm; }
  .no-break { break-inside: avoid; }
  .page-break { break-before: page; }
}
      `}</style>
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
            <p className="text-xs text-text-tertiary">Loading report...</p>
          </div>
        </div>
      )}

      {error && (
        <div>
          <div className="rounded-xl border border-danger/30 bg-surface-card p-6">
            <p className="text-sm text-danger">{error}</p>
          </div>
          <Link
            href="/history"
            className="mt-4 inline-block text-xs font-medium text-brand underline underline-offset-2"
          >
            Back to history
          </Link>
        </div>
      )}

      {report && (
        <div ref={printRef}>
          <ReportHeader report={report} onExport={handleExportJson} onPdfDownload={handleExportPdf} onCadDownload={handleCadDownload} onPortalShare={handlePortalShare} cadLoading={cadLoading} portalLoading={portalLoading} jobStatus={jobStatus} />
          <ReportContent report={report} />
        </div>
      )}

      {!error && !loading && report && portalSessions.length > 0 && (
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Shared Links ({portalSessions.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-text-tertiary">
                  <th className="pb-2 pr-3 font-medium">Customer</th>
                  <th className="pb-2 pr-3 font-medium">Email</th>
                  <th className="pb-2 pr-3 font-medium">Status</th>
                  <th className="pb-2 pr-3 font-medium">Sent</th>
                  <th className="pb-2 font-medium">Response</th>
                </tr>
              </thead>
              <tbody>
                {portalSessions.map((s) => (
                  <tr key={s.id} className="border-b border-border/50 last:border-0">
                    <td className="py-2 pr-3 text-text-primary">
                      {s.customer_name || "—"}
                    </td>
                    <td className="py-2 pr-3 text-text-secondary">{s.customer_email}</td>
                    <td className="py-2 pr-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        s.status === "approved" ? "bg-success/10 text-success" :
                        s.status === "rejected" ? "bg-danger/10 text-danger" :
                        s.status === "expired" ? "bg-warning/10 text-warning" :
                        "bg-surface-hover text-text-tertiary"
                      }`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-text-tertiary whitespace-nowrap">
                      {new Date(s.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 text-text-secondary">
                      {s.status === "approved" && s.approved_at
                        ? `Approved ${new Date(s.approved_at).toLocaleDateString()}`
                        : s.status === "rejected" && s.rejection_reason
                        ? s.rejection_reason
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {portalError && (
        <div className="fixed bottom-4 right-4 rounded-lg border border-danger/30 bg-danger/5 p-3 text-xs text-danger shadow-lg">
          {portalError}
        </div>
      )}

      {portalFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Share with Customer</h3>
            <p className="mb-4 text-xs text-text-secondary">
              Enter the customer details to generate a secure portal link.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">Customer Email *</label>
                <input
                  type="email"
                  value={portalEmail}
                  onChange={(e) => setPortalEmail(e.target.value)}
                  placeholder="customer@example.com"
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">Customer Name</label>
                <input
                  type="text"
                  value={portalName}
                  onChange={(e) => setPortalName(e.target.value)}
                  placeholder="John Doe (optional)"
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
                />
              </div>
              {portalError && <p className="text-xs text-danger">{portalError}</p>}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => { setPortalFormOpen(false); setPortalError(null); }}
                className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-all"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePortalGenerate}
                disabled={portalLoading || !portalEmail.trim()}
                className="rounded-lg bg-brand px-4 py-2 text-xs font-medium text-white hover:bg-brand-dark transition-all disabled:opacity-40"
              >
                {portalLoading ? "Generating..." : "Generate Link"}
              </button>
            </div>
          </div>
        </div>
      )}

      {portalViewOpen && portalLink && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Portal Link Ready</h3>
            <p className="mb-4 text-xs text-text-secondary">
              Share this link with your customer to let them view the assessment and approve or reject recommendations.
            </p>
            <div className="flex gap-2">
              <input
                id="portal-link-input"
                type="text"
                readOnly
                value={portalLink}
                className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary focus:outline-none"
              />
              <button
                type="button"
                onClick={copyToClipboard}
                className="rounded-lg bg-brand px-4 py-2 text-xs font-medium text-white hover:bg-brand-dark transition-all"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => { setPortalViewOpen(false); setCopied(false); }}
                className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
