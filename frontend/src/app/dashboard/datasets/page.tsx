"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/contexts/AuthContext";
import {
  DatasetSummary,
  deleteDataset,
  listDatasets,
} from "@/lib/authApi";

export default function DatasetsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) router.replace("/sign-in");
  }, [authLoading, user, router]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDatasets(await listDatasets());
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void refresh();
  }, [user, refresh]);

  async function handleDelete(id: number, title: string) {
    if (!confirm(`Delete "${title}" and all its segments and rankings? This cannot be undone.`))
      return;
    try {
      await deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "delete failed");
    }
  }

  if (authLoading || !user) {
    return <div className="max-w-5xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Your data uploads</h1>
          <p className="text-slate-600 mt-2">
            Upload CSV or XLSX files and rank entities across one or many segments.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard"
            className="px-3 py-2 rounded-md border border-slate-300 text-slate-700 text-sm hover:bg-slate-50"
          >
            Saved rankings
          </Link>
          <Link
            href="/dashboard/datasets/new"
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            + New upload
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-slate-500">Loading…</div>
      ) : datasets.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-slate-600 mb-4">No datasets yet.</p>
          <Link
            href="/dashboard/datasets/new"
            className="inline-block px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            Upload your first file
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {datasets.map((d) => (
            <li
              key={d.id}
              className="bg-white rounded-lg shadow p-4 flex flex-wrap items-center gap-4 justify-between"
            >
              <div className="flex-1 min-w-0">
                <Link
                  href={`/dashboard/datasets/${d.id}`}
                  className="font-medium text-slate-900 hover:text-blue-700 truncate block"
                >
                  {d.title}
                </Link>
                <div className="text-xs text-slate-500 mt-0.5">
                  {d.segment_count} segment{d.segment_count === 1 ? "" : "s"} · {d.total_rows} rows
                  {" · "}name col: <code className="text-slate-700">{d.name_column}</code>
                  {" · "}updated {new Date(d.updated_at).toLocaleDateString()}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/dashboard/datasets/${d.id}`}
                  className="px-3 py-1 rounded-md border border-slate-300 text-slate-700 text-xs hover:bg-slate-50"
                >
                  Open
                </Link>
                <button
                  onClick={() => handleDelete(d.id, d.title)}
                  className="px-3 py-1 rounded-md border border-red-300 text-red-700 text-xs hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
