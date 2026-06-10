"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { useUser } from "@/contexts/UserContext";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useUser();

  useEffect(() => {
    const token = searchParams.get("token");
    const workshopId = searchParams.get("workshop_id");

    if (token && login) {
      const payload = JSON.parse(atob(token.split(".")[1]));
      login(token, { id: payload.sub, email: payload.email || "", name: payload.name || "" }, []);
    }
    if (workshopId) {
      localStorage.setItem("retromind_workshop_id", workshopId);
    }

    router.replace(token ? "/" : "/login");
  }, [searchParams, router, login]);

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
      <p className="text-sm text-text-secondary">Completing sign in...</p>
    </div>
  );
}

export default function SSOCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <p className="text-sm text-text-secondary">Completing sign in...</p>
      </div>
    }>
      <CallbackInner />
    </Suspense>
  );
}
