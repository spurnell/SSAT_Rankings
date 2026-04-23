"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/contexts/AuthContext";
import { verifyToken } from "@/lib/authApi";

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="max-w-md mx-auto px-4 py-16 text-slate-500">Signing you in…</div>}>
      <VerifyInner />
    </Suspense>
  );
}

function VerifyInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();
  const [status, setStatus] = useState<"verifying" | "error">("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setStatus("error");
      setError("missing token");
      return;
    }
    (async () => {
      try {
        await verifyToken(token);
        await refresh();
        router.replace("/dashboard");
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "verification failed");
      }
    })();
  }, [params, router, refresh]);

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      {status === "verifying" ? (
        <>
          <h1 className="text-2xl font-semibold text-slate-900">Signing you in…</h1>
          <p className="text-slate-600 mt-2">One moment.</p>
        </>
      ) : (
        <div className="bg-red-50 border border-red-200 text-red-900 rounded-md p-4">
          <p className="font-medium">Sign-in link invalid or expired.</p>
          {error && <p className="text-sm mt-1">{error}</p>}
          <a href="/sign-in" className="text-sm underline mt-2 inline-block">
            Request a new link
          </a>
        </div>
      )}
    </div>
  );
}
