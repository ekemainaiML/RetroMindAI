"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { setApiKey, getJwt } from "@/utils/api";
import { useUser } from "@/contexts/UserContext";
import Link from "next/link";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Logo from "@/components/Logo";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function SignupPage() {
  const router = useRouter();
  const { login } = useUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getJwt()) router.replace("/");
  }, [router]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      login(data.jwt, data.user, data.workshops);
      if (data.default_api_key) setApiKey(data.default_api_key);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }, [name, email, password, confirm, login, router]);

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm animate-slide-up">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Logo size="md" />
          </div>
          <h1 className="text-xl font-bold text-text-primary">Create Account</h1>
          <p className="mt-1 text-sm text-text-secondary">Get started with RetroMind AI</p>
        </div>

        <div className="rounded-xl border border-border bg-surface-card p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your workshop name"
              required
              autoFocus
            />

            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              required
              minLength={6}
            />

            <Input
              label="Confirm Password"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repeat your password"
              required
              minLength={6}
            />

            {error && (
              <div className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">
                {error}
              </div>
            )}

            <Button type="submit" variant="brand" loading={loading} className="w-full">
              Create Account
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-text-tertiary">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand hover:text-brand-light transition-colors">
            Sign in
          </Link>
        </p>

        <div className="mt-4 text-center">
          <Link href="/auth" className="text-xs text-text-tertiary hover:text-text-secondary transition-colors underline underline-offset-2">
            Use API Key Instead
          </Link>
        </div>
      </div>
    </div>
  );
}
