"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiGet } from "@/utils/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";

type AssessmentData = Record<string, unknown>;

function maybe(label: string, val: unknown): string {
  if (val === null || val === undefined || val === "") return "-";
  if (typeof val === "string") return val.replace(/_/g, " ");
  return String(val);
}

function pct(v: unknown): string {
  if (v === null || v === undefined) return "-";
  return `${v}%`;
}

export default function ComparePage() {
  const searchParams = useSearchParams();
  const jobIds = useMemo(
    () => (searchParams.get("jobs") || "").split(",").filter(Boolean),
    [searchParams],
  );

  const [left, setLeft] = useState<AssessmentData | null>(null);
  const [right, setRight] = useState<AssessmentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOne = useCallback(async (jobId: string): Promise<AssessmentData> => {
    const resp = await apiGet<Record<string, unknown>>(`/jobs/${jobId}`);
    return (resp.result as AssessmentData) || resp;
  }, []);

  useEffect(() => {
    if (jobIds.length < 2) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([fetchOne(jobIds[0]), fetchOne(jobIds[1])])
      .then(([a, b]) => { if (!cancelled) { setLeft(a); setRight(b); } })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [jobIds, fetchOne]);

  if (jobIds.length < 2) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <Card className="text-center">
          <p className="text-sm text-text-secondary">Select at least 2 assessments from the{" "}
            <a href="/history" className="text-brand underline underline-offset-2">history page</a> to compare.
          </p>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
            <p className="text-xs text-text-tertiary">Loading assessments...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <Card className="border-danger/30">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      </div>
    );
  }

  const l = left || {};
  const r = right || {};
  const rows: { label: string; lv: unknown; rv: unknown }[] = [
    { label: "Vehicle Type", lv: l.vehicle_type, rv: r.vehicle_type },
    { label: "Compliance State", lv: l.compliance_state, rv: r.compliance_state },
    { label: "Feasibility", lv: l.feasibility_label, rv: r.feasibility_label },
    { label: "Confidence", lv: l.confidence_score, rv: r.confidence_score },
    { label: "Risk State", lv: l.risk_state, rv: r.risk_state },
    { label: "Critical Risks", lv: (l.critical_risks as unknown[])?.length ?? 0, rv: (r.critical_risks as unknown[])?.length ?? 0 },
    { label: "High Risks", lv: (l.high_risks as unknown[])?.length ?? 0, rv: (r.high_risks as unknown[])?.length ?? 0 },
    { label: "Recommendations", lv: (l.recommendations as unknown[])?.length ?? 0, rv: (r.recommendations as unknown[])?.length ?? 0 },
    { label: "Degradations", lv: (l.degradations as unknown[])?.length ?? 0, rv: (r.degradations as unknown[])?.length ?? 0 },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 animate-fade-in">
      <PageHeader title="Compare Assessments" subtitle={`Job ${jobIds[0].slice(0, 8)} vs ${jobIds[1].slice(0, 8)}`} />

      <Card padding="none" className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-muted text-xs uppercase tracking-wider text-text-tertiary">
              <th className="px-4 py-3 font-medium w-1/4">Metric</th>
              <th className="px-4 py-3 font-medium w-[37.5%]">Assessment A</th>
              <th className="px-4 py-3 font-medium w-[37.5%]">Assessment B</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r) => (
              <tr key={r.label} className="hover:bg-surface-hover transition-colors">
                <td className="px-4 py-3 font-medium text-text-primary">{r.label}</td>
                <td className={`px-4 py-3 ${compareClass(r.lv, r.rv)}`}>
                  {formatValue(r.label, r.lv)}
                </td>
                <td className={`px-4 py-3 ${compareClass(r.rv, r.lv)}`}>
                  {formatValue(r.label, r.rv)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <JobCard title="Assessment A" data={l} />
        <JobCard title="Assessment B" data={r} />
      </div>
    </div>
  );
}

function formatValue(label: string, v: unknown): string {
  if (label === "Confidence" && typeof v === "number") return pct(v);
  if (label === "Critical Risks" || label === "High Risks") return String(v ?? 0);
  return maybe(label, v);
}

function compareClass(a: unknown, b: unknown): string {
  if (a === b) return "";
  const va = a === null || a === undefined || a === "" ? null : a;
  const vb = b === null || b === undefined || b === "" ? null : b;
  if (va === null && vb === null) return "";
  if (va === null) return "text-danger";
  if (vb === null) return "text-success";
  return "text-accent";
}

function JobCard({ title, data }: { title: string; data: AssessmentData }) {
  const ds = (data.deviation_score ?? data.deviation_score_overall ?? null) as number | null;
  const sp = (data.salvage_potential ?? null) as number | null;
  const dc = (data.deviation_certainty ?? null) as number | null;
  const issues = (data.top_issues ?? []) as string[];

  const bar = (v: number, color: string) => (
    <div className="h-2 w-full rounded-full bg-surface-muted">
      <div className="h-2 rounded-full transition-all" style={{ width: `${Math.max(0, Math.min(100, v))}%`, backgroundColor: color }} />
    </div>
  );

  return (
    <Card>
      <h3 className="text-sm font-semibold text-text-primary mb-4">{title}</h3>
      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-secondary">Deviation Score</span>
            <span className="font-medium text-text-primary">{ds != null ? `${ds.toFixed(1)}%` : "-"}</span>
          </div>
          {ds != null && bar(ds, "#dc2626")}
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-secondary">Salvage Potential</span>
            <span className="font-medium text-success">{sp != null ? `${sp.toFixed(1)}%` : "-"}</span>
          </div>
          {sp != null && bar(sp, "#059669")}
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-secondary">Deviation Certainty</span>
            <span className="font-medium text-text-primary">{dc != null ? `${dc.toFixed(1)}%` : "-"}</span>
          </div>
          {dc != null && bar(dc, "#0d9488")}
        </div>
        {issues.length > 0 && (
          <div>
            <p className="text-xs text-text-secondary mb-2">Top Issues</p>
            <div className="flex flex-wrap gap-1">
              {issues.map((issue, i) => (
                <Badge key={i} variant="warning" size="sm">{issue}</Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
