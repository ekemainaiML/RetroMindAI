"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, getApiKey, setApiKey } from "@/utils/api";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Logo from "@/components/Logo";

export default function AuthPage() {
  const router = useRouter();
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [demoKey, setDemoKey] = useState<string | null>(null);
  const [fetchingDemo, setFetchingDemo] = useState(false);

  useEffect(() => {
    if (getApiKey()) router.replace("/");
  }, [router]);

  const fetchDemoKey = useCallback(async () => {
    setFetchingDemo(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/setup/demo-key`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.api_key) {
        setDemoKey(data.api_key);
        setKeyInput(data.api_key);
      } else {
        setError("No demo key available. Start the backend first.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch demo key");
    } finally {
      setFetchingDemo(false);
    }
  }, []);

  const validateAndStore = useCallback(async (key: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/history`, {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `HTTP ${res.status}`);
      }
      setApiKey(key);
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid API key");
    } finally {
      setLoading(false);
    }
  }, [router]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    validateAndStore(keyInput.trim());
  }, [keyInput, validateAndStore]);

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm animate-slide-up">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Logo size="md" />
          </div>
          <h1 className="text-xl font-bold text-text-primary">API Key Access</h1>
          <p className="mt-1 text-sm text-text-secondary">Enter your API key to continue</p>
        </div>

        <div className="rounded-xl border border-border bg-surface-card p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="API Key"
              type="text"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="rm_..."
              className="font-mono"
              autoFocus
            />

            {error && (
              <div className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="brand"
              loading={loading}
              disabled={!keyInput.trim()}
              className="w-full"
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-border">
            <Button
              onClick={fetchDemoKey}
              variant="secondary"
              loading={fetchingDemo}
              className="w-full"
            >
              {demoKey ? "Re-fetch Demo Key" : "Use Demo Key"}
            </Button>
            <p className="text-xs text-text-tertiary text-center mt-2">
              Fetches the demo API key from the backend
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
