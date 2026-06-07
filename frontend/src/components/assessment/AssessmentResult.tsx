"use client";

import Link from "next/link";
import { useState } from "react";
import type { AssessmentData } from "@/types/assessment";
import { getApiKey } from "@/utils/api";
import {
  ASSESSMENT_STATE_LABELS,
  ASSESSMENT_STATE_COLORS,
  FEASIBILITY_LABELS,
} from "@/types/assessment";
import FeasibilityGauge from "./FeasibilityGauge";
import RiskBadge from "./RiskBadge";
import RecommendationCard from "./RecommendationCard";
import ConfirmDialog from "./ConfirmDialog";
import DigitalTwinScene from "../digital-twin/DigitalTwinScene";
import type { DigitalTwinData } from "@/types/assessment";

interface Props {
  assessment: AssessmentData;
  jobId: string;
  onConfirm: (confirmationType: string, selection: string) => Promise<void>;
}

function ConfidenceFactorBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const pct = Math.round((value > 1 ? value / 100 : value) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="w-32 text-xs font-medium capitalize text-zinc-500 dark:text-zinc-400">
        {label.replace(/_/g, " ")}
      </span>
      <div className="flex-1">
        <div className="h-2 w-full rounded-full bg-zinc-200 dark:bg-zinc-700">
          <div
            className="h-2 rounded-full bg-amber-500 transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <span className="w-10 text-right text-xs font-semibold tabular-nums text-zinc-700 dark:text-zinc-300">
        {pct}%
      </span>
    </div>
  );
}

