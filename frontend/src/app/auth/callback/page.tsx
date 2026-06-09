"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    const workshopId = searchParams.get("workshop_id");

    if (token) {
      localStorage.setItem("retromind_jwt", token);
    }
    if (workshopId) {
      localStorage.setItem("retromind_workshop_id", workshopId);
    }

    router.replace(token ? "/" : "/login");
  }, [searchParams, router]);

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
