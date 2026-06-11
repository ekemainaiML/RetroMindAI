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
  const h: Record<string, string> = { "X-API-Key": ak };
  const JSON_H = { ...h, "Content-Type": "application/json" };
  type OEMTab = "manufacturers" | "models";
  const [oemTab, setOemTab] = useState<OEMTab>("manufacturers");
  const [manus, setManus] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [modelSearch, setModelSearch] = useState("");
  const [manuId, setManuId] = useState<string | null>(null);
  const [manuOpen, setManuOpen] = useState(false);
  const [manuName, setManuName] = useState("");
  const [manuCountry, setManuCountry] = useState("");
  const [manuYear, setManuYear] = useState("");
  const [formError, setFormError] = useState("");
  const [specs, setSpecs] = useState<any[] | null>(null);
  const [mounts, setMounts] = useState<any[]>([]);
  const [routes, setRoutes] = useState<any[]>([]);
  const [specsModelId, setSpecsModelId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [modelOpen, setModelOpen] = useState(false);
  const [editModelId, setEditModelId] = useState<string | null>(null);
  const [modelForm, setModelForm] = useState({ model_name: "", generation: "", vehicle_type: "auto_rickshaw", year_start: "", year_end: "" });

  const [specOpen, setSpecOpen] = useState(false);
  const [editSpecId, setEditSpecId] = useState<string | null>(null);
  const [specForm, setSpecForm] = useState<Record<string, string>>({});

  const [mountOpen, setMountOpen] = useState(false);
  const [editMountId, setEditMountId] = useState<string | null>(null);
  const [mountForm, setMountForm] = useState({ point_name: "", point_type: "", position_x_mm: "", position_y_mm: "", position_z_mm: "", bolt_pattern: "", torque_spec_nm: "", notes: "" });

  const [routeOpen, setRouteOpen] = useState(false);
  const [editRouteId, setEditRouteId] = useState<string | null>(null);
  const [routeForm, setRouteForm] = useState({ path_name: "", path_type: "", start_point: "", end_point: "", length_estimate_mm: "", notes: "" });

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
    setSpecs(null); setSpecsModelId(null);
    try {
      const q = modelSearch ? `?search=${encodeURIComponent(modelSearch)}` : `?manufacturer_id=${mid}`;
      const r = await fetch(`${apiBase}/oem/models${q}`, { headers: h });
      if (r.ok) setModels(await r.json());
    } finally { setLoading(false); }
  }, [apiBase, modelSearch]);

  const loadDetail = useCallback(async (mid: string) => {
    try {
      const [sRes, mpRes, rpRes] = await Promise.all([
        fetch(`${apiBase}/oem/models/${mid}/specifications`, { headers: h }),
        fetch(`${apiBase}/oem/mounting-points?model_id=${mid}`, { headers: h }),
        fetch(`${apiBase}/oem/routing-paths?model_id=${mid}`, { headers: h }),
      ]);
      setSpecs(sRes.ok ? await sRes.json() : []);
      setMounts(mpRes.ok ? await mpRes.json() : []);
      setRoutes(rpRes.ok ? await rpRes.json() : []);
      setSpecsModelId(mid);
    } catch { setSpecs(null); }
  }, [apiBase]);

  const createManu = useCallback(async () => {
    setFormError("");
    if (!manuName.trim()) { setFormError("Name is required"); return; }
    try {
      const r = await fetch(`${apiBase}/oem/manufacturers`, {
        method: "POST", headers: JSON_H,
        body: JSON.stringify({ name: manuName.trim(), country: manuCountry.trim() || null, founded_year: manuYear ? parseInt(manuYear) : null }),
      });
      if (!r.ok) throw new Error(await r.text());
      setManuOpen(false); setManuName(""); setManuCountry(""); setManuYear("");
      loadManus();
    } catch (e: unknown) { setFormError(e instanceof Error ? e.message : "Failed"); }
  }, [manuName, manuCountry, manuYear, loadManus]);

  const delManu = useCallback(async (id: string) => {
    if (!confirm("Delete this manufacturer and all associated models?")) return;
    try {
      const r = await fetch(`${apiBase}/oem/manufacturers/${id}`, { method: "DELETE", headers: h });
      if (!r.ok) throw new Error(await r.text());
      loadManus();
    } catch (e: unknown) { alert(e instanceof Error ? e.message : "Delete failed"); }
  }, [loadManus]);

  const saveModel = useCallback(async () => {
    setFormError("");
    if (!modelForm.model_name.trim()) { setFormError("Model name is required"); return; }
    if (!manuId) { setFormError("No manufacturer selected"); return; }
    try {
      const body: Record<string, any> = {
        model_name: modelForm.model_name.trim(),
        vehicle_type: modelForm.vehicle_type,
      };
      if (editModelId) {
        if (modelForm.generation) body.generation = modelForm.generation;
        if (modelForm.year_start) body.year_start = parseInt(modelForm.year_start);
        if (modelForm.year_end) body.year_end = parseInt(modelForm.year_end);
      } else {
        body.manufacturer_id = manuId;
        body.generation = modelForm.generation || null;
        if (modelForm.year_start) body.year_start = parseInt(modelForm.year_start);
        if (modelForm.year_end) body.year_end = parseInt(modelForm.year_end);
      }

      const url = editModelId ? `${apiBase}/oem/models/${editModelId}` : `${apiBase}/oem/models`;
      const method = editModelId ? "PUT" : "POST";
      const r = await fetch(url, { method, headers: JSON_H, body: JSON.stringify(body) });
      if (!r.ok) throw new Error(await r.text());
      setModelOpen(false); setEditModelId(null);
      setModelForm({ model_name: "", generation: "", vehicle_type: "auto_rickshaw", year_start: "", year_end: "" });
      loadModels(manuId);
    } catch (e: unknown) { setFormError(e instanceof Error ? e.message : "Failed"); }
  }, [modelForm, manuId, editModelId, loadModels]);

  const delModel = useCallback(async (id: string) => {
    if (!confirm("Delete this vehicle model?")) return;
    try {
      const r = await fetch(`${apiBase}/oem/models/${id}`, { method: "DELETE", headers: h });
      if (!r.ok) throw new Error(await r.text());
      if (manuId) loadModels(manuId);
      if (specsModelId === id) { setSpecs(null); setSpecsModelId(null); }
    } catch (e: unknown) { alert(e instanceof Error ? e.message : "Delete failed"); }
  }, [manuId, loadModels, specsModelId]);

  const openModelModal = useCallback((model?: any) => {
    if (model) {
      setEditModelId(model.id);
      setModelForm({
        model_name: model.model_name || "",
        generation: model.generation || "",
        vehicle_type: model.vehicle_type || "auto_rickshaw",
        year_start: model.year_start?.toString() || "",
        year_end: model.year_end?.toString() || "",
      });
    } else {
      setEditModelId(null);
      setModelForm({ model_name: "", generation: "", vehicle_type: "auto_rickshaw", year_start: "", year_end: "" });
    }
    setFormError("");
    setModelOpen(true);
  }, []);

  const saveSpec = useCallback(async () => {
    setFormError("");
    if (!specsModelId) return;
    const numFields = ["wheelbase_mm", "overall_length_mm", "overall_width_mm", "overall_height_mm", "ground_clearance_mm", "cargo_length_mm", "cargo_width_mm", "kerb_weight_kg", "gross_weight_kg", "payload_kg", "seating_capacity", "engine_cc"];
    const body: Record<string, any> = {};
    if (!editSpecId) body.model_id = specsModelId;
    for (const [k, v] of Object.entries(specForm)) {
      if (v !== "" && v !== undefined) body[k] = numFields.includes(k) ? Number(v) : v;
    }
    try {
      const url = editSpecId ? `${apiBase}/oem/specifications/${editSpecId}` : `${apiBase}/oem/models/${specsModelId}/specifications`;
      const method = editSpecId ? "PUT" : "POST";
      const r = await fetch(url, { method, headers: JSON_H, body: JSON.stringify(body) });
      if (!r.ok) throw new Error(await r.text());
      setSpecOpen(false); setEditSpecId(null); setSpecForm({});
      loadDetail(specsModelId);
    } catch (e: unknown) { setFormError(e instanceof Error ? e.message : "Failed"); }
  }, [specForm, specsModelId, editSpecId, loadDetail]);

  const openSpecModal = useCallback((spec?: any) => {
    if (spec) {
      setEditSpecId(spec.id);
      const f: Record<string, string> = {};
      for (const k of ["wheelbase_mm", "overall_length_mm", "overall_width_mm", "overall_height_mm", "ground_clearance_mm", "cargo_length_mm", "cargo_width_mm", "kerb_weight_kg", "gross_weight_kg", "payload_kg", "seating_capacity", "engine_cc", "fuel_type", "notes"]) {
        if (spec[k] !== null && spec[k] !== undefined) f[k] = String(spec[k]);
      }
      setSpecForm(f);
    } else {
      setEditSpecId(null);
      setSpecForm({});
    }
    setFormError("");
    setSpecOpen(true);
  }, []);

  const delSpec = useCallback(async (id: string) => {
    if (!confirm("Delete this specification?")) return;
    try {
      await fetch(`${apiBase}/oem/specifications/${id}`, { method: "DELETE", headers: h });
      if (specsModelId) loadDetail(specsModelId);
    } catch {}
  }, [specsModelId, loadDetail]);

  const saveMount = useCallback(async () => {
    setFormError("");
    if (!specsModelId || !mountForm.point_name.trim()) { setFormError("Name is required"); return; }
    const body: Record<string, any> = {};
    if (editMountId) {
      body.point_name = mountForm.point_name.trim();
      if (mountForm.point_type) body.point_type = mountForm.point_type;
    } else {
      body.model_id = specsModelId;
      body.point_name = mountForm.point_name.trim();
      body.point_type = mountForm.point_type || "standard";
    }
    if (mountForm.position_x_mm) body.position_x_mm = Number(mountForm.position_x_mm);
    if (mountForm.position_y_mm) body.position_y_mm = Number(mountForm.position_y_mm);
    if (mountForm.position_z_mm) body.position_z_mm = Number(mountForm.position_z_mm);
    if (mountForm.bolt_pattern) body.bolt_pattern = mountForm.bolt_pattern;
    if (mountForm.torque_spec_nm) body.torque_spec_nm = Number(mountForm.torque_spec_nm);
    if (mountForm.notes) body.notes = mountForm.notes;
    try {
      const url = editMountId ? `${apiBase}/oem/mounting-points/${editMountId}` : `${apiBase}/oem/models/${specsModelId}/mounting-points`;
      const method = editMountId ? "PUT" : "POST";
      const r = await fetch(url, { method, headers: JSON_H, body: JSON.stringify(body) });
      if (!r.ok) throw new Error(await r.text());
      setMountOpen(false); setEditMountId(null);
      setMountForm({ point_name: "", point_type: "", position_x_mm: "", position_y_mm: "", position_z_mm: "", bolt_pattern: "", torque_spec_nm: "", notes: "" });
      loadDetail(specsModelId);
    } catch (e: unknown) { setFormError(e instanceof Error ? e.message : "Failed"); }
  }, [mountForm, specsModelId, editMountId, loadDetail]);

  const openMountModal = useCallback((mount?: any) => {
    if (mount) {
      setEditMountId(mount.id);
      setMountForm({
        point_name: mount.point_name || "", point_type: mount.point_type || "",
        position_x_mm: mount.position_x_mm?.toString() || "", position_y_mm: mount.position_y_mm?.toString() || "", position_z_mm: mount.position_z_mm?.toString() || "",
        bolt_pattern: mount.bolt_pattern || "", torque_spec_nm: mount.torque_spec_nm?.toString() || "",
        notes: mount.notes || "",
      });
    } else {
      setEditMountId(null);
      setMountForm({ point_name: "", point_type: "", position_x_mm: "", position_y_mm: "", position_z_mm: "", bolt_pattern: "", torque_spec_nm: "", notes: "" });
    }
    setFormError("");
    setMountOpen(true);
  }, []);

  const delMount = useCallback(async (id: string) => {
    if (!confirm("Delete this mounting point?")) return;
    try {
      await fetch(`${apiBase}/oem/mounting-points/${id}`, { method: "DELETE", headers: h });
      if (specsModelId) loadDetail(specsModelId);
    } catch {}
  }, [specsModelId, loadDetail]);

  const saveRoute = useCallback(async () => {
    setFormError("");
    if (!specsModelId || !routeForm.path_name.trim()) { setFormError("Name is required"); return; }
    const body: Record<string, any> = {};
    if (editRouteId) {
      body.path_name = routeForm.path_name.trim();
      if (routeForm.path_type) body.path_type = routeForm.path_type;
    } else {
      body.model_id = specsModelId;
      body.path_name = routeForm.path_name.trim();
      body.path_type = routeForm.path_type || "cable";
    }
    if (routeForm.start_point) body.start_point = routeForm.start_point;
    if (routeForm.end_point) body.end_point = routeForm.end_point;
    if (routeForm.length_estimate_mm) body.length_estimate_mm = Number(routeForm.length_estimate_mm);
    if (routeForm.notes) body.notes = routeForm.notes;
    try {
      const url = editRouteId ? `${apiBase}/oem/routing-paths/${editRouteId}` : `${apiBase}/oem/models/${specsModelId}/routing-paths`;
      const method = editRouteId ? "PUT" : "POST";
      const r = await fetch(url, { method, headers: JSON_H, body: JSON.stringify(body) });
      if (!r.ok) throw new Error(await r.text());
      setRouteOpen(false); setEditRouteId(null);
      setRouteForm({ path_name: "", path_type: "", start_point: "", end_point: "", length_estimate_mm: "", notes: "" });
      loadDetail(specsModelId);
    } catch (e: unknown) { setFormError(e instanceof Error ? e.message : "Failed"); }
  }, [routeForm, specsModelId, editRouteId, loadDetail]);

  const openRouteModal = useCallback((route?: any) => {
    if (route) {
      setEditRouteId(route.id);
      setRouteForm({
        path_name: route.path_name || "",
        path_type: route.path_type || "",
        start_point: route.start_point || "",
        end_point: route.end_point || "",
        length_estimate_mm: route.length_estimate_mm?.toString() || "",
        notes: route.notes || "",
      });
    } else {
      setEditRouteId(null);
      setRouteForm({ path_name: "", path_type: "", start_point: "", end_point: "", length_estimate_mm: "", notes: "" });
    }
    setFormError("");
    setRouteOpen(true);
  }, []);

  const delRoute = useCallback(async (id: string) => {
    if (!confirm("Delete this routing path?")) return;
    try {
      await fetch(`${apiBase}/oem/routing-paths/${id}`, { method: "DELETE", headers: h });
      if (specsModelId) loadDetail(specsModelId);
    } catch {}
  }, [specsModelId, loadDetail]);

  const currentManuName = manuId ? manus.find((m: any) => m.id === manuId)?.name || "Unknown" : "";
  const specFieldLabels: Record<string, string> = {
    wheelbase_mm: "Wheelbase (mm)", overall_length_mm: "Length (mm)", overall_width_mm: "Width (mm)",
    overall_height_mm: "Height (mm)", ground_clearance_mm: "Ground Clearance (mm)",
    cargo_length_mm: "Cargo Length (mm)", cargo_width_mm: "Cargo Width (mm)",
    kerb_weight_kg: "Kerb Weight (kg)", gross_weight_kg: "Gross Weight (kg)", payload_kg: "Payload (kg)",
    seating_capacity: "Seating", engine_cc: "Engine CC", fuel_type: "Fuel Type", notes: "Notes",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-surface-muted p-1 border border-border">
          <button type="button" onClick={() => setOemTab("manufacturers")} className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${oemTab === "manufacturers" ? "bg-surface-card text-text-primary shadow-sm border border-border" : "text-text-tertiary hover:text-text-secondary"}`}>Manufacturers</button>
          <button type="button" onClick={() => setOemTab("models")} className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${oemTab === "models" ? "bg-surface-card text-text-primary shadow-sm border border-border" : "text-text-tertiary hover:text-text-secondary"}`}>Vehicle Models</button>
        </div>
        {oemTab === "manufacturers" && <Button size="sm" onClick={() => { setManuOpen(true); setFormError(""); }}>+ Add Manufacturer</Button>}
      </div>

      {oemTab === "manufacturers" && (
        <div className="space-y-3">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search manufacturers..." className="max-w-xs" />
          <Card padding="none">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                  <TH>Name</TH><TH>Country</TH><TH>Founded</TH><TH>Models</TH><TH>Active</TH><TH>Actions</TH>
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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => setOemTab("manufacturers")} className="text-xs text-brand underline underline-offset-2 hover:text-brand-dark">&larr; Back to Manufacturers</button>
              {manuId && <span className="text-xs text-text-tertiary">{currentManuName}</span>}
            </div>
            {manuId && <Button size="sm" onClick={() => openModelModal()}>+ Add Model</Button>}
          </div>
          <Input value={modelSearch} onChange={(e) => setModelSearch(e.target.value)} placeholder="Search models..." className="max-w-xs" />
          <Card padding="none">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wider text-text-tertiary">
                  <TH>Model</TH><TH>Generation</TH><TH>Type</TH><TH>Years</TH><TH>Specs</TH><TH>Mount</TH><TH>Routing</TH><TH>Actions</TH>
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
                        {(specsModelId === m.id ? (specs?.length ?? 0) : m.spec_count || 0)} spec{(specsModelId === m.id ? ((specs?.length ?? 0) !== 1) : (m.spec_count || 0) !== 1) ? "s" : ""}
                      </button>
                    </TD>
                    <TD className="text-xs text-text-tertiary">{specsModelId === m.id ? mounts.length : (m.mounting_point_count || "-")}</TD>
                    <TD className="text-xs text-text-tertiary">{specsModelId === m.id ? routes.length : (m.routing_path_count || "-")}</TD>
                    <TD className="flex gap-2">
                      <button type="button" onClick={() => openModelModal(m)} className="text-xs text-brand underline underline-offset-2">Edit</button>
                      <button type="button" onClick={() => delModel(m.id)} className="text-xs text-danger underline underline-offset-2">Delete</button>
                    </TD>
                  </tr>
                ))}
              </tbody>
            </table>
            {models.length === 0 && <p className="px-4 py-6 text-center text-xs text-text-tertiary">{loading ? "Loading..." : "No models found"}</p>}
          </Card>

          {specsModelId && specs !== null && (
            <Card>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-text-primary">
                  Details for {models.find((m: any) => m.id === specsModelId)?.model_name || ""}
                </h3>
                <button type="button" onClick={() => { setSpecs(null); setSpecsModelId(null); }} className="text-xs text-text-tertiary underline underline-offset-2">Close</button>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider">Specifications</h4>
                    <Button size="sm" variant="ghost" onClick={() => openSpecModal()}>+ Add</Button>
                  </div>
                  {specs.length === 0 ? <p className="text-xs text-text-tertiary">No specifications</p> : (
                    <div className="space-y-2">
                      {specs.map((spec: any) => (
                        <div key={spec.id} className="rounded-lg border border-border p-3">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {Object.entries(spec).filter(([k]) => !["id", "model_id", "created_at", "notes"].includes(k)).map(([k, v]) => v != null ? (
                              <div key={k}>
                                <p className="text-[10px] uppercase tracking-wider text-text-tertiary">{k.replace(/_/g, " ")}</p>
                                <p className="text-sm font-semibold text-text-primary">{String(v)}{k.includes("mm") ? " mm" : k.includes("kg") ? " kg" : ""}</p>
                              </div>
                            ) : null)}
                          </div>
                          {spec.notes && <p className="mt-1 text-xs text-text-tertiary">{spec.notes}</p>}
                          <div className="mt-2 flex gap-2">
                            <button type="button" onClick={() => openSpecModal(spec)} className="text-xs text-brand underline underline-offset-2">Edit</button>
                            <button type="button" onClick={() => delSpec(spec.id)} className="text-xs text-danger underline underline-offset-2">Delete</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider">Mounting Points ({mounts.length})</h4>
                    <Button size="sm" variant="ghost" onClick={() => openMountModal()}>+ Add</Button>
                  </div>
                  {mounts.length === 0 ? <p className="text-xs text-text-tertiary">No mounting points</p> : (
                    <div className="space-y-1">
                      {mounts.map((mp: any) => (
                        <div key={mp.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                          <div>
                            <span className="text-sm font-medium text-text-primary">{mp.point_name}</span>
                            {mp.point_type && <Badge variant="default" size="sm" className="ml-2">{mp.point_type}</Badge>}
                            <span className="ml-2 text-xs text-text-tertiary font-mono">
                              {mp.position_x_mm != null && `${mp.position_x_mm}, ${mp.position_y_mm}, ${mp.position_z_mm} mm`}
                            </span>
                          </div>
                          <div className="flex gap-2">
                            <button type="button" onClick={() => openMountModal(mp)} className="text-xs text-brand underline underline-offset-2">Edit</button>
                            <button type="button" onClick={() => delMount(mp.id)} className="text-xs text-danger underline underline-offset-2">Delete</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider">Routing Paths ({routes.length})</h4>
                    <Button size="sm" variant="ghost" onClick={() => openRouteModal()}>+ Add</Button>
                  </div>
                  {routes.length === 0 ? <p className="text-xs text-text-tertiary">No routing paths</p> : (
                    <div className="space-y-1">
                      {routes.map((rp: any) => (
                        <div key={rp.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                          <div>
                            <span className="text-sm font-medium text-text-primary">{rp.path_name}</span>
                            {rp.path_type && <Badge variant="default" size="sm" className="ml-2">{rp.path_type}</Badge>}
                            <span className="ml-2 text-xs text-text-tertiary">
                              {rp.start_point && `${rp.start_point} → ${rp.end_point || "?"}`}
                              {rp.length_estimate_mm && ` (${rp.length_estimate_mm} mm)`}
                            </span>
                            {rp.notes && <span className="ml-2 text-xs text-text-tertiary">- {rp.notes}</span>}
                          </div>
                          <div className="flex gap-2">
                            <button type="button" onClick={() => openRouteModal(rp)} className="text-xs text-brand underline underline-offset-2">Edit</button>
                            <button type="button" onClick={() => delRoute(rp.id)} className="text-xs text-danger underline underline-offset-2">Delete</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {manuOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Add Manufacturer</h3>
            <div className="space-y-3">
              <Input value={manuName} onChange={(e) => setManuName(e.target.value)} placeholder="Manufacturer name *" />
              <Input value={manuCountry} onChange={(e) => setManuCountry(e.target.value)} placeholder="Country (optional)" />
              <Input value={manuYear} onChange={(e) => setManuYear(e.target.value)} placeholder="Founded year (optional)" type="number" />
              {formError && <p className="text-xs text-danger">{formError}</p>}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setManuOpen(false); setFormError(""); }}>Cancel</Button>
              <Button variant="primary" onClick={createManu}>Create</Button>
            </div>
          </div>
        </div>
      )}

      {modelOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-4">{editModelId ? "Edit Model" : "Add Model"}</h3>
            <div className="space-y-3">
              <Input value={modelForm.model_name} onChange={(e) => setModelForm({ ...modelForm, model_name: e.target.value })} placeholder="Model name *" />
              <Input value={modelForm.generation} onChange={(e) => setModelForm({ ...modelForm, generation: e.target.value })} placeholder="Generation (e.g. Mk2)" />
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">Vehicle Type</label>
                <select value={modelForm.vehicle_type} onChange={(e) => setModelForm({ ...modelForm, vehicle_type: e.target.value })}
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30">
                  <option value="auto_rickshaw">Auto Rickshaw</option>
                  <option value="hatchback">Hatchback</option>
                  <option value="sedan">Sedan</option>
                  <option value="suv">SUV</option>
                  <option value="pickup">Pickup</option>
                  <option value="van">Van</option>
                  <option value="truck">Truck</option>
                  <option value="bus">Bus</option>
                  <option value="motorcycle">Motorcycle</option>
                  <option value="bicycle">Bicycle</option>
                  <option value="three_wheeler_goods">Three Wheeler Goods</option>
                  <option value="tractor">Tractor</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="flex gap-3">
                <Input value={modelForm.year_start} onChange={(e) => setModelForm({ ...modelForm, year_start: e.target.value })} placeholder="Year start" type="number" />
                <Input value={modelForm.year_end} onChange={(e) => setModelForm({ ...modelForm, year_end: e.target.value })} placeholder="Year end" type="number" />
              </div>
              {formError && <p className="text-xs text-danger">{formError}</p>}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setModelOpen(false); setFormError(""); }}>Cancel</Button>
              <Button variant="primary" onClick={saveModel}>{editModelId ? "Save" : "Create"}</Button>
            </div>
          </div>
        </div>
      )}

      {specOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-surface-card p-6 shadow-xl border border-border max-h-[90vh] overflow-y-auto">
            <h3 className="text-sm font-semibold text-text-primary mb-4">{editSpecId ? "Edit Specification" : "Add Specification"}</h3>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(specFieldLabels).map(([k, label]) => (
                <Input key={k} label={label} value={specForm[k] ?? ""} onChange={(e) => setSpecForm({ ...specForm, [k]: e.target.value })}
                  type={k === "notes" ? "text" : k === "fuel_type" ? "text" : "number"} />
              ))}
            </div>
            {formError && <p className="mt-2 text-xs text-danger">{formError}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setSpecOpen(false); setFormError(""); }}>Cancel</Button>
              <Button variant="primary" onClick={saveSpec}>{editSpecId ? "Save" : "Create"}</Button>
            </div>
          </div>
        </div>
      )}

      {mountOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-4">{editMountId ? "Edit Mounting Point" : "Add Mounting Point"}</h3>
            <div className="space-y-3">
              <Input value={mountForm.point_name} onChange={(e) => setMountForm({ ...mountForm, point_name: e.target.value })} placeholder="Name *" />
              <Input value={mountForm.point_type} onChange={(e) => setMountForm({ ...mountForm, point_type: e.target.value })} placeholder="Type (e.g. engine, battery, body)" />
              <div className="flex gap-3">
                <Input value={mountForm.position_x_mm} onChange={(e) => setMountForm({ ...mountForm, position_x_mm: e.target.value })} placeholder="X (mm)" type="number" />
                <Input value={mountForm.position_y_mm} onChange={(e) => setMountForm({ ...mountForm, position_y_mm: e.target.value })} placeholder="Y (mm)" type="number" />
                <Input value={mountForm.position_z_mm} onChange={(e) => setMountForm({ ...mountForm, position_z_mm: e.target.value })} placeholder="Z (mm)" type="number" />
              </div>
              <div className="flex gap-3">
                <Input value={mountForm.bolt_pattern} onChange={(e) => setMountForm({ ...mountForm, bolt_pattern: e.target.value })} placeholder="Bolt pattern (e.g. 4x100)" />
                <Input value={mountForm.torque_spec_nm} onChange={(e) => setMountForm({ ...mountForm, torque_spec_nm: e.target.value })} placeholder="Torque (Nm)" type="number" />
              </div>
              <Input value={mountForm.notes} onChange={(e) => setMountForm({ ...mountForm, notes: e.target.value })} placeholder="Notes (optional)" />
              {formError && <p className="text-xs text-danger">{formError}</p>}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setMountOpen(false); setFormError(""); }}>Cancel</Button>
              <Button variant="primary" onClick={saveMount}>{editMountId ? "Save" : "Create"}</Button>
            </div>
          </div>
        </div>
      )}

      {routeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-surface-card p-6 shadow-xl border border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-4">{editRouteId ? "Edit Routing Path" : "Add Routing Path"}</h3>
            <div className="space-y-3">
              <Input value={routeForm.path_name} onChange={(e) => setRouteForm({ ...routeForm, path_name: e.target.value })} placeholder="Path name *" />
              <Input value={routeForm.path_type} onChange={(e) => setRouteForm({ ...routeForm, path_type: e.target.value })} placeholder="Path type (e.g. cable, hose)" />
              <div className="flex gap-3">
                <Input value={routeForm.start_point} onChange={(e) => setRouteForm({ ...routeForm, start_point: e.target.value })} placeholder="Start point" />
                <Input value={routeForm.end_point} onChange={(e) => setRouteForm({ ...routeForm, end_point: e.target.value })} placeholder="End point" />
              </div>
              <Input value={routeForm.length_estimate_mm} onChange={(e) => setRouteForm({ ...routeForm, length_estimate_mm: e.target.value })} placeholder="Length estimate (mm)" type="number" />
              <Input value={routeForm.notes} onChange={(e) => setRouteForm({ ...routeForm, notes: e.target.value })} placeholder="Notes (optional)" />
              {formError && <p className="text-xs text-danger">{formError}</p>}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setRouteOpen(false); setFormError(""); }}>Cancel</Button>
              <Button variant="primary" onClick={saveRoute}>{editRouteId ? "Save" : "Create"}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