function RiskRegisterSection({
  risks,
}: {
  risks: NonNullable<AssessmentData["risk_register"]>;
}) {
  const [expanded, setExpanded] = useState(false);

  if (risks.length === 0) return null;

  const criticalCount = risks.filter((r) => r.severity === "critical").length;
  const highCount = risks.filter((r) => r.severity === "high").length;

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-700">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Risk Register
          </span>
          {criticalCount > 0 && (
            <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700 dark:bg-red-900 dark:text-red-300">
              {criticalCount} critical
            </span>
          )}
          {highCount > 0 && (
            <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-bold text-orange-700 dark:bg-orange-900 dark:text-orange-300">
              {highCount} high
            </span>
          )}
          <span className="text-xs text-zinc-400">({risks.length} total)</span>
        </div>
        <svg
          className={`h-4 w-4 text-zinc-400 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-zinc-200 px-3 pb-3 pt-2 space-y-2 dark:border-zinc-700">
          {risks.map((risk, i) => (
            <div
              key={i}
              className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-800/50"
            >
              <div className="mb-1.5 flex items-center gap-2">
                <RiskBadge severity={risk.severity} />
                <span className="text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">
                  {risk.category.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-sm text-zinc-700 dark:text-zinc-300">
                {risk.message}
              </p>
              {risk.description && (
                <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  {risk.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DeviationsSection({
  deviations,
  oemActive,
}: {
  deviations: NonNullable<AssessmentData["deviations"]>;
  oemActive?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (deviations.length === 0) return null;

  const grouped = deviations.reduce<
    Record<string, typeof deviations>
  >((acc, d) => {
    if (!acc[d.severity]) acc[d.severity] = [];
    acc[d.severity].push(d);
    return acc;
  }, {});

  const severityOrder = ["critical", "high", "medium", "low"];

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-700">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-3 text-left"
      >
        <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          Deviations ({deviations.length})
        </span>
        <svg
          className={`h-4 w-4 text-zinc-400 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-zinc-200 px-3 pb-3 pt-2 space-y-2 dark:border-zinc-700">
          {severityOrder.map(
            (sev) =>
              grouped[sev] &&
              grouped[sev].map((dev, i) => (
                <div
                  key={`${sev}-${i}`}
                  className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-800/50"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <RiskBadge severity={dev.severity as "low" | "medium" | "high" | "critical"} />
                    <span className="text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">
                      {dev.component.replace(/_/g, " ")}
                    </span>
                    {oemActive && dev.reference != null && (
                      <span className="ml-auto rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-200">
                        OEM Spec
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">
                    {dev.description}
                  </p>
                  {dev.estimated != null && dev.reference != null && (
                    <div className="mt-2 grid grid-cols-3 gap-2 rounded-md bg-white px-3 py-2 text-[11px] dark:bg-zinc-900">
                      <div>
                        <span className="text-zinc-400">Estimated</span>
                        <p className="font-semibold tabular-nums text-zinc-700 dark:text-zinc-200">
                          {dev.estimated}{dev.component.includes("mm") ? "" : " mm"}
                        </p>
                      </div>
                      <div>
                        <span className="text-zinc-400">Reference</span>
                        <p className="font-semibold tabular-nums text-zinc-700 dark:text-zinc-200">
                          {dev.reference}{dev.component.includes("mm") ? "" : " mm"}
                        </p>
                      </div>
                      <div>
                        <span className="text-zinc-400">Delta</span>
                        <p className={`font-semibold tabular-nums ${dev.delta_pct != null && Math.abs(dev.delta_pct) > 5 ? "text-red-600 dark:text-red-400" : dev.delta_pct != null && Math.abs(dev.delta_pct) > 2 ? "text-amber-600 dark:text-amber-400" : "text-green-600 dark:text-green-400"}`}>
                          {dev.delta != null ? `${dev.delta > 0 ? "+" : ""}${dev.delta}` : "—"}
                          {dev.delta_pct != null ? ` (${dev.delta_pct > 0 ? "+" : ""}${dev.delta_pct}%)` : ""}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))
          )}
        </div>
      )}
    </div>
  );
}

function RecommendationsSection({
  recommendations,
}: {
  recommendations: NonNullable<AssessmentData["recommendations"]>;
}) {
  if (recommendations.length === 0) {
    return (
      <p className="text-sm text-zinc-400 italic">
        No recommendations generated.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {recommendations.map((rec, i) => (
        <RecommendationCard key={i} recommendation={rec} />
      ))}
    </div>
  );
}

export default function AssessmentResult({
  assessment,
  jobId,
  onConfirm,
}: Props) {
  const [showConfirm, setShowConfirm] = useState(
    assessment.needs_confirmation
  );
  const [cadLoading, setCadLoading] = useState<string | null>(null);

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

  const handleConfirm = async (selection: string) => {
    if (!assessment.confirmation_required) return;
    await onConfirm(assessment.confirmation_required.type, selection);
    setShowConfirm(false);
  };

  const handleConfirmTimeout = async () => {
    if (!jobId) return;
    try {
      const key = getApiKey();
      const headers: Record<string, string> = {};
      if (key) headers["X-API-Key"] = key;
      await fetch(`http://localhost:8000/api/v1/jobs/${jobId}/confirm-timeout`, {
        method: "POST",
        headers,
      });
    } catch {
      // Best-effort — result will show partial_assessment on next poll
    }
    setShowConfirm(false);
  };

  const stateColor =
    ASSESSMENT_STATE_COLORS[assessment.assessment_state] ??
    "bg-zinc-100 text-zinc-800 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-600";

  return (
    <>
      <div className="mx-auto mt-8 w-full max-w-3xl space-y-6">
        <div className="rounded-xl border bg-white p-6 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                Assessment Complete
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Job {jobId.slice(0, 8)}…
              </p>
            </div>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-medium ${stateColor}`}
            >
              {ASSESSMENT_STATE_LABELS[assessment.assessment_state] ??
                assessment.assessment_state?.replace(/_/g, " ")}
            </span>
          </div>

          {assessment.degradations && assessment.degradations.length > 0 && (
            <div className="mb-6 space-y-2">
              {assessment.degradations.map((d, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs dark:border-amber-800 dark:bg-amber-950"
                >
                  <span className="font-medium text-amber-800 dark:text-amber-200">
                    {(d.service ?? d.component ?? "").replace(/_/g, " ")}
                  </span>
                  {d.fallback && (
                    <span className="text-amber-700 dark:text-amber-300">
                      {" — "}Using {String(d.fallback).replace(/_/g, " ")}
                    </span>
                  )}
                  {d.message && (
                    <p className="mt-0.5 text-amber-600 dark:text-amber-400">
                      {d.message}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="mb-6 flex flex-col items-center">
            <FeasibilityGauge score={assessment.feasibility_score} />
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              {FEASIBILITY_LABELS[assessment.feasibility_label] ??
                assessment.feasibility_label?.replace(/_/g, " ")}
            </p>
          </div>

          {assessment.digital_twin && (
            <div className="mb-6 rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
              <div className="flex items-center gap-2 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
                <svg className="h-4 w-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  Digital Twin — 3D Vehicle View
                </h3>
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                  {(assessment.digital_twin as DigitalTwinData).deviations_3d.length} deviation{(assessment.digital_twin as DigitalTwinData).deviations_3d.length !== 1 ? "s" : ""}
                </span>
              </div>
              <DigitalTwinScene twinData={assessment.digital_twin as DigitalTwinData} />
            </div>
          )}

          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
              <p className="text-xs font-medium text-zinc-500">
                Vehicle Classification
              </p>
              {assessment.vehicle_classification ? (
                <>
                  <p className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    {assessment.vehicle_classification.type?.replace(
                      /_/g,
                      " "
                    )}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-400">
                    <span>
                      {Math.round(
                        assessment.vehicle_classification.confidence * 100
                      )}%
                    </span>
                    <span className="inline-block h-1 w-1 rounded-full bg-zinc-300" />
                    <span>
                      {assessment.vehicle_classification.classifier}
                    </span>
                    {assessment.vehicle_classification.human_confirmed && (
                      <>
                        <span className="inline-block h-1 w-1 rounded-full bg-zinc-300" />
                        <span className="font-medium text-amber-600">
                          Human confirmed
                        </span>
                      </>
                    )}
                  </div>
                </>
              ) : (
                <p className="mt-1 text-sm italic text-zinc-400">N/A</p>
              )}
            </div>
            <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
              <p className="text-xs font-medium text-zinc-500">Risk Summary</p>
              {assessment.risk_summary ? (
                <>
                  <p className="mt-1 text-sm capitalize text-zinc-700 dark:text-zinc-300">
                    {assessment.risk_summary.system_risk_state?.replace(
                      /_/g,
                      " "
                    )}
                  </p>
                  <div className="mt-1.5 flex gap-3 text-xs">
                    <span className="font-semibold text-red-600">
                      Critical:{" "}
                      {assessment.risk_summary.critical_count || 0}
                    </span>
                    <span className="font-semibold text-orange-600">
                      High: {assessment.risk_summary.high_count || 0}
                    </span>
                    <span className="font-semibold text-yellow-600">
                      Med: {assessment.risk_summary.medium_count || 0}
                    </span>
                    <span className="font-semibold text-zinc-500">
                      Low: {assessment.risk_summary.low_count || 0}
                    </span>
                  </div>
                </>
              ) : (
                <p className="mt-1 text-sm italic text-zinc-400">N/A</p>
              )}
            </div>
          </div>

          {assessment.confidence_factors && (
            <div className="mb-6">
              <h3 className="mb-3 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                Confidence Factors
              </h3>
              <div className="space-y-2">
                {Object.entries(assessment.confidence_factors).map(
                  ([key, value]) => (
                    <ConfidenceFactorBar
                      key={key}
                      label={key}
                      value={value}
                    />
                  )
                )}
              </div>
            </div>
          )}
        </div>

        {assessment.risk_register && assessment.risk_register.length > 0 && (
          <RiskRegisterSection risks={assessment.risk_register} />
        )}

        {assessment.deviations && assessment.deviations.length > 0 && (
          <DeviationsSection
            deviations={assessment.deviations}
            oemActive={assessment.deviations.some((d) => d.reference != null && d.estimated != null)}
          />
        )}

        {assessment.similar_retrofits && assessment.similar_retrofits.length > 0 && (
          <div className="rounded-xl border border-indigo-200 bg-white p-4 shadow-sm dark:border-indigo-800 dark:bg-zinc-900">
            <div className="mb-1 flex items-center gap-2">
              <svg className="h-4 w-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              <h3 className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">
                Retrofit DNA Match
              </h3>
              <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
                {assessment.similar_retrofits.length} found
              </span>
            </div>
            <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
              Vehicles with similar deviation patterns found in the knowledge graph
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {assessment.similar_retrofits.map((retrofit, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3 dark:border-indigo-900 dark:bg-indigo-950/30"
                >
                  <p className="text-xs font-medium text-indigo-700 dark:text-indigo-400">
                    {retrofit.type?.replace(/_/g, " ")}
                  </p>
                  <p className="mt-0.5 font-mono text-[10px] text-zinc-500">
                    {retrofit.vehicle_id?.slice(0, 8)}…
                  </p>
                  <div className="mt-2 flex items-center gap-3 text-[10px] text-zinc-600 dark:text-zinc-400">
                    <span>{retrofit.matching_deviations} match{retrofit.matching_deviations !== 1 ? "es" : ""}</span>
                    <span>·</span>
                    <span>{Math.round((retrofit.confidence ?? 0) * 100)}% confidence</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3">
              <Link
                href="/knowledge-graph"
                className="text-[11px] font-medium text-indigo-600 underline underline-offset-2 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300"
              >
                View all in Knowledge Graph →
              </Link>
            </div>
          </div>
        )}
        {(!assessment.similar_retrofits || assessment.similar_retrofits.length === 0) && (
          <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/30 p-4 shadow-sm dark:border-indigo-800 dark:bg-indigo-950/10">
            <div className="flex items-center gap-2">
              <svg className="h-4 w-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">
                Retrofit DNA Match
              </h3>
            </div>
            <p className="mt-2 text-xs font-medium text-indigo-600 dark:text-indigo-400">
              New Pattern
            </p>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              No similar retrofit patterns found in the knowledge graph.
            </p>
          </div>
        )}

        {assessment.enhanced_views && assessment.enhanced_views.length > 0 && (
          <div className="rounded-xl border border-emerald-200 bg-white p-4 shadow-sm dark:border-emerald-800 dark:bg-zinc-900">
            <div className="mb-3 flex items-center gap-2">
              <svg className="h-4 w-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <h3 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                Low-Light Auto-Enhancement
              </h3>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                {assessment.enhanced_views.length} view{assessment.enhanced_views.length !== 1 ? "s" : ""}
              </span>
            </div>
            <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
              The following views were captured in low-light conditions and automatically enhanced before analysis
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {assessment.enhanced_views.map((ev) => (
                <div key={ev.view} className="rounded-lg border border-emerald-100 bg-emerald-50/30 p-3 dark:border-emerald-900 dark:bg-emerald-950/20">
                  <p className="mb-2 text-xs font-medium text-emerald-700 dark:text-emerald-400">
                    {({ left_side_profile: "Left Side Profile", right_side_profile: "Right Side Profile", front_view: "Front View", rear_view: "Rear View", engine_bay: "Engine Bay", underbody: "Underbody" } as Record<string, string>)[ev.view] || ev.view.replace(/_/g, " ")}
                  </p>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <p className="mb-1 text-[10px] text-zinc-400 uppercase tracking-wide">Original</p>
                      <img
                        src={`http://localhost:8000${ev.original_url}`}
                        alt={`Original ${ev.view}`}
                        className="w-full rounded border border-zinc-200 object-cover dark:border-zinc-700"
                        style={{ aspectRatio: "4/3" }}
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                    <div className="flex-1">
                      <p className="mb-1 text-[10px] text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">Enhanced</p>
                      <img
                        src={`http://localhost:8000${ev.enhanced_url}`}
                        alt={`Enhanced ${ev.view}`}
                        className="w-full rounded border border-emerald-300 object-cover dark:border-emerald-700"
                        style={{ aspectRatio: "4/3" }}
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-xl border bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
          <h3 className="mb-3 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Recommendations
          </h3>
          {assessment.recommendations &&
          assessment.recommendations.length > 0 ? (
            <RecommendationsSection
              recommendations={assessment.recommendations}
            />
          ) : (
            <p className="text-sm text-zinc-400 italic">
              No recommendations generated.
            </p>
          )}
        </div>

        <div className="flex items-center justify-center gap-3 text-xs text-zinc-400">
          <span>Job ID: {jobId}</span>
          <span className="text-zinc-300 dark:text-zinc-600">·</span>
          <Link
            href={`/reports/${jobId}`}
            className="font-medium text-blue-600 underline underline-offset-2 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          >
            View Compliance Report
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">·</span>
          <Link
            href="/knowledge-graph"
            className="font-medium text-violet-600 underline underline-offset-2 hover:text-violet-800 dark:text-violet-400 dark:hover:text-violet-300"
          >
            Knowledge Graph
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">·</span>
          <button
            type="button"
            disabled={cadLoading !== null}
            onClick={() => handleCadDownload("step")}
            className="font-medium text-emerald-600 underline underline-offset-2 hover:text-emerald-800 disabled:opacity-40 dark:text-emerald-400 dark:hover:text-emerald-300"
          >
            {cadLoading === "step" ? "Downloading..." : "Download STEP"}
          </button>
          <span className="text-zinc-300 dark:text-zinc-600">·</span>
          <button
            type="button"
            disabled={cadLoading !== null}
            onClick={() => handleCadDownload("stl")}
            className="font-medium text-emerald-600 underline underline-offset-2 hover:text-emerald-800 disabled:opacity-40 dark:text-emerald-400 dark:hover:text-emerald-300"
          >
            {cadLoading === "stl" ? "Downloading..." : "Download STL"}
          </button>
        </div>
      </div>

      {showConfirm && assessment.confirmation_required && (
        <ConfirmDialog
          confirmation={assessment.confirmation_required}
          onConfirm={handleConfirm}
          onDismiss={() => setShowConfirm(false)}
          onTimeout={handleConfirmTimeout}
        />
      )}
    </>
  );
}
