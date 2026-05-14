"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { useAuth } from "@/contexts/AuthContext";
import {
  DatasetDetail,
  DatasetRankingSummary,
  deleteDatasetRanking,
  deleteSegment,
  getDataset,
  listDatasetRankings,
} from "@/lib/authApi";

export default function DatasetDetailPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const datasetId = Number(params.id);

  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [rankings, setRankings] = useState<DatasetRankingSummary[]>([]);
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
      const [ds, allRankings] = await Promise.all([
        getDataset(datasetId),
        listDatasetRankings(),
      ]);
      setDataset(ds);
      setRankings(allRankings.filter((r) => r.dataset_id === datasetId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load");
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    if (user && datasetId) void refresh();
  }, [user, datasetId, refresh]);

  async function handleDeleteSegment(segmentId: number, label: string) {
    if (!confirm(`Delete segment "${label}"? Rows in this segment will be removed.`))
      return;
    try {
      await deleteSegment(datasetId, segmentId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "delete failed");
    }
  }

  async function handleDeleteRanking(id: number, title: string) {
    if (!confirm(`Delete ranking "${title}"?`)) return;
    try {
      await deleteDatasetRanking(id);
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
      <div className="mb-4">
        <Link href="/dashboard/datasets" className="text-sm text-slate-600 hover:text-slate-900">
          ← Back to data uploads
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {loading || !dataset ? (
        <div className="text-slate-500">Loading…</div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4 mb-2">
            <h1 className="text-2xl font-bold text-slate-900">{dataset.title}</h1>
            <Link
              href={`/dashboard/datasets/${dataset.id}/rankings/new`}
              className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
            >
              + New ranking
            </Link>
          </div>
          <p className="text-sm text-slate-600 mb-6">
            Name column: <code className="text-slate-800">{dataset.name_column}</code>
            {" · "}
            {dataset.column_schema.length} other column
            {dataset.column_schema.length === 1 ? "" : "s"}
          </p>

          <section className="bg-white rounded-lg shadow p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-slate-900">Segments</h2>
              <Link
                href={`/dashboard/datasets/${dataset.id}/append`}
                className="px-3 py-1.5 rounded-md border border-slate-300 text-slate-700 text-xs hover:bg-slate-50"
              >
                + Append upload
              </Link>
            </div>
            {dataset.segments.length === 0 ? (
              <p className="text-sm text-slate-500">No segments yet.</p>
            ) : (
              <ul className="divide-y divide-slate-200">
                {dataset.segments.map((s) => (
                  <li key={s.id} className="py-2 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-slate-900">{s.label}</div>
                      <div className="text-xs text-slate-500">
                        {s.row_count} rows
                        {s.source_filename ? ` · ${s.source_filename}` : ""}
                        {" · "}added {new Date(s.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteSegment(s.id, s.label)}
                      className="px-3 py-1 rounded-md border border-red-300 text-red-700 text-xs hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="bg-white rounded-lg shadow p-5 mb-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Schema</h2>
            <ul className="text-sm text-slate-700 flex flex-wrap gap-2">
              {dataset.column_schema.map((c) => (
                <li
                  key={c.name}
                  className="px-2 py-1 rounded border border-slate-200 bg-slate-50"
                >
                  <code className="text-slate-900">{c.name}</code>
                  <span className="text-slate-500 ml-1">({c.dtype})</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500 mt-3">
              Entities are matched across segments by a normalized form of the
              name column (lowercase, alphanumerics only). Variants like
              &quot;P. Mahomes&quot; won&apos;t merge with &quot;Patrick Mahomes&quot;.
            </p>
          </section>

          <section className="bg-white rounded-lg shadow p-5">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Rankings</h2>
            {rankings.length === 0 ? (
              <p className="text-sm text-slate-500">
                No rankings yet. Configure one to score entities in this dataset.
              </p>
            ) : (
              <ul className="divide-y divide-slate-200">
                {rankings.map((r) => (
                  <li key={r.id} className="py-2 flex items-center justify-between">
                    <Link
                      href={`/dashboard/datasets/${dataset.id}/rankings/${r.id}`}
                      className="text-sm font-medium text-slate-900 hover:text-blue-700"
                    >
                      {r.title}
                    </Link>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-500">
                        {r.mode} · {r.segment_ids.length} segment
                        {r.segment_ids.length === 1 ? "" : "s"}
                      </span>
                      <button
                        onClick={() => handleDeleteRanking(r.id, r.title)}
                        className="px-3 py-1 rounded-md border border-red-300 text-red-700 text-xs hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
