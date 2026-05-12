"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import DatasetCategoryBuilder from "@/components/custom_data/DatasetCategoryBuilder";
import DatasetResultsTable from "@/components/custom_data/DatasetResultsTable";
import SegmentMultiSelect from "@/components/custom_data/SegmentMultiSelect";
import { useAuth } from "@/contexts/AuthContext";
import {
  DatasetDetail,
  DatasetRankingCategory,
  DatasetRankingDetail,
  DatasetRankingMode,
  getDataset,
  getDatasetRanking,
  updateDatasetRanking,
  updateDatasetRankingShare,
} from "@/lib/authApi";

type ShareMode = "none" | "live" | "frozen";

export default function DatasetRankingResultsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string; rankingId: string }>();
  const datasetId = Number(params.id);
  const rankingId = Number(params.rankingId);

  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [ranking, setRanking] = useState<DatasetRankingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // local edit state
  const [title, setTitle] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mode, setMode] = useState<DatasetRankingMode>("single");
  const [gamesColumn, setGamesColumn] = useState<string | null>(null);
  const [categories, setCategories] = useState<DatasetRankingCategory[]>([]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) router.replace("/sign-in");
  }, [authLoading, user, router]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [ds, r] = await Promise.all([
        getDataset(datasetId),
        getDatasetRanking(rankingId),
      ]);
      setDataset(ds);
      setRanking(r);
      setTitle(r.title);
      setSelectedIds(r.segment_ids);
      setMode(r.mode);
      setGamesColumn(r.games_column);
      setCategories(r.categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load");
    }
  }, [datasetId, rankingId]);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  const numericColumns = useMemo(
    () => (dataset?.column_schema ?? []).filter((c) => c.dtype === "numeric"),
    [dataset]
  );

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const validCats = categories
        .map((c) => ({ ...c, stats: c.stats.filter((s) => s.name) }))
        .filter((c) => c.stats.length > 0);
      const updated = await updateDatasetRanking(rankingId, {
        title: title.trim(),
        categories: validCats,
        mode,
        segment_ids: selectedIds,
        games_column: mode === "per_game" ? gamesColumn : null,
      });
      setRanking(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleShare(next: ShareMode) {
    setError(null);
    try {
      const updated = await updateDatasetRankingShare(rankingId, next);
      setRanking(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "share update failed");
    }
  }

  if (authLoading || !user) {
    return <div className="max-w-5xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }

  const shareUrl =
    ranking?.share_slug && typeof window !== "undefined"
      ? `${window.location.origin}/shared/data/${ranking.share_slug}`
      : null;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-4">
        <Link
          href={`/dashboard/datasets/${datasetId}`}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          ← Back to dataset
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {!ranking || !dataset ? (
        <div className="text-slate-500">Loading…</div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="text-2xl font-bold text-slate-900 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-none px-1"
            />
            <div className="flex items-center gap-3">
              <label className="text-xs text-slate-600 flex items-center gap-2">
                Share:
                <select
                  value={ranking.share_mode}
                  onChange={(e) => handleShare(e.target.value as ShareMode)}
                  className="rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1 text-xs"
                >
                  <option value="none">Private</option>
                  <option value="live">Live</option>
                  <option value="frozen">Frozen</option>
                </select>
              </label>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save & recompute"}
              </button>
            </div>
          </div>

          {shareUrl && (
            <div className="mb-4 text-xs text-blue-700">
              Share URL:{" "}
              <a href={shareUrl} className="underline break-all">
                {shareUrl}
              </a>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-1 space-y-6">
              <div className="bg-white rounded-lg shadow p-5">
                <SegmentMultiSelect
                  segments={dataset.segments}
                  selectedIds={selectedIds}
                  mode={mode}
                  gamesColumn={gamesColumn}
                  numericColumns={numericColumns}
                  onChange={(next) => {
                    setSelectedIds(next.selectedIds);
                    setMode(next.mode);
                    setGamesColumn(next.gamesColumn);
                  }}
                />
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="bg-white rounded-lg shadow p-5">
                <h2 className="text-lg font-semibold text-slate-900 mb-3">Categories</h2>
                <DatasetCategoryBuilder
                  categories={categories}
                  numericColumns={numericColumns}
                  onChange={setCategories}
                />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-5">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">
              Results ({ranking.results.length})
            </h2>
            <DatasetResultsTable
              results={ranking.results}
              categories={ranking.categories}
              showSegments={ranking.mode !== "single"}
            />
          </div>
        </>
      )}
    </div>
  );
}
