"use client";

import { useEffect, useRef, useState } from "react";
import { getApiKey } from "@/utils/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type JobEvent = {
  event: string;
  data: {
    job_id: string;
    status: string;
    current_stage?: string;
    progress_pct?: number;
    completed_stages?: string[];
    message?: string;
  };
};

export function useJobSSE(
  jobId: string | null,
  options?: { fallbackPollMs?: number }
) {
  const fallbackMs = options?.fallbackPollMs ?? 2000;
  const [event, setEvent] = useState<JobEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttempt = useRef(0);

  useEffect(() => {
    if (!jobId) return;

    const apiKey = getApiKey();

    let useSSE = typeof EventSource !== "undefined" && !!apiKey;

    if (useSSE) {
      const url = new URL(`${API_BASE}/jobs/${jobId}/events`);
      url.searchParams.set("token", apiKey);
      const es = new EventSource(url.toString());
      esRef.current = es;

      es.onopen = () => {
        setConnected(true);
        reconnectAttempt.current = 0;
      };

      es.onmessage = (msg) => {
        try {
          const parsed: JobEvent = JSON.parse(msg.data);
          setEvent(parsed);
          setConnected(true);
          if (
            ["completed", "partial_complete", "failed", "timed_out", "cancelled"].includes(
              parsed.data?.status || ""
            )
          ) {
            es.close();
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        reconnectAttempt.current += 1;
        if (reconnectAttempt.current > 5) {
          es.close();
          useSSE = false;
          setConnected(false);
          startPolling();
          return;
        }
        setConnected(false);
      };
    }

    const currentJobId = jobId;
    function startPolling() {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/jobs/${currentJobId}`, {
            headers: { "X-API-Key": apiKey },
          });
          if (!res.ok) return;
          const data = await res.json();
          setEvent({
            event: "job.progress",
            data: {
              job_id: currentJobId,
              status: data.status,
              current_stage: data.current_stage,
              progress_pct: data.progress_pct,
              completed_stages: data.completed_stages,
            },
          });
          if (
            ["completed", "partial_complete", "failed", "timed_out", "cancelled"].includes(
              data.status
            )
          ) {
            if (pollRef.current) clearInterval(pollRef.current);
          }
        } catch (e: unknown) {
          setError(e instanceof Error ? e.message : "Poll error");
        }
      }, fallbackMs);
    }

    if (!useSSE) {
      startPolling();
    }

    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobId, fallbackMs]);

  return { event, connected, error };
}
