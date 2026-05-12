"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/contexts/AuthContext";
import {
  deleteSavedRanking,
  listSavedRankings,
  SavedRankingSummary,
  updateSavedRanking,
} from "@/lib/authApi";
import { ShareMode } from "@/components/SaveRankingModal";
import NewRankingChooserModal from "@/components/NewRankingChooserModal";

const POSITION_GROUP_NAMES: Record<string, string> = {
  DEF: "Defense",
  QB: "Quarterbacks",
  RB: "Running Backs",
  WR: "Wide Receivers",
  TE: "Tight Ends",
  K: "Kickers",
};

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [rankings, setRankings] = useState<SavedRankingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chooserOpen, setChooserOpen] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace("/sign-in");
      return;
    }
  }, [authLoading, user, router]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRankings(await listSavedRankings());
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void refresh();
  }, [user, refresh]);

  async function handleShareModeChange(id: number, share_mode: ShareMode) {
    try {
      await updateSavedRanking(id, { share_mode });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "update failed");
    }
  }

  async function handleDelete(id: number, title: string) {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      await deleteSavedRanking(id);
      setRankings((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "delete failed");
    }
  }

  if (authLoading || !user) {
    return <div className="max-w-5xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Your saved rankings</h1>
          <p className="text-slate-600 mt-2">Signed in as {user.email}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard/datasets"
            className="px-3 py-2 rounded-md border border-slate-300 text-slate-700 text-sm hover:bg-slate-50"
          >
            Data uploads
          </Link>
          <button
            onClick={() => setChooserOpen(true)}
            className="inline-block px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            + New ranking
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-slate-500">Loading…</div>
      ) : rankings.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-slate-600 mb-4">No saved rankings yet.</p>
          <button
            onClick={() => setChooserOpen(true)}
            className="inline-block px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            Create your first ranking
          </button>
        </div>
      ) : (
        <ul className="space-y-3">
          {rankings.map((r) => {
            const shareUrl =
              r.share_slug && typeof window !== "undefined"
                ? `${window.location.origin}/shared/${r.share_slug}`
                : null;
            return (
              <li
                key={r.id}
                className="bg-white rounded-lg shadow p-4 flex flex-wrap items-center gap-4 justify-between"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-900 truncate">{r.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {POSITION_GROUP_NAMES[r.position_group] ?? r.position_group}
                    {" · "}
                    updated {new Date(r.updated_at).toLocaleDateString()}
                  </div>
                  {shareUrl && (
                    <a
                      href={shareUrl}
                      className="text-xs text-blue-600 hover:text-blue-800 underline break-all block mt-1"
                    >
                      {shareUrl}
                    </a>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <label className="text-xs text-slate-600 flex items-center gap-2">
                    Share:
                    <select
                      value={r.share_mode}
                      onChange={(e) =>
                        handleShareModeChange(r.id, e.target.value as ShareMode)
                      }
                      className="rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1 text-xs"
                    >
                      <option value="none">Private</option>
                      <option value="live">Live</option>
                      <option value="frozen">Frozen</option>
                    </select>
                  </label>
                  <button
                    onClick={() => handleDelete(r.id, r.title)}
                    className="px-3 py-1 rounded-md border border-red-300 text-red-700 text-xs hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <NewRankingChooserModal
        open={chooserOpen}
        onClose={() => setChooserOpen(false)}
      />
    </div>
  );
}
