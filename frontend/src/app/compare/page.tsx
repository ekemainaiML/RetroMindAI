"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API_BASE, getApiKey } from "@/utils/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";

interface ComparisonJob {
  job_id: string;
  vehicle_type: string;
  confidence_score: number;
  compliance_state: string;
  feasibility_score: number;
  feasibility_label: string;
  deviation_score: number;
  deviation_certainty: number;
  salvage_potential: number;
  risk_counts: Record<string, number>;
  system_risk_state: string;
  top_issues: string[];
  recommendation_count: number;
  degradation_count: number;
}

function maybe(val: unknown): string {
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

  const [jobs, setJobs] = useState<ComparisonJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (jobIds.length < 2) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const key = getApiKey();
        const res = await fetch(`${API_BASE}/comparison?job_ids=${jobIds.join(",")}`, {
          headers: { "X-API-Key": key ?? "" },
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        if (!cancelled) setJobs(data.jobs ?? []);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [jobIds]);

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

  const jobA = jobs[0];
  const jobB = jobs[1];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 animate-fade-in">
      <PageHeader title="Compare Assessments" subtitle={jobs.map((j) => j.job_id.slice(0, 8)).join(" vs ")} />

      <Card padding="none" className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-muted text-xs uppercase tracking-wider text-text-tertiary">
              <th className="px-4 py-3 font-medium w-1/4">Metric</th>
              {jobs.map((j) => (
                <th key={j.job_id} className="px-4 py-3 font-medium w-[37.5%]">Job {j.job_id.slice(0, 8)}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {comparisonRows(jobs).map((row) => (
              <tr key={row.label} className="hover:bg-surface-hover transition-colors">
                <td className="px-4 py-3 font-medium text-text-primary">{row.label}</td>
                {row.values.map((v, i) => {
                  const other = row.values[i === 0 ? 1 : 0];
                  return (
                    <td key={i} className={`px-4 py-3 ${compareClass(v, other)}`}>
                      {formatValue(row.label, v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-8 grid gap-6" style={{ gridTemplateColumns: `repeat(${Math.min(jobs.length, 3)}, 1fr)` }}>
        {jobs.map((j, i) => (
          <JobCard key={j.job_id} title={`Job ${j.job_id.slice(0, 8)}`} job={j} />
        ))}
      </div>
    </div>
  );
}

function comparisonRows(jobs: ComparisonJob[]): { label: string; values: unknown[] }[] {
  return [
    { label: "Vehicle Type", values: jobs.map((j) => j.vehicle_type) },
    { label: "Compliance State", values: jobs.map((j) => j.compliance_state) },
    { label: "Feasibility", values: jobs.map((j) => j.feasibility_label) },
    { label: "Confidence", values: jobs.map((j) => j.confidence_score) },
    { label: "Risk State", values: jobs.map((j) => j.system_risk_state) },
    { label: "Critical Risks", values: jobs.map((j) => j.risk_counts.critical ?? 0) },
    { label: "High Risks", values: jobs.map((j) => j.risk_counts.high ?? 0) },
    { label: "Medium Risks", values: jobs.map((j) => j.risk_counts.medium ?? 0) },
    { label: "Low Risks", values: jobs.map((j) => j.risk_counts.low ?? 0) },
    { label: "Recommendations", values: jobs.map((j) => j.recommendation_count) },
    { label: "Degradations", values: jobs.map((j) => j.degradation_count) },
  ];
}

function formatValue(label: string, v: unknown): string {
  if (label === "Confidence") return pct(v);
  if (label.endsWith("Risks") || label === "Recommendations" || label === "Degradations") return String(v ?? 0);
  return maybe(v);
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

function JobCard({ title, job }: { title: string; job: ComparisonJob }) {
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
            <span className="font-medium text-text-primary">{job.deviation_score.toFixed(1)}%</span>
          </div>
          {bar(job.deviation_score, "#dc2626")}
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-secondary">Salvage Potential</span>
            <span className="font-medium text-success">{job.salvage_potential.toFixed(1)}%</span>
          </div>
          {bar(job.salvage_potential, "#059669")}
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-secondary">Deviation Certainty</span>
            <span className="font-medium text-text-primary">{job.deviation_certainty.toFixed(1)}%</span>
          </div>
          {bar(job.deviation_certainty, "#0d9488")}
        </div>
        {job.top_issues.length > 0 && (
          <div>
            <p className="text-xs text-text-secondary mb-2">Top Issues</p>
            <div className="flex flex-wrap gap-1">
              {job.top_issues.map((issue, i) => (
                <Badge key={i} variant="warning" size="sm">{issue}</Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
