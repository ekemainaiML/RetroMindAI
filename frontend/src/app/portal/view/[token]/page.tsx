"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = "http://localhost:8000/api/v1";

interface PortalAssessment {
  portal: {
    status: string;
    customer_email: string;
    customer_name: string | null;
  };
  assessment: {
    job_id: string;
    status: string;
    vehicle_classification: Record<string, unknown>;
    compliance_state: string;
    confidence_score: number;
    feasibility_score: number;
    feasibility_label: string;
    recommendations: Array<Record<string, unknown>>;
    estimated_total_cost_inr: Record<string, number> | number;
    estimated_days: number;
    digital_twin: unknown;
  };
}

function CostDisplay({ cost }: { cost: Record<string, number> | number }) {
  if (typeof cost === "number") {
    return <>₹{cost.toLocaleString("en-IN")}</>;
  }
  const low = cost.low ?? 0;
  const mid = cost.mid ?? 0;
  const high = cost.high ?? 0;
  return (
    <div className="grid grid-cols-3 gap-3 text-center">
      {[
        { label: "Low", value: low, color: "text-green-600" },
        { label: "Mid", value: mid, color: "text-blue-600" },
        { label: "High", value: high, color: "text-red-600" },
      ].map(({ label, value, color }) => (
        <div key={label} className="rounded-lg bg-surface-muted p-3">
          <p className="text-[10px] font-medium text-text-tertiary">{label}</p>
          <p className={`text-lg font-bold ${color}`}>₹{value.toLocaleString("en-IN")}</p>
        </div>
      ))}
    </div>
  );
}

export default function PortalViewPage() {
  const params = useParams();
  const token = params.token as string;
  const [data, setData] = useState<PortalAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [responded, setResponded] = useState(false);

  const fetchAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/portal/view/${token}`);
      if (!res.ok) {
        if (res.status === 410) throw new Error("This portal link has expired.");
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load assessment");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAssessment();
  }, [fetchAssessment]);

  const handleRespond = async (action: "approved" | "rejected") => {
    const reason = action === "rejected"
      ? prompt("Please provide a reason for rejection:") || undefined
      : undefined;
    if (action === "rejected" && !reason) return;

    try {
      const res = await fetch(`${API_BASE}/portal/${token}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, rejection_reason: reason }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Failed (${res.status})`);
      }
      setResponded(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to submit response");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="text-xs text-text-tertiary">Loading assessment...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="w-full max-w-md rounded-xl border border-border bg-surface-card p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-danger/10">
            <svg className="h-6 w-6 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-text-primary">Access Denied</h1>
          <p className="mt-2 text-sm text-text-secondary">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { portal, assessment } = data;
  const vc = assessment.vehicle_classification;
  const recs = assessment.recommendations || [];

  const priorityStyle = (p: string) => {
    switch (p) {
      case "high": case "essential": return "bg-red-100 text-red-700 border-red-200 dark:bg-red-900 dark:text-red-300 dark:border-red-800";
      case "medium": case "recommended": return "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900 dark:text-amber-300 dark:border-amber-800";
      default: return "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900 dark:text-blue-300 dark:border-blue-800";
    }
  };

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-bold text-text-primary">Vehicle Assessment Report</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Prepared for {portal.customer_name || portal.customer_email}
          </p>
        </div>

        <div className="mb-6 rounded-xl border border-border bg-surface-card p-5">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Vehicle</p>
              <p className="font-semibold text-text-primary">{String(vc.type || "Unknown")}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Status</p>
              <p className="font-semibold text-text-primary">{assessment.compliance_state.replace(/_/g, " ")}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Confidence</p>
              <p className="font-semibold text-text-primary">{assessment.confidence_score}%</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-text-tertiary">Feasibility</p>
              <p className="font-semibold text-text-primary">{assessment.feasibility_label}</p>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <h2 className="mb-3 text-sm font-semibold text-text-primary">Cost Estimate</h2>
          <CostDisplay cost={assessment.estimated_total_cost_inr} />
          <p className="mt-2 text-xs text-text-tertiary">Estimated {assessment.estimated_days} days to complete</p>
        </div>

        {recs.length > 0 && (
          <div className="mb-6">
            <h2 className="mb-3 text-sm font-semibold text-text-primary">
              Recommendations ({recs.length})
            </h2>
            <div className="space-y-3">
              {recs.map((r, i) => (
                <div key={i} className="rounded-xl border border-border bg-surface-card p-4">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-semibold text-text-primary">{String(r.title || "")}</h3>
                    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${priorityStyle(String(r.priority || "optional"))}`}>
                      {String(r.priority || "optional")}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-text-secondary">{String(r.description || "")}</p>
                  {(r.cost_estimate != null) && (
                    <p className="mt-2 text-[10px] text-text-tertiary">
                      Cost: {String(r.cost_estimate)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {portal.status === "pending" && !responded && (
          <div className="rounded-xl border border-border bg-surface-card p-6">
            <h2 className="mb-2 text-sm font-semibold text-text-primary">Your Decision</h2>
            <p className="mb-4 text-xs text-text-secondary">
              Please review the assessment and let us know if you approve the recommended work.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => handleRespond("approved")}
                className="flex-1 rounded-lg bg-green-600 px-4 py-3 text-sm font-semibold text-white hover:bg-green-700 transition-all"
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => handleRespond("rejected")}
                className="flex-1 rounded-lg bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700 transition-all"
              >
                Reject
              </button>
            </div>
          </div>
        )}

        {(portal.status !== "pending" || responded) && (
          <div className="rounded-xl border border-border bg-surface-card p-6 text-center">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
              <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-text-primary">
              {portal.status === "approved" ? "Assessment Approved" : portal.status === "rejected" ? "Assessment Rejected" : "Response Recorded"}
            </p>
            <p className="mt-1 text-xs text-text-secondary">
              Thank you for your feedback. The workshop will be notified of your decision.
            </p>
          </div>
        )}

        <div className="mt-8 text-center">
          <p className="text-[10px] text-text-tertiary">
            Powered by <span className="font-semibold">RetroMind AI</span> &middot; Confidential
          </p>
        </div>
      </div>
    </div>
  );
}
