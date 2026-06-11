"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type HealthResponse = {
  status: string;
  services: Record<string, string>;
  version: string;
  timestamp: string;
};

export default function ApiHealthPage() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-8 px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight">System Health</h1>
      {error && (
        <div className="w-full max-w-md rounded-lg border border-red-300 bg-red-50 p-4 text-red-800 dark:border-red-700 dark:bg-red-950 dark:text-red-200">
          <p className="font-semibold">Connection Error</p>
          <p className="text-sm">{error}</p>
        </div>
      )}
      {data && (
        <pre className="w-full max-w-md rounded-lg border bg-zinc-50 p-4 text-sm dark:border-zinc-700 dark:bg-zinc-900">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
      {!data && !error && (
        <p className="text-zinc-400">Loading health status...</p>
      )}
    </div>
  );
}
