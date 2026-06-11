"use client";

import { useCallback, useEffect, useState } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";

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
  const [loading, setLoading] = useState(true);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchHealth(); }, [fetchHealth]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-8 animate-fade-in">
      <PageHeader title="System Health" subtitle="Backend service status and version info" />
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={fetchHealth} loading={loading}>Refresh</Button>
      </div>
      {error ? (
        <Card className="border-danger/30">
          <p className="text-sm font-semibold text-danger">Connection Error</p>
          <p className="mt-1 text-xs text-danger">{error}</p>
        </Card>
      ) : data ? (
        <Card>
          <div className="space-y-2">
            <div className="flex justify-between text-sm"><span className="text-text-secondary">Status</span><Badge variant={data.status === "healthy" ? "success" : "danger"}>{data.status}</Badge></div>
            <div className="flex justify-between text-sm"><span className="text-text-secondary">Version</span><span className="font-mono text-xs text-text-primary">{data.version}</span></div>
            <div className="flex justify-between text-sm"><span className="text-text-secondary">Timestamp</span><span className="text-xs text-text-tertiary">{new Date(data.timestamp).toLocaleString()}</span></div>
          </div>
          {Object.keys(data.services).length > 0 && (
            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-xs font-medium text-text-secondary uppercase tracking-wider">Services</p>
              <div className="space-y-1.5">
                {Object.entries(data.services).map(([name, status]) => (
                  <div key={name} className="flex justify-between text-xs">
                    <span className="text-text-primary">{name}</span>
                    <span className={status === "ok" ? "text-success" : "text-danger"}>{status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      ) : (
        <p className="text-center text-xs text-text-tertiary py-12">Loading health status...</p>
      )}
    </div>
  );
}
