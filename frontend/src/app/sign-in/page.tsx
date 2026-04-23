"use client";

import { FormEvent, useState } from "react";

import { requestMagicLink } from "@/lib/authApi";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await requestMagicLink(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold text-slate-900 mb-2">Sign in</h1>
      <p className="text-slate-600 mb-6">
        Enter your email and we&apos;ll send you a sign-in link.
      </p>

      {sent ? (
        <div className="bg-green-50 border border-green-200 text-green-900 rounded-md p-4">
          <p className="font-medium">Check your inbox.</p>
          <p className="text-sm mt-1">
            We sent a sign-in link to <strong>{email}</strong>. It expires in 15 minutes.
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Email</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </label>
          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-slate-900 px-4 py-2 text-white font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Sending…" : "Send link"}
          </button>
        </form>
      )}
    </div>
  );
}
