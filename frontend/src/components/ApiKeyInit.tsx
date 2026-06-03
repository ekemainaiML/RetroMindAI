"use client";

import { useEffect } from "react";
import { ensureApiKey } from "@/utils/api";

export default function ApiKeyInit() {
  useEffect(() => {
    ensureApiKey();
  }, []);

  return null;
}
