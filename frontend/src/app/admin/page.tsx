"use client";

import { useCallback, useEffect, useState } from "react";
import Card, { CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";
import { getApiKey } from "@/utils/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type WorkshopItem = {
  id: string;
  name: string;
  api_key_prefix: string;
  is_active: boolean;
  intake_count: number;
  created_at: string;
};

type AuditLogItem = {
  id: string;
  workshop_id: string | null;
  method: string;
  path: string;
  status_code: string;
  duration_ms: string | null;
  ip_address: string | null;
  created_at: string;
};

type Metrics = {
  total_workshops: number;
  total_intakes: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  timed_out_jobs: number;
  active_jobs: number;
  unique_workshops_24h: number;
};

type Tab = "metrics" | "workshops" | "users" | "audit-logs" | "oem";

type UserItem = {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  workshop_count: number;
  created_at: string;
};

const ADMIN_KEY_STORAGE = "retromind_admin_key";

function getStoredAdminKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(ADMIN_KEY_STORAGE) || "";
}

function setStoredAdminKey(key: string) {
  localStorage.setItem(ADMIN_KEY_STORAGE, key);
}

async function apiFetch<T>(path: string, key?: string): Promise<T> {
  const k = key || getStoredAdminKey();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "X-API-Key": k },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("metrics");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [workshops, setWorkshops] = useState<WorkshopItem[]>([]);
  const [workshopTotal, setWorkshopTotal] = useState(0);
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [logTotal, setLogTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [methodFilter, setMethodFilter] = useState("");
  const [codeFilter, setCodeFilter] = useState("");
  const [users, setUsers] = useState<UserItem[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [logOffset, setLogOffset] = useState(0);
  const [adminKeyInput, setAdminKeyInput] = useState(getStoredAdminKey());
  const [authenticated, setAuthenticated] = useState(false);
  const LOG_LIMIT = 50;

  const load = useCallback(async (keyOverride?: string) => {
    setError(null);
    const effectiveKey = keyOverride || getStoredAdminKey();
    if (!effectiveKey) return;
    try {
      if (tab === "metrics") setMetrics(await apiFetch<Metrics>("/admin/metrics", effectiveKey));
      else if (tab === "workshops") {
        const r = await apiFetch<{ workshops: WorkshopItem[]; total: number }>("/admin/workshops?limit=100", effectiveKey);
        setWorkshops(r.workshops);
        setWorkshopTotal(r.total);
      } else if (tab === "users") {
        const r = await apiFetch<{ users: UserItem[]; total: number }>("/admin/users?limit=100", effectiveKey);
        setUsers(r.users);
        setUserTotal(r.total);
      } else if (tab === "audit-logs") {
        const p = new URLSearchParams({ limit: String(LOG_LIMIT), offset: String(logOffset) });
        if (methodFilter) p.set("method", methodFilter);
        if (codeFilter) p.set("status_code", codeFilter);
        const r = await apiFetch<{ logs: AuditLogItem[]; total: number }>(`/admin/audit-logs?${p}`, effectiveKey);
        setLogs(r.logs);
        setLogTotal(r.total);
      }
      setAuthenticated(true);
    } catch (e: unknown) {
      setAuthenticated(false);
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }, [tab, logOffset, methodFilter, codeFilter]);

  useEffect(() => {
    const stored = getStoredAdminKey();
    if (stored) load(stored);
  }, [load]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "metrics", label: "Metrics" },
    { key: "workshops", label: "Workshops" },
    { key: "users", label: "Users" },
    { key: "audit-logs", label: "Audit Logs" },
    { key: "oem", label: "OEM Data" },
  ];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 animate-fade-in">
      <PageHeader title="Admin Dashboard" subtitle="System-wide monitoring and management" />

      <div className="flex gap-1 rounded-lg bg-surface-muted p-1 border border-border w-fit">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => { setTab(key); setLogOffset(0); }}
            className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${
              tab === key
                ? "bg-surface-card text-text-primary shadow-sm border border-border"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {!authenticated && (
        <Card>
          <h2 className="text-sm font-semibold text-text-primary mb-2">Admin API Key Required</h2>
          <p className="text-xs text-text-secondary mb-4">
            Enter the admin API key or your workshop API key to access the dashboard.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={adminKeyInput}
              onChange={(e) => setAdminKeyInput(e.target.value)}
              placeholder="Enter API key..."
              className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
              onKeyDown={(e) => {
                if (e.key === "Enter" && adminKeyInput) {
                  setStoredAdminKey(adminKeyInput);
                  load(adminKeyInput);
                }
              }}
            />
            <Button
              onClick={() => { setStoredAdminKey(adminKeyInput); load(adminKeyInput); }}
              disabled={!adminKeyInput}
              variant="primary"
            >
              Authenticate
            </Button>
          </div>
          {error && <p className="mt-3 text-xs text-danger">{error}</p>}
        </Card>
      )}

      {authenticated && error && (
        <Card className="border-danger/30">
          <p className="text-sm font-semibold text-danger">Error</p>
          <p className="text-xs text-danger mt-1">{error}</p>
        </Card>
      )}

      {authenticated && tab === "metrics" && metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Workshops" value={metrics.total_workshops} />
          <MetricCard label="Intakes" value={metrics.total_intakes} />
          <MetricCard label="Total Jobs" value={metrics.total_jobs} />
          <MetricCard label="Completed" value={metrics.completed_jobs} />
          <MetricCard label="Failed" value={metrics.failed_jobs} />
          <MetricCard label="Timed Out" value={metrics.timed_out_jobs} />
          <MetricCard label="Active" value={metrics.active_jobs} />
          <MetricCard label="Active Workshops (24h)" value={metrics.unique_workshops_24h} />
        </div>
      )}

      {authenticated && tab === "workshops" && (
        <Card padding="none">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                <TH>Name</TH>
                <TH>Key Prefix</TH>
                <TH>Active</TH>
                <TH>Intakes</TH>
                <TH>Created</TH>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {workshops.map((w) => (
                <tr key={w.id} className="hover:bg-surface-hover transition-colors">
                  <TD>{w.name}</TD>
                  <TD className="font-mono text-xs text-text-secondary">{w.api_key_prefix}...</TD>
                  <TD>{w.is_active ? <Badge variant="success" size="sm">Active</Badge> : <Badge variant="default" size="sm">Inactive</Badge>}</TD>
                  <TD className="text-text-secondary">{w.intake_count}</TD>
                  <TD className="text-xs text-text-tertiary">{new Date(w.created_at).toLocaleDateString()}</TD>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-border px-4 py-2 text-xs text-text-tertiary">
            {workshopTotal} total workshop(s)
          </div>
        </Card>
      )}

      {authenticated && tab === "users" && (
        <Card padding="none">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                <TH>Name</TH>
                <TH>Email</TH>
                <TH>Status</TH>
                <TH>Workshops</TH>
                <TH>Created</TH>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-surface-hover transition-colors">
                  <TD>{u.name}</TD>
                  <TD className="text-xs text-text-secondary">{u.email}</TD>
                  <TD>{u.is_active ? <Badge variant="success" size="sm">Active</Badge> : <Badge variant="default" size="sm">Inactive</Badge>}</TD>
                  <TD className="text-text-secondary">{u.workshop_count}</TD>
                  <TD className="text-xs text-text-tertiary">{new Date(u.created_at).toLocaleDateString()}</TD>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-border px-4 py-2 text-xs text-text-tertiary">
            {userTotal} total user(s)
          </div>
        </Card>
      )}

      {authenticated && tab === "audit-logs" && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <select
              value={methodFilter}
              onChange={(e) => { setMethodFilter(e.target.value); setLogOffset(0); }}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30"
            >
              <option value="">All Methods</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
            <select
              value={codeFilter}
              onChange={(e) => { setCodeFilter(e.target.value); setLogOffset(0); }}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30"
            >
              <option value="">All Status</option>
              <option value="200">200</option>
              <option value="201">201</option>
              <option value="400">400</option>
              <option value="401">401</option>
              <option value="404">404</option>
              <option value="500">500</option>
            </select>
          </div>
          <Card padding="none">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-[10px] uppercase tracking-wider text-text-tertiary">
                  <TH>Time</TH>
                  <TH>Method</TH>
                  <TH>Path</TH>
                  <TH>Status</TH>
                  <TH>Duration</TH>
                  <TH>Workshop</TH>
                  <TH>IP</TH>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((l) => (
                  <tr key={l.id} className="hover:bg-surface-hover transition-colors">
                    <TD>{new Date(l.created_at).toLocaleTimeString()}</TD>
                    <TD className="font-medium text-text-primary">{l.method}</TD>
                    <TD className="max-w-[300px] truncate text-text-secondary">{l.path}</TD>
                    <TD>
                      <StatusCodeBadge code={l.status_code} />
                    </TD>
                    <TD className="text-text-tertiary">{l.duration_ms}ms</TD>
                    <TD className="font-mono text-text-tertiary">{l.workshop_id ? l.workshop_id.slice(0, 8) : "-"}</TD>
                    <TD className="text-text-tertiary">{l.ip_address || "-"}</TD>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div className="flex items-center justify-between">
            <Button
              onClick={() => setLogOffset(Math.max(0, logOffset - LOG_LIMIT))}
              disabled={logOffset === 0}
              variant="secondary"
              size="sm"
            >
              Previous
            </Button>
            <span className="text-xs text-text-tertiary">
              {logOffset + 1}&ndash;{Math.min(logOffset + LOG_LIMIT, logTotal)} of {logTotal}
            </span>
            <Button
              onClick={() => setLogOffset(logOffset + LOG_LIMIT)}
              disabled={logOffset + LOG_LIMIT >= logTotal}
              variant="secondary"
              size="sm"
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {authenticated && tab === "oem" && (
        <OemAdminContent
          apiBase={API_BASE}
          apiKey={getApiKey()}
        />
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wider text-text-tertiary">{label}</p>
      <p className="mt-1 text-2xl font-bold text-text-primary">{value}</p>
    </Card>
  );
}

function StatusCodeBadge({ code }: { code: string }) {
  const variant = code.startsWith("2") ? "success" : code.startsWith("4") ? "warning" : "danger";
  return <Badge variant={variant} size="sm">{code}</Badge>;
}

function TH({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-3 text-left font-medium">{children}</th>;
}

function TD({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 ${className}`}>{children}</td>;
}

function OemAdminContent({ apiBase, apiKey }: { apiBase: string; apiKey: string }) {
  const ak = apiKey;
  const h = { "X-API-Key": ak };
  type OEMTab = "manufacturers" | "models";
  const [oemTab, setOemTab] = useState<OEMTab>("manufacturers");
  const [manus, setManus] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [modelSearch, setModelSearch] = useState("");
  const [manuId, setManuId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formCountry, setFormCountry] = useState("");
  const [formYear, setFormYear] = useState("");
  const [formError, setFormError] = useState("");
  const [specs, setSpecs] = useState<any | null>(null);
  const [specsModelId, setSpecsModelId] = useState<string | null>(null);
  const [mountCount, setMountCount] = useState(0);
  const [routeCount, setRouteCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const loadManus = useCallback(async () => {
    setLoading(true);
    try {
      const q = search ? `?search=${encodeURIComponent(search)}` : "";
      const r = await fetch(`${apiBase}/oem/manufacturers${q}`, { headers: h });
      if (r.ok) setManus(await r.json());
    } finally { setLoading(false); }
  }, [apiBase, search]);

  useEffect(() => { loadManus(); }, [loadManus]);

  const loadModels = useCallback(async (mid: string) => {
    setManuId(mid);
    setLoading(true);
    try {
      const q = modelSearch ? `?search=${encodeURIComponent(modelSearch)}` : `?manufacturer_id=${mid}`;
      const r = await fetch(`${apiBase}/oem/models${q}`, { headers: h });
      if (r.ok) setModels(await r.json());
    } finally { setLoading(false); }
  }, [apiBase, modelSearch]);

  const loadDetail = useCallback(async (mid: string) => {
    try {
      const [s, mp, rp] = await Promise.all([
        fetch(`${apiBase}/oem/models/${mid}/specifications`, { headers: h }),
        fetch(`${apiBase}/oem/mounting-points?model_id=${mid}`, { headers: h }),
        fetch(`${apiBase}/oem/routing-paths?model_id=${mid}`, { headers: h }),
      ]);
      setSpecs(s.ok ? await s.json() : null);
      setSpecsModelId(mid);
      setMountCount(mp.ok ? (await mp.json()).length : 0);
      setRouteCount(rp.ok ? (await rp.json()).length : 0);
    } catch { setSpecs(null); }
  }, [apiBase]);

  const createManu = useCallback(async () => {
    setFormError("");
    if (!formName.trim()) { setFormError("Name is required"); return; }
    try {
      const r = await fetch(`${apiBase}/oem/manufacturers`, {
        method: "POST", headers: { ...h, "Content-Type": "application/json" },
        body: JSON.stringify({ name: formName.trim(), country: formCountry.trim() || null, founded_year: formYear ? parseInt(formYear) : null }),
      });
      if (!r.ok) throw new Error(await r.text());
      setFormOpen(false); setFormName(""); setFormCountry(""); setFormYear("");
      loadManus();
    } catch (e: unknown) { setFormError(e instanceof Error ? e.message : "Failed"); }
  }, [formName, formCountry, formYear, loadManus]);

  const delManu = useCallback(async (id: string) => {
    if (!confirm("Delete this manufacturer and all associated models?")) return;
    try {
      const r = await fetch(`${apiBase}/oem/manufacturers/${id}`, { method: "DELETE", headers: h });
      if (!r.ok) throw new Error(await r.text());
      loadManus();
    } catch (e: unknown) { alert(e instanceof Error ? e.message : "Delete failed"); }
  }, [loadManus]);

  const delModel = useCallback(async (id: string) => {
    if (!confirm("Delete this vehicle model?")) return;
    try {
      const r = await fetch(`${apiBase}/oem/models/${id}`, { method: "DELETE", headers: h });
      if (!r.ok) throw new Error(await r.text());
      if (manuId) loadModels(manuId);
    } catch (e: unknown) { alert(e instanceof Error ? e.message : "Delete failed"); }
  }, [manuId, loadModels]);

  const manuName = manuId ? manus.find((m: any) => m.id === manuId)?.name || "Unknown" : "";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-surface-muted p-1 border border-border">
          <button type="button" onClick={() => setOemTab("manufacturers")} className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${oemTab === "manufacturers" ? "bg-surface-card text-text-primary shadow-sm border border-border" : "text-text-tertiary hover:text-text-secondary"}`}>Manufacturers</button>
          <button type="button" onClick={() => setOemTab("models")} className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${oemTab === "models" ? "bg-surface-card text-text-primary shadow-sm border border-border" : "text-text-tertiary hover:text-text-secondary"}`}>Vehicle Models</button>
        </div>
        {oemTab === "manufacturers" && <Button size="sm" onClick={() => setFormOpen(true)}>+ Add Manufacturer</Button>}
      </div>

      {oemTab === "manufacturers" && (
        <div className="space-y-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search manufacturers..." className="max-w-xs" />
          <Card padding="none">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                  <TH>Name</TH>
                  <TH>Country</TH>
                  <TH>Founded</TH>
                  <TH>Models</TH>
                  <TH>Active</TH>
                  <TH>Actions</TH>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {manus.map((m: any) => (
                  <tr key={m.id} className="hover:bg-surface-hover transition-colors">
                    <TD className="font-medium text-text-primary">{m.name}</TD>
                    <TD className="text-text-secondary">{m.country || "-"}</TD>
                    <TD className="text-text-tertiary">{m.founded_year || "-"}</TD>
                    <TD>
                      <button type="button" onClick={() => { loadModels(m.id); setOemTab("models"); }} className="text-xs text-brand underline underline-offset-2 hover:text-brand-dark">
                        {m.model_count} model{m.model_count !== 1 ? "s" : ""}
                      </button>
                    </TD>
                    <TD>{m.is_active ? <Badge variant="success" size="sm">Active</Badge> : <Badge variant="default" size="sm">Inactive</Badge>}</TD>
                    <TD><button type="button" onClick={() => delManu(m.id)} className="text-xs text-danger underline underline-offset-2">Delete</button></TD>
                  </tr>
                ))}
              </tbody>
            </table>
            {manus.length === 0 && <p className="px-4 py-6 text-center text-xs text-text-tertiary">{loading ? "Loading..." : "No manufacturers found"}</p>}
          </Card>
        </div>
      )}

      {oemTab === "models" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setOemTab("manufacturers")} className="text-xs text-brand underline underline-offset-2 hover:text-brand-dark">&larr; Back to Manufacturers</button>
            {manuId && <span className="text-xs text-text-tertiary">{manuName}</span>}
          </div>
          <Input value={modelSearch} onChange={(e) => setModelSearch(e.target.value)} placeholder="Search models..." className="max-w-xs" />
          <Card padding="none">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                  <TH>Model</TH>
                  <TH>Generation</TH>
                  <TH>Type</TH>
                  <TH>Years</TH>
                  <TH>Specs</TH>
                  <TH>Mount</TH>
                  <TH>Routing</TH>
                  <TH>Actions</TH>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {models.map((m: any) => (
                  <tr key={m.id} className="hover:bg-surface-hover transition-colors">
                    <TD className="font-medium text-text-primary">{m.model_name}</TD>
                    <TD className="text-text-tertiary">{m.generation || "-"}</TD>
                    <TD><Badge variant="default" size="sm">{m.vehicle_type.replace(/_/g, " ")}</Badge></TD>
                    <TD className="text-xs text-text-tertiary">{m.year_start || "?"}{m.year_end ? `-${m.year_end}` : ""}</TD>
                    <TD>
                      <button type="button" onClick={() => loadDetail(m.id)} className="text-xs text-brand underline underline-offset-2 hover:text-brand-dark">
                        {m.spec_count || 0} {specsModelId === m.id ? "(viewing)" : ""}
                      </button>
                    </TD>
                    <TD className="text-xs text-text-tertiary">{specsModelId === m.id ? mountCount : "-"}</TD>
                    <TD className="text-xs text-text-tertiary">{specsModelId === m.id ? routeCount : "-"}</TD>
                    <TD><button type="button" onClick={() => delModel(m.id)} className="text-xs text-danger underline underline-offset-2">Delete</button></TD>
                  </tr>
                ))}
              </tbody>
            </table>
            {models.length === 0 && <p className="px-4 py-6 text-center text-xs text-text-tertiary">{loading ? "Loading..." : "No models found"}</p>}
          </Card>

          {specs && specsModelId && (
            <Card>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-text-primary">Specifications</h3>
                <button type="button" onClick={() => { setSpecs(null); setSpecsModelId(null); }} className="text-xs text-text-tertiary underline underline-offset-2">Close</button>
              </div>
              {Array.isArray(specs) && specs.length === 0 && <p className="text-xs text-text-tertiary">No specifications</p>}
              {Array.isArray(specs) && specs.map((spec: any, idx: number) => (
                <div key={idx} className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(spec).filter(([k]) => !["id", "model_id", "created_at", "notes"].includes(k)).map(([k, v]) => v != null ? (
                    <div key={k}>
                      <p className="text-[10px] uppercase tracking-wider text-text-tertiary">{k.replace(/_/g, " ")}</p>
                      <p className="text-sm font-semibold text-text-primary">{String(v)}{k.includes("mm") ? " mm" : k.includes("kg") ? " kg" : ""}</p>
                    </div>
                  ) : null)}
                </div>
              ))}
              {!Array.isArray(specs) && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(specs).filter(([k]) => !["id", "model_id", "created_at", "notes"].includes(k)).map(([k, v]) => v != null ? (
                    <div key={k}>
                      <p className="text-[10px] uppercase tracking-wider text-text-tertiary">{k.replace(/_/g, " ")}</p>
                      <p className="text-sm font-semibold text-text-primary">{String(v)}{k.includes("mm") ? " mm" : k.includes("kg") ? " kg" : ""}</p>
                    </div>
                  ) : null)}
                </div>
              )}
              {mountCount > 0 && <p className="mt-3 text-xs text-text-tertiary">{mountCount} mounting point(s)</p>}
              {routeCount > 0 && <p className="text-xs text-text-tertiary">{routeCount} routing path(s)</p>}
            </Card>
          )}
        </div>
      )}

      {formOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Add Manufacturer</h3>
            <div className="space-y-3">
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Manufacturer name *" />
              <Input value={formCountry} onChange={(e) => setFormCountry(e.target.value)} placeholder="Country (optional)" />
              <Input value={formYear} onChange={(e) => setFormYear(e.target.value)} placeholder="Founded year (optional)" type="number" />
              {formError && <p className="text-xs text-danger">{formError}</p>}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setFormOpen(false); setFormError(""); }}>Cancel</Button>
              <Button variant="primary" onClick={createManu}>Create</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
