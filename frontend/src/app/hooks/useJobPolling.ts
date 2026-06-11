"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, ensureApiKey, recoverWithDemoKey } from "@/utils/api";

export type JobState = {
  job_id: string;
  status: string;
  current_stage: string | null;
  progress_pct: number;
  assessment_state: string | null;
  completed_stages: string[];
  missing_stages: string[];
  result: Record<string, unknown> | null;
  retry_count: number;
  retry_available: boolean;
  error_message: string | null;
  timed_out: boolean;
  infrastructure_degradation: Array<{
    service: string;
    severity: string;
    fallback?: string;
    message?: string;
  }>;
  created_at: string | null;
  updated_at: string | null;
};

const TERMINAL_STATUSES = [
  "completed",
  "partial_complete",
  "failed",
  "timed_out",
  "cancelled",
  "expired",
];

const SOFT_TIMEOUT_MS = 90_000;
const EXPIRY_MS = 1_800_000;

export function useJobPolling(jobId: string | null) {
  const [jobState, setJobState] = useState<JobState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [softTimedOut, setSoftTimedOut] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollStartRef = useRef<number | null>(null);
  const fetchJobRef = useRef<(() => Promise<void>) | null>(null);

  const refresh = useCallback(() => {
    if (fetchJobRef.current) fetchJobRef.current();
  }, []);

  useEffect(() => {
    if (!jobId) {
      setJobState(null);
      setError(null);
      setSoftTimedOut(false);
      return;
    }

    pollStartRef.current = Date.now();
    setSoftTimedOut(false);

    const fetchJob = async () => {
      try {
        const key = await ensureApiKey();
        const headers: Record<string, string> = {};
        if (key) headers["X-API-Key"] = key;
        const res = await fetch(
          `${API_BASE}/jobs/${jobId}`,
          { headers }
        );
        if (!res.ok) {
          if (res.status === 404) {
            localStorage.removeItem("retromind_active_job_id");
            throw new Error("Job not found");
          }
          if (res.status === 401) {
            localStorage.removeItem("retromind_active_job_id");
            const demoKey = await recoverWithDemoKey();
            if (demoKey) {
              throw new Error("API key was stale. Retrying...");
            }
            throw new Error("Authentication failed. Use the Auth page to re-enter your API key.");
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data: JobState = await res.json();
        setJobState(data);
        setError(null);

        const elapsed = Date.now() - (pollStartRef.current ?? Date.now());
        if (elapsed > EXPIRY_MS) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return;
        }
        if (elapsed > SOFT_TIMEOUT_MS && !data.timed_out) {
          setSoftTimedOut(true);
        }

        if (TERMINAL_STATUSES.includes(data.status)) {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Polling error");
      }
    };

    fetchJobRef.current = fetchJob;
    fetchJob();

    intervalRef.current = setInterval(fetchJob, 2_000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId]);

  return { jobState, error, softTimedOut, isExpired: false, refresh };
}
