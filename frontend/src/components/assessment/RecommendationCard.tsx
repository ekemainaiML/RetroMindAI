"use client";

import { useState } from "react";
import type { Recommendation } from "@/types/assessment";

interface Props {
  recommendation: Recommendation;
}

const PRIORITY_STYLES: Record<string, string> = {
  essential:
    "bg-red-100 text-red-700 border-red-300 dark:bg-red-900 dark:text-red-300 dark:border-red-700",
  recommended:
    "bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900 dark:text-blue-300 dark:border-blue-700",
  optional:
    "bg-zinc-100 text-zinc-600 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-600",
};

const PRIORITY_LABELS: Record<string, string> = {
  essential: "Essential",
  recommended: "Recommended",
  optional: "Optional",
};

export default function RecommendationCard({
  recommendation,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const rec = recommendation;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white transition-colors hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between gap-3 p-4 text-left"
      >
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase ${PRIORITY_STYLES[rec.priority]}`}
            >
              {PRIORITY_LABELS[rec.priority]}
            </span>
            <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800 dark:bg-amber-900 dark:text-amber-200">
              {rec.category}
            </span>
            {rec.blocking && (
              <span className="rounded-md bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-900 dark:text-red-300">
                Blocking
              </span>
            )}
          </div>
          <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {rec.title}
          </h4>
        </div>

        <div className="flex shrink-0 items-center gap-3 text-xs text-zinc-400">
          {rec.estimated_days > 0 && (
            <span className="whitespace-nowrap">~{rec.estimated_days}d</span>
          )}
          {rec.cost_estimate && (
            <span className="whitespace-nowrap">
              {rec.cost_estimate.currency}
              {rec.cost_estimate.min}–{rec.cost_estimate.max}
            </span>
          )}
          <svg
            className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`}
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
        </div>
      </button>

      {expanded && (
        <div className="border-t border-zinc-200 px-4 pb-4 pt-3 dark:border-zinc-700">
          <p className="mb-3 text-sm text-zinc-600 dark:text-zinc-400">
            {rec.description}
          </p>

          {rec.rationale && rec.rationale.length > 0 && (
            <div className="mb-3">
              <p className="mb-1 text-xs font-medium text-zinc-500 dark:text-zinc-400">
                Rationale
              </p>
              <ul className="list-disc space-y-1 pl-4 text-xs text-zinc-600 dark:text-zinc-400">
                {rec.rationale.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </div>
          )}

          {rec.depends_on && rec.depends_on.length > 0 && (
            <div className="mb-3">
              <p className="mb-1 text-xs font-medium text-zinc-500 dark:text-zinc-400">
                Depends on
              </p>
              <div className="flex flex-wrap gap-1.5">
                {rec.depends_on.map((dep, i) => (
                  <span
                    key={i}
                    className="rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300"
                  >
                    {dep}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
