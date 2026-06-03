const API_BASE = "http://localhost:8000/api/v1";

let _keyPromise: Promise<string> | null = null;

async function fetchDemoKey(): Promise<string> {
  try {
    const res = await fetch(`${API_BASE}/setup/demo-key`);
    if (!res.ok) return "";
    const data = await res.json();
    return data.api_key || "";
  } catch {
    return "";
  }
}

export function getApiKey(): string {
  return typeof window !== "undefined"
    ? localStorage.getItem("retromind_api_key") || process.env.NEXT_PUBLIC_API_KEY || ""
    : process.env.NEXT_PUBLIC_API_KEY || "";
}

export async function ensureApiKey(): Promise<string> {
  const existing = getApiKey();
  if (existing) return existing;

      res = await fetch(`${API_BASE}${path}`, { ...options, headers: h });
    }
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${options.method || "GET"} ${path} failed (${res.status}): ${body}`);
  }
  return res.json();
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, {
    headers: await headers(),
  });
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    headers: await headers(!!body),
    body: body ? JSON.stringify(body) : undefined,
  });
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const key = getApiKey();
  const h: Record<string, string> = {};
  if (key) {
    h["X-API-Key"] = key;
  }

  let res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: h,
    body: formData,
  });

  if (res.status === 401) {
    const demoKey = await recoverWithDemoKey();
    if (demoKey) {
      h["X-API-Key"] = demoKey;
      res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: h,
        body: formData,
      });
    }
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function recoverWithDemoKey(): Promise<string | null> {
  const demoKey = await fetchDemoKey();
  if (demoKey) {
    setApiKey(demoKey);
    return demoKey;
  }
  return null;
}

export function setApiKey(key: string) {
  localStorage.setItem("retromind_api_key", key);
}

export function clearApiKey() {
  localStorage.removeItem("retromind_api_key");
  _keyPromise = null;
}

export function getJwt(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("retromind_jwt");
}

export function setJwt(token: string) {
  localStorage.setItem("retromind_jwt", token);
}

export function clearJwt() {
  localStorage.removeItem("retromind_jwt");
}
