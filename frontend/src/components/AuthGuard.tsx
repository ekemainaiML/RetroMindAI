"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getApiKey, getJwt } from "@/utils/api";

const PUBLIC_PATHS = new Set(["/auth", "/login", "/signup"]);

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (PUBLIC_PATHS.has(pathname)) {
      setReady(true);
      return;
    }
    if (pathname === "/admin") {
      setReady(true);
      return;
    }
    const hasApiKey = !!getApiKey();
    const hasJwt = !!getJwt();
    if (!hasApiKey && !hasJwt) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [pathname, router]);

  if (!ready) return null;

  return <>{children}</>;
}
