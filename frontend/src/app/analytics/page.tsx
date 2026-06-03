"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "@/utils/api";
import Card from "@/components/ui/Card";
import PageHeader from "@/components/ui/PageHeader";
import Badge from "@/components/ui/Badge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type MonthlyStat = {
  month: string;
  total_jobs: number;
  completed: number;
  partial_complete: number;
  failed: number;
  timed_out: number;
  avg_confidence: number | null;
  avg_processing_sec: number | null;
};

type DeviationTypeCount = { component: string; count: number };

type Stats = {
  monthly: MonthlyStat[];
  total_jobs: number;
  total_completed: number;
  overall_avg_confidence: number | null;
  overall_avg_processing_sec: number | null;
  top_deviations: DeviationTypeCount[];
};

function formatDuration(sec: number | null): string {
  if (sec === null || sec === undefined) return "-";
  if (sec < 60) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}m ${Math.round(sec % 60)}s`;
  return `${Math.round(sec / 3600)}h ${Math.round((sec % 3600) / 60)}m`;
}

function LineChart({
  data, xKey, yKey, label, color, unit,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  label: string;
  color: string;
  unit: string;
}) {
  const width = 600;
  const height = 200;
  const pad = { top: 20, right: 20, bottom: 30, left: 50 };

  const values = data.map((d) => d[yKey] as number | null);
  const max = Math.max(...values.filter((v): v is number => v !== null), 1);
  const xStep = (width - pad.left - pad.right) / Math.max(data.length - 1, 1);

  const points = data
    .map((d, i) => {
      const v = d[yKey] as number | null;
      if (v === null) return null;
      const x = pad.left + i * xStep;
      const y = pad.top + height - pad.top - pad.bottom - ((v / max) * (height - pad.top - pad.bottom));
      return `${x},${y}`;
    })
    .filter(Boolean)
    .join(" ");

  const yTicks = 4;
  const yTicksArr = Array.from({ length: yTicks + 1 }, (_, i) => Math.round((max / yTicks) * i));

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-text-primary">{label}</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-h-48">
        {yTicksArr.map((tick, i) => {
          const y = pad.top + height - pad.top - pad.bottom - ((tick / max) * (height - pad.top - pad.bottom));
          return (
            <g key={i}>
              <line x1={pad.left} y1={y} x2={width - pad.right} y2={y} stroke="rgb(var(--border))" strokeWidth="0.5" />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" fill="rgb(var(--text-tertiary))" fontSize="10">
                {tick}{unit}
              </text>
            </g>
          );
        })}
        {points && <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />}
        {data.map((d, i) => {
          const v = d[yKey] as number | null;
          if (v === null) return null;
          const cx = pad.left + i * xStep;
          const cy = pad.top + height - pad.top - pad.bottom - ((v / max) * (height - pad.top - pad.bottom));
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r="3" fill={color} />
              <text x={cx} y={height - 6} textAnchor="middle" fill="rgb(var(--text-tertiary))" fontSize="9">
                {d[xKey]?.toString().slice(-2)}
              </text>
            </g>
          );
        })}
      </svg>
    </Card>
  );
}

function BarChart({ data, labelKey, valueKey, color }: { data: Record<string, number | string>[]; labelKey: string; valueKey: string; color: string }) {
  const max = Math.max(...data.map((d) => Number(d[valueKey])), 1);
  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-text-primary">Top Deviations</h3>
      <div className="space-y-2">
        {data.map((d, i) => {
          const label = String(d[labelKey]).replace(/_/g, " ");
          const val = Number(d[valueKey]);
          const pct = (val / max) * 100;
          return (
            <div key={i}>
              <div className="mb-1 flex justify-between text-xs">
                <span className="capitalize text-text-secondary">{label}</span>
                <span className="font-semibold text-text-primary">{val}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-surface-muted">
                <div className="h-2 rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [months, setMonths] = useState(12);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<Stats>(`/workshop/stats?months=${months}`);
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stats");
    } finally {
      setLoading(false);
    }
  }, [months]);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  const monthlyData = useMemo(() => {
    if (!stats) return [];
    return stats.monthly.map((m) => ({
      ...m,
      pass_rate: m.total_jobs > 0 ? Math.round(((m.completed + m.partial_complete) / m.total_jobs) * 100) : 0,
    }));
  }, [stats]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="text-xs text-text-tertiary">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <Card className="border-danger/30 text-center">
          <p className="text-sm text-danger">{error}</p>
          <button onClick={fetchStats} className="mt-3 rounded-lg bg-danger px-4 py-2 text-xs font-medium text-white hover:opacity-90">
            Retry
          </button>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 animate-fade-in">
      <PageHeader
        title="Workshop Analytics"
        subtitle="Monthly aggregated statistics for your workshop"
        actions={
          <select
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
            className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30"
          >
            <option value={6}>Last 6 months</option>
            <option value={12}>Last 12 months</option>
            <option value={24}>Last 24 months</option>
            <option value={36}>Last 36 months</option>
          </select>
        }
      />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Jobs" value={stats?.total_jobs ?? "-"} />
        <MetricCard label="Completed" value={stats?.total_completed ?? "-"} color="text-success" />
        <MetricCard label="Avg Confidence" value={stats?.overall_avg_confidence != null ? `${stats.overall_avg_confidence}%` : "-"} color="text-accent" />
        <MetricCard label="Avg Processing" value={formatDuration(stats?.overall_avg_processing_sec ?? null)} color="text-info" />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <LineChart data={monthlyData} xKey="month" yKey="total_jobs" label="Jobs per Month" color="#d97706" unit="" />
        <LineChart data={monthlyData} xKey="month" yKey="avg_confidence" label="Avg Confidence Score" color="#059669" unit="%" />
        <LineChart
          data={monthlyData.map((m) => ({ ...m, pass_rate_as_number: m.pass_rate }))}
          xKey="month" yKey="pass_rate_as_number" label="Pass Rate (completed + partial)" color="#0d9488" unit="%"
        />
        <LineChart data={monthlyData} xKey="month" yKey="avg_processing_sec" label="Avg Processing Time" color="#8b5cf6" unit="s" />
      </div>

      {stats?.top_deviations && stats.top_deviations.length > 0 && (
        <div className="mb-8 max-w-lg">
          <BarChart data={stats.top_deviations} labelKey="component" valueKey="count" color="#dc2626" />
        </div>
      )}

      <Card padding="none">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
              <th className="px-4 py-3 font-medium">Month</th>
              <th className="px-4 py-3 font-medium">Total</th>
              <th className="px-4 py-3 font-medium text-success">Completed</th>
              <th className="px-4 py-3 font-medium text-accent">Partial</th>
              <th className="px-4 py-3 font-medium text-danger">Failed</th>
              <th className="px-4 py-3 font-medium">Timed Out</th>
              <th className="px-4 py-3 font-medium">Avg Conf</th>
              <th className="px-4 py-3 font-medium">Avg Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {monthlyData.map((m) => (
              <tr key={m.month} className="hover:bg-surface-hover transition-colors">
                <td className="px-4 py-3 font-medium text-text-primary">{m.month}</td>
                <td className="px-4 py-3 text-text-secondary">{m.total_jobs}</td>
                <td className="px-4 py-3 text-success">{m.completed}</td>
                <td className="px-4 py-3 text-accent">{m.partial_complete}</td>
                <td className="px-4 py-3 text-danger">{m.failed}</td>
                <td className="px-4 py-3 text-text-tertiary">{m.timed_out}</td>
                <td className="px-4 py-3 text-text-secondary">{m.avg_confidence != null ? `${m.avg_confidence}%` : "-"}</td>
                <td className="px-4 py-3 text-text-secondary">{formatDuration(m.avg_processing_sec)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function MetricCard({ label, value, color = "text-text-primary" }: { label: string; value: number | string; color?: string }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
    </Card>
  );
}
