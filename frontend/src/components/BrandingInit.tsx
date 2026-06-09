"use client";

import { useEffect } from "react";
import { getApiKey } from "@/utils/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const BRANDING_KEY = "retromind_branding";

export function applyBranding(branding: {
  logo_url?: string;
  primary_color?: string;
  secondary_color?: string;
}) {
  const root = document.documentElement;
  if (branding.primary_color) {
    root.style.setProperty("--brand-primary", branding.primary_color);
  }
  if (branding.secondary_color) {
    root.style.setProperty("--brand-secondary", branding.secondary_color);
  }
}

export default function BrandingInit() {
  useEffect(() => {
    const key = getApiKey();
    if (!key) return;

    const cached = localStorage.getItem(BRANDING_KEY);
    if (cached) {
      try {
        applyBranding(JSON.parse(cached));
      } catch {}
    }

    fetch(`${API_BASE}/workshop/branding`, {
      headers: key ? { "X-API-Key": key } : {},
    })
      .then((r) => r.json())
      .then((data) => {
        localStorage.setItem(BRANDING_KEY, JSON.stringify(data));
        applyBranding(data);
      })
      .catch(() => {});
  }, []);

  return null;
}
