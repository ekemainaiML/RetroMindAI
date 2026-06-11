"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE, apiGet, apiPost, ensureApiKey, getApiKey, setApiKey } from "@/utils/api";
import { useRouter } from "next/navigation";
import { useUser } from "@/contexts/UserContext";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card, { CardHeader } from "@/components/ui/Card";



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

interface SubscriptionResponse {
  plan: {
    id: string;
    tier: string;
    name: string;
    price_monthly: number;
    price_yearly: number;
    max_users: number | null;
    max_assessments: number | null;
    max_storage_mb: number | null;
    features: string[];
  } | null;
  status: string;
  billing_period_start: string | null;
  billing_period_end: string | null;
  cancel_at_period_end: boolean;
}

interface UsageItem {
  metric: string;
  total: number;
  limit: number | null;
}

interface MemberItem {
  user_id: string;
  email: string;
  name: string;
  role: string;
  accepted_at: string | null;
  invited_at: string | null;
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

  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [subLoading, setSubLoading] = useState(false);
  const [usage, setUsage] = useState<UsageItem[]>([]);
  const [usageLoading, setUsageLoading] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [billingError, setBillingError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const [members, setMembers] = useState<MemberItem[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

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
      const k = getApiKey();
      await fetch(`${API_BASE}/notifications/preferences`, {
        method: "PUT",
        headers: { "X-API-Key": k, "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value }),
      });
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

  const fetchSubscription = useCallback(async () => {
    setSubLoading(true);
    try {
      const data = await apiGet<SubscriptionResponse>("/billing/subscription");
      setSubscription(data);
    } catch {
    } finally {
      setSubLoading(false);
    }
  }, []);

  const fetchUsage = useCallback(async () => {
    setUsageLoading(true);
    try {
      const data = await apiGet<{ usage: UsageItem[] }>("/billing/usage");
      setUsage(data.usage);
    } catch {
    } finally {
      setUsageLoading(false);
    }
  }, []);

  const handleUpgrade = useCallback(async (priceId: string) => {
    setBillingError(null);
    setUpgrading(true);
    try {
      const data = await apiPost<{ url: string }>("/billing/create-checkout", {
        price_id: priceId,
        success_url: window.location.href,
        cancel_url: window.location.href,
      });
      window.location.href = data.url;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("501") || msg.includes("Billing not configured")) {
        setBillingError("Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in production.");
      } else {
        setBillingError(msg || "Failed to open checkout");
      }
    } finally {
      setUpgrading(false);
    }
  }, []);

  const handleBillingPortal = useCallback(async () => {
    setBillingError(null);
    setPortalLoading(true);
    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/billing/portal`, {
        method: "POST",
        headers: { "X-API-Key": key, "Content-Type": "application/json" },
        body: JSON.stringify({ return_url: window.location.href }),
      });
      if (!res.ok) {
        const text = await res.text();
        if (res.status === 501 || text.includes("Billing not configured")) {
          setBillingError("Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in production.");
          return;
        }
        throw new Error(text || "Failed to open billing portal");
      }
      const data = await res.json();
      window.location.href = data.url;
    } catch (err) {
      setBillingError(err instanceof Error ? err.message : "Failed to open billing portal");
    } finally {
      setPortalLoading(false);
    }
  }, []);

  const handleExport = useCallback(async () => {
    setExporting(true);
    setError(null);
    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/workshop/export`, {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) throw new Error(`Export failed: ${await res.text()}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `workshop-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export data");
    } finally {
      setExporting(false);
    }
  }, []);

  const fetchMembers = useCallback(async () => {
    const key = getApiKey();
    if (!key) return;
    setMembersLoading(true);
    try {
      const res = await fetch(`${API_BASE}/workshop/members`, {
        headers: { "X-API-Key": key },
      });
      if (res.ok) {
        const data = await res.json();
        setMembers(data.members);
      }
    } catch {
    } finally {
      setMembersLoading(false);
    }
  }, []);

  const handleRemoveMember = useCallback(async (userId: string) => {
    if (!jwt) return;
    setRemovingId(userId);
    try {
      const res = await fetch(`${API_BASE}/workshop/members/${userId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (res.ok) {
        setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      } else {
        const text = await res.text();
        setError(text || "Failed to remove member");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    } finally {
      setRemovingId(null);
    }
  }, [jwt]);

  const handleUpdateRole = useCallback(async (userId: string, role: string) => {
    if (!jwt) return;
    try {
      const res = await fetch(`${API_BASE}/workshop/members/${userId}/role`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${jwt}`, "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (res.ok) {
        setMembers((prev) => prev.map((m) => (m.user_id === userId ? { ...m, role } : m)));
      }
    } catch {
    }
  }, [jwt]);

  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  useEffect(() => {
    fetchNotifPrefs();
    fetchSubscription();
    fetchUsage();
  }, [fetchNotifPrefs, fetchSubscription, fetchUsage]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

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

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Billing & Plan</h2>
        </CardHeader>
        {subLoading ? (
          <div className="flex items-center justify-center py-6">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : subscription ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-text-primary">
                  {subscription.plan?.name || subscription.status}
                </p>
                <p className="text-xs text-text-tertiary">
                  {subscription.plan
                    ? `$${subscription.plan.price_monthly}/mo or $${subscription.plan.price_yearly}/yr`
                    : "No active plan"}
                </p>
              </div>
              <Badge variant={subscription.status === "active" ? "success" : subscription.status === "past_due" ? "danger" : "default"}>
                {subscription.status}
              </Badge>
            </div>

            {subscription.plan && subscription.plan.features.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {subscription.plan.features.map((f) => (
                  <Badge key={f} variant="info">{f}</Badge>
                ))}
              </div>
            )}

            {subscription.billing_period_end && (
              <p className="text-xs text-text-secondary">
                Current period ends: {new Date(subscription.billing_period_end).toLocaleDateString()}
              </p>
            )}

            <div className="flex gap-2">
              <Button
                onClick={() => handleUpgrade(subscription.plan?.id || "")}
                variant="brand"
                size="sm"
                loading={upgrading}
                disabled={!subscription.plan}
              >
                {subscription.plan?.tier === "enterprise" ? "Contact Sales" : "Upgrade Plan"}
              </Button>
              <Button
                onClick={handleBillingPortal}
                variant="secondary"
                size="sm"
                loading={portalLoading}
              >
                Manage Billing
              </Button>
            </div>
            {billingError && (
              <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 px-3 py-2">
                {billingError}
              </p>
            )}
          </div>
        ) : (
          <p className="text-xs text-text-secondary">Could not load billing info.</p>
        )}

        <div className="mt-4 border-t border-border pt-4">
          <h3 className="mb-3 text-xs font-medium text-text-secondary">Monthly Usage</h3>
          {usageLoading ? (
            <div className="flex items-center justify-center py-3">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-brand border-t-transparent" />
            </div>
          ) : usage.length > 0 ? (
            <div className="space-y-2">
              {usage.map((u) => (
                <div key={u.metric}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-text-secondary">
                      {u.metric.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <span className="text-xs font-medium text-text-primary">
                      {u.total}{u.limit !== null ? ` / ${u.limit}` : ""}
                    </span>
                  </div>
                  {u.limit !== null && (
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
                      <div
                        className={`h-full rounded-full transition-all ${
                          u.total / u.limit > 0.8
                            ? "bg-danger"
                            : u.total / u.limit > 0.5
                            ? "bg-warning"
                            : "bg-brand"
                        }`}
                        style={{ width: `${Math.min(100, (u.total / u.limit) * 100)}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-secondary">No usage data available.</p>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Data Export</h2>
        </CardHeader>
        <div className="px-6 pb-6">
          <p className="mb-3 text-xs text-text-secondary">
            Download all workshop data — intakes, jobs, and metadata — as a JSON file.
          </p>
          <Button variant="secondary" onClick={handleExport} disabled={exporting} className="w-full sm:w-auto">
            {exporting ? "Exporting…" : "Export Data"}
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Team Members</h2>
        </CardHeader>
          {membersLoading ? (
            <div className="flex items-center justify-center py-6">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
            </div>
          ) : members.length > 0 ? (
            <div className="space-y-2">
              {members.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                  <div className="min-w-0 flex-1 pr-4">
                    <p className="text-sm font-medium text-text-primary">{m.name || m.email}</p>
                    <p className="text-xs text-text-tertiary">{m.email}</p>
                    {m.invited_at && !m.accepted_at && (
                      <p className="text-xs text-warning">Invited — awaiting acceptance</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={m.role}
                      onChange={(e) => handleUpdateRole(m.user_id, e.target.value)}
                      className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30"
                    >
                      <option value="admin">Admin</option>
                      <option value="operator">Operator</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    {confirmRemoveId === m.user_id ? (
                      <div className="flex gap-1">
                        <Button
                          variant="danger"
                          size="sm"
                          loading={removingId === m.user_id}
                          onClick={() => handleRemoveMember(m.user_id)}
                        >
                          Confirm
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setConfirmRemoveId(null)}>
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setConfirmRemoveId(m.user_id)}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-secondary">No team members.</p>
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
        {renewDone && newKey ? (
          <div className="rounded-lg border border-brand/30 bg-brand/5 p-4">
            <p className="text-sm font-semibold text-brand">API Key Renewed Successfully</p>
            <p className="mt-1 text-xs text-text-secondary">
              Save this key — it will not be shown again.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <code className="flex-1 break-all rounded border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary">
                {newKey}
              </code>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => { navigator.clipboard.writeText(newKey); }}
              >
                Copy
              </Button>
            </div>
            <div className="mt-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setRenewDone(false); setNewKey(null); }}
              >
                Dismiss
              </Button>
            </div>
          </div>
        ) : !showRenewConfirm ? (
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
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">Branding</h2>
        </CardHeader>
        <p className="mb-4 text-xs text-text-secondary">
          Customize the look and feel of reports and the portal for your customers.
        </p>
        <BrandingForm />
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

function BrandingForm() {
  const [logoUrl, setLogoUrl] = useState("");
  const [primaryColor, setPrimaryColor] = useState("");
  const [secondaryColor, setSecondaryColor] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const key = getApiKey();
    if (!key) return;
    fetch(`${API_BASE}/workshop/branding`, {
      headers: { "X-API-Key": key },
    })
      .then((r) => r.json())
      .then((data) => {
        setLogoUrl(data.logo_url || "");
        setPrimaryColor(data.primary_color || "");
        setSecondaryColor(data.secondary_color || "");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaved(false);
    try {
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/workshop/branding`, {
        method: "PUT",
        headers: { "X-API-Key": key, "Content-Type": "application/json" },
        body: JSON.stringify({
          logo_url: logoUrl,
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          custom_domain: "",
        }),
      });
      if (!res.ok) throw new Error("Failed to save branding");
      const data = await res.json();
      localStorage.setItem("retromind_branding", JSON.stringify(data));
      const root = document.documentElement;
      if (data.primary_color) root.style.setProperty("--brand-primary", data.primary_color);
      if (data.secondary_color) root.style.setProperty("--brand-secondary", data.secondary_color);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
    } finally {
      setSaving(false);
    }
  }, [logoUrl, primaryColor, secondaryColor]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs font-medium text-text-secondary mb-1">Logo URL</label>
        <input
          type="text"
          value={logoUrl}
          onChange={(e) => setLogoUrl(e.target.value)}
          placeholder="https://example.com/logo.png"
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
        />
        {logoUrl && (
          <div className="mt-2 flex items-center gap-3 rounded-lg border border-border bg-surface p-3">
            <img src={logoUrl} alt="Preview" className="h-10 w-auto max-w-[120px] object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
            <span className="text-[10px] text-text-tertiary">Preview</span>
          </div>
        )}
      </div>
      <div className="flex gap-3">
        <div className="flex-1">
          <label className="block text-xs font-medium text-text-secondary mb-1">Primary Color</label>
          <div className="flex gap-2">
            <input
              type="color"
              value={primaryColor || "#1a73e8"}
              onChange={(e) => setPrimaryColor(e.target.value)}
              className="h-9 w-9 cursor-pointer rounded border border-border bg-transparent p-0.5"
            />
            <input
              type="text"
              value={primaryColor}
              onChange={(e) => setPrimaryColor(e.target.value)}
              placeholder="#1a73e8"
              className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
            />
          </div>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-text-secondary mb-1">Secondary Color</label>
          <div className="flex gap-2">
            <input
              type="color"
              value={secondaryColor || "#7c3aed"}
              onChange={(e) => setSecondaryColor(e.target.value)}
              className="h-9 w-9 cursor-pointer rounded border border-border bg-transparent p-0.5"
            />
            <input
              type="text"
              value={secondaryColor}
              onChange={(e) => setSecondaryColor(e.target.value)}
              placeholder="#7c3aed"
              className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
            />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 pt-1">
        <Button onClick={handleSave} variant="brand" size="sm" loading={saving}>
          Save Branding
        </Button>
        {saved && <span className="text-xs text-green-600 dark:text-green-400">Saved!</span>}
      </div>
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
