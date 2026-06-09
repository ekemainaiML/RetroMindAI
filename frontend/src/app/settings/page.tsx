"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, ensureApiKey, getApiKey, setApiKey } from "@/utils/api";
import { useRouter } from "next/navigation";
import { useUser } from "@/contexts/UserContext";
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
  const { user, jwt, workshops, setWorkshops } = useUser();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [capsLoading, setCapsLoading] = useState(true);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [renewing, setRenewing] = useState(false);
  const [showRenewConfirm, setShowRenewConfirm] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [renewDone, setRenewDone] = useState(false);
  const [newWorkshopName, setNewWorkshopName] = useState("");
  const [creatingWorkshop, setCreatingWorkshop] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const [notifPrefs, setNotifPrefs] = useState<Record<string, boolean> | null>(null);
  const [notifLoading, setNotifLoading] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);
  const [testEmailResult, setTestEmailResult] = useState<string | null>(null);

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
      const key = await ensureApiKey();
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

  const fetchNotifPrefs = useCallback(async () => {
    setNotifLoading(true);
    try {
      const data = await apiGet<{ preferences: Record<string, boolean> }>("/notifications/preferences");
      setNotifPrefs(data.preferences);
    } catch {
    } finally {
      setNotifLoading(false);
    }
  }, []);

  const updateNotifPref = useCallback(async (key: string, value: boolean) => {
    setNotifPrefs((prev) => prev ? { ...prev, [key]: value } : prev);
    try {
      await apiPost("/notifications/preferences", { key, value });
    } catch {
      fetchNotifPrefs();
    }
  }, [fetchNotifPrefs]);

  const sendTestEmail = useCallback(async () => {
    setSendingTest(true);
    setTestEmailResult(null);
    try {
      await apiPost("/notifications/test");
      setTestEmailResult("Test email sent! Check your inbox (or MailHog at :8025).");
    } catch (err) {
      setTestEmailResult(err instanceof Error ? err.message : "Failed to send test email");
    } finally {
      setSendingTest(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifPrefs();
  }, [fetchNotifPrefs]);

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8">
      <h1 className="text-lg font-bold text-text-primary">Settings</h1>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-3">
          <p className="text-xs text-danger">{error}</p>
        </div>
      )}

      {user && (
        <Card>
          <CardHeader>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">User</h2>
          </CardHeader>
          <div className="space-y-2">
            <Row label="Name" value={user.name} />
            <Row label="Email" value={user.email} />
            <Row label="ID" value={user.id} mono />
          </div>
        </Card>
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

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Email Notifications</h2>
        </CardHeader>
        <p className="mb-4 text-xs text-text-secondary">
          Configure which events trigger email notifications. Requires SMTP to be configured on the server (MailHog in development).
        </p>
        {notifLoading && notifPrefs === null ? (
          <div className="flex items-center justify-center py-6">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : notifPrefs ? (
          <div className="space-y-2">
            {Object.entries(notifPrefs).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                <span className="text-sm font-medium text-text-primary">
                  {key.replace(/notify_/g, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
                <button
                  role="switch"
                  aria-checked={value}
                  onClick={() => updateNotifPref(key, !value)}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-brand focus-visible:outline-offset-2 ${
                    value ? "bg-brand" : "bg-border"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ${
                      value ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-secondary">Could not load preferences.</p>
        )}
        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            onClick={sendTestEmail}
            disabled={sendingTest}
            className="rounded-lg border border-border bg-surface px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-all disabled:opacity-40"
          >
            {sendingTest ? "Sending..." : "Send Test Email"}
          </button>
          {testEmailResult && (
            <span className={`text-xs ${testEmailResult.includes("sent") ? "text-green-600 dark:text-green-400" : "text-danger"}`}>
              {testEmailResult}
            </span>
          )}
        </div>
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
