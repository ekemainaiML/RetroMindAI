"use client";

import { useCallback } from "react";
import { useJobPolling, type JobState } from "@/app/hooks/useJobPolling";
import { ensureApiKey } from "@/utils/api";
import type { AssessmentData } from "@/types/assessment";

function parseResult(
  jobState: JobState | null
): AssessmentData | null {
  if (!jobState?.result) return null;
  return jobState.result as unknown as AssessmentData;
}

export function useAssessment(jobId: string | null) {
  const { jobState, error, softTimedOut, isExpired, refresh } = useJobPolling(jobId);

  const assessment = parseResult(jobState);

  const confirm = useCallback(
    async (confirmationType: string, selection: string) => {
      if (!jobId) throw new Error("No active job");
      const key = await ensureApiKey();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (key) headers["X-API-Key"] = key;
      const res = await fetch(
        `http://localhost:8000/api/v1/jobs/${jobId}/confirm`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({
            confirmation_type: confirmationType,
            selection,
          }),
        }
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Confirmation failed (${res.status}): ${text}`);
      }
      refresh();
    },
    [jobId, refresh]
  );

  return {
    job: jobState,
    assessment,
    loading: jobId !== null && !jobState?.result,
    error,
    softTimedOut,
    isExpired,
    confirm,
  };
}
