"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, getApiKey, getJwt, setApiKey } from "@/utils/api";
import { useRouter } from "next/navigation";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card, { CardHeader } from "@/components/ui/Card";

const API_BASE = "http://localhost:8000/api/v1";

interface Profile {
  id: string;
  name: string;
  email: string;
  tier: string;
  created_at: string;
  api_key_prefix: string;
}

interface Capability {
  name: string;
  label: string;
  description: string;
  effective: boolean;
  dep_installed: boolean;
}

interface Workshop {
  id: string;
  name: string;
  api_key_prefix: string;
  tier: string;
}

const phaseLabel: Record<string, string> = {
  vision: "Phase 1",
  classification: "Phase 1",
  deviation: "Phase 2",
  geometry: "Phase 2",
  degradation: "Phase 2",
  digital_twin: "Phase 3",
  generative: "Phase 4",
  recommendations: "Phase 5",
  rl: "Phase 5",
};

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [capsLoading, setCapsLoading] = useState(true);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [renewing, setRenewing] = useState(false);
  const [showRenewConfirm, setShowRenewConfirm] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [renewDone, setRenewDone] = useState(false);
  const [workshops, setWorkshops] = useState<Workshop[]>([]);
  const [newWorkshopName, setNewWorkshopName] = useState("");
  const [creatingWorkshop, setCreatingWorkshop] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);

  const jwt = getJwt();

  useEffect(() => {
    if (!jwt) return;
    fetch(`${API_BASE}/workshops`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => r.ok && r.json())
      .then((data) => {
        if (data) setWorkshops(data.workshops);
      })
      .catch(() => {});
  }, [jwt]);

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<Profile>("/workshop/profile");
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCapabilities = useCallback(async () => {
    setCapsLoading(true);
    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/workshop/capabilities`, {
        headers: { "X-API-Key": key },
      });
      if (res.ok) {
        const data = await res.json();
        setCapabilities(data.capabilities);
      }
    } catch {
    } finally {
      setCapsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
    fetchCapabilities();
  }, [fetchProfile, fetchCapabilities]);

  const handleRenew = useCallback(async () => {
    setRenewing(true);
    setError(null);
    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/auth/renew`, {
        method: "POST",
        headers: { "X-API-Key": key, "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(`Renew failed: ${await res.text()}`);
      const data = await res.json();
      setApiKey(data.api_key);
      setNewKey(data.api_key);
      setRenewDone(true);
      setShowRenewConfirm(false);
      await fetchProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to renew key");
    } finally {
      setRenewing(false);
    }
  }, [fetchProfile]);

  const toggleCapability = useCallback(async (name: string, value: boolean) => {
    setCapabilities((prev) =>
      prev.map((c) => (c.name === name ? { ...c, effective: value } : c))
    );
    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/workshop/capabilities/${name}`, {
        method: "PUT",
        headers: { "X-API-Key": key, "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!res.ok) fetchCapabilities();
    } catch {
      fetchCapabilities();
    }
  }, [fetchCapabilities]);

  const createWorkshop = useCallback(async () => {
    if (!newWorkshopName.trim() || !jwt) return;
    setCreatingWorkshop(true);
    try {
      const res = await fetch(`${API_BASE}/workshops`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}`, "Content-Type": "application/json" },
        body: JSON.stringify({ name: newWorkshopName.trim() }),
      });
      if (!res.ok) throw new Error(await res.text());
      const updated = await fetch(`${API_BASE}/workshops`, {
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (updated.ok) {
        const data = await updated.json();
        setWorkshops(data.workshops);
      }
      setNewWorkshopName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workshop");
    } finally {
      setCreatingWorkshop(false);
    }
  }, [newWorkshopName, jwt]);

  const handleSwitchWorkshop = useCallback(async (workshopId: string) => {
    if (!jwt) return;
    setSwitchingId(workshopId);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/workshops/${workshopId}/key`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}`, "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(`Failed: ${await res.text()}`);
      const data = await res.json();
      setApiKey(data.api_key);
      router.refresh();
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to switch workshop");
    } finally {
      setSwitchingId(null);
    }
  }, [jwt, router]);

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8">
      <h1 className="text-lg font-bold text-text-primary">Settings</h1>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-3">
          <p className="text-xs text-danger">{error}</p>
        </div>
      )}

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Workshop Profile</h2>
        </CardHeader>
        {loading ? (
          <div className="flex items-center justify-center py-6">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : profile ? (
          <div className="space-y-2">
            <Row label="ID" value={profile.id} mono />
            <Row label="Name" value={profile.name} />
            <Row label="Email" value={profile.email} />
            <Row label="Tier" value={profile.tier} />
            <Row label="API Key Prefix" value={profile.api_key_prefix} mono />
            <Row label="Created">
              <span className="text-sm text-text-primary">
                {new Date(profile.created_at).toLocaleDateString()}
              </span>
            </Row>
          </div>
        ) : (
          <p className="text-xs text-text-secondary">Could not load profile.</p>
        )}
      </Card>

      {jwt && (
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Workspaces</h2>
          </CardHeader>
          {workshops.length > 0 && (
            <div className="mb-3 space-y-2">
              {workshops.map((w) => (
                <div key={w.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                  <div>
                    <span className="text-sm font-medium text-text-primary">{w.name}</span>
                    <span className="ml-2 text-xs text-text-tertiary">{w.api_key_prefix}</span>
                  </div>
                  <Button
                    onClick={() => handleSwitchWorkshop(w.id)}
                    disabled={switchingId === w.id}
                    loading={switchingId === w.id}
                    variant="brand"
                    size="sm"
                  >
                    Use This Workshop
                  </Button>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={newWorkshopName}
              onChange={(e) => setNewWorkshopName(e.target.value)}
              placeholder="New workshop name"
              className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
              onKeyDown={(e) => e.key === "Enter" && createWorkshop()}
            />
            <Button
              onClick={createWorkshop}
              disabled={creatingWorkshop || !newWorkshopName.trim()}
              loading={creatingWorkshop}
              variant="brand"
              size="sm"
            >
              Create
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">API Key</h2>
        </CardHeader>
        <p className="mb-4 text-xs text-text-secondary">
          Renewing your API key will immediately invalidate the current key. Services using the old key will need to be updated.
        </p>
        {!showRenewConfirm ? (
          <Button onClick={() => setShowRenewConfirm(true)} variant="accent" size="sm">
            Renew API Key
          </Button>
        ) : (
          <div className="rounded-lg border border-danger/30 bg-danger/5 p-4">
            <p className="text-sm font-semibold text-danger">Are you sure?</p>
            <p className="mt-1 text-xs text-danger">
              This will invalidate your current API key immediately. This action cannot be undone.
            </p>
            <div className="mt-3 flex gap-2">
              <Button onClick={handleRenew} variant="danger" size="sm" loading={renewing}>
                Yes, Renew Key
              </Button>
              <Button onClick={() => setShowRenewConfirm(false)} variant="secondary" size="sm" disabled={renewing}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Optional Capabilities</h2>
        </CardHeader>
        <p className="mb-4 text-xs text-text-secondary">
          Toggle optional AI/ML capabilities on or off. All are disabled by default.
        </p>
        {capsLoading && capabilities.length === 0 ? (
          <div className="flex items-center justify-center py-6">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : (
          <div className="space-y-2">
            {capabilities.map((cap) => (
              <div key={cap.name} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                <div className="min-w-0 flex-1 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">{cap.label}</span>
                    {phaseLabel[cap.name] && (
                      <Badge variant="brand" size="sm">{phaseLabel[cap.name]}</Badge>
                    )}
                    {cap.dep_installed ? (
                      <Badge variant="success" size="sm">dep ready</Badge>
                    ) : (
                      <Badge variant="warning" size="sm">dep missing</Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-text-tertiary">{cap.description}</p>
                </div>
                <button
                  role="switch"
                  aria-checked={cap.effective}
                  onClick={() => toggleCapability(cap.name, !cap.effective)}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-brand focus-visible:outline-offset-2 ${
                    cap.effective ? "bg-brand" : "bg-border"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ${
                      cap.effective ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function Row({ label, value, mono, children }: { label: string; value?: string; mono?: boolean; children?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-text-secondary">{label}</span>
      {children || <span className={`text-sm font-medium text-text-primary ${mono ? "font-mono" : ""}`}>{value}</span>}
    </div>
  );
}
