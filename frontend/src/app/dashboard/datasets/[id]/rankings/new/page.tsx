"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import DatasetCategoryBuilder from "@/components/custom_data/DatasetCategoryBuilder";
import SegmentMultiSelect from "@/components/custom_data/SegmentMultiSelect";
import { useAuth } from "@/contexts/AuthContext";
import {
  DatasetDetail,
  DatasetRankingCategory,
  DatasetRankingMode,
  createDatasetRanking,
  getDataset,
} from "@/lib/authApi";

export default function NewDatasetRankingPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const datasetId = Number(params.id);

  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [title, setTitle] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mode, setMode] = useState<DatasetRankingMode>("single");
  const [gamesColumn, setGamesColumn] = useState<string | null>(null);
  const [categories, setCategories] = useState<DatasetRankingCategory[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) router.replace("/sign-in");
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user || !datasetId) return;
    getDataset(datasetId)
      .then((ds) => {
        setDataset(ds);
        // default: select most recent segment, single mode
        if (ds.segments.length > 0) {
          const newest = ds.segments[ds.segments.length - 1];
          setSelectedIds([newest.id]);
        }
        // start with one empty category
        setCategories([
          {
            id: `cat_${Date.now()}_0`,
            name: "Score",
            weight: 1,
            stats: [],
          },
        ]);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "failed"));
  }, [user, datasetId]);

  const numericColumns = useMemo(
    () => (dataset?.column_schema ?? []).filter((c) => c.dtype === "numeric"),
    [dataset]
  );

  async function handleSubmit() {
    setError(null);
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    if (selectedIds.length === 0) {
      setError("Select at least one segment.");
      return;
    }
    if (mode === "single" && selectedIds.length !== 1) {
      setError("Single mode requires exactly one segment.");
      return;
    }
    if (mode === "per_game" && !gamesColumn) {
      setError("Per-game mode requires a games column.");
      return;
    }
    const validCats = categories
      .map((c) => ({ ...c, stats: c.stats.filter((s) => s.name) }))
      .filter((c) => c.stats.length > 0);
    if (validCats.length === 0) {
      setError("Add at least one category with at least one stat.");
      return;
    }
    setSubmitting(true);
    try {
      const ranking = await createDatasetRanking(datasetId, {
        title: title.trim(),
        categories: validCats,
        mode,
        segment_ids: selectedIds,
        games_column: mode === "per_game" ? gamesColumn : null,
      });
      router.push(`/dashboard/datasets/${datasetId}/rankings/${ranking.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to create");
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading || !user) {
    return <div className="max-w-5xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-4">
        <Link
          href={`/dashboard/datasets/${datasetId}`}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          ← Back to dataset
        </Link>
      </div>

      <h1 className="text-2xl font-bold text-slate-900 mb-2">New ranking</h1>
      {dataset && (
        <p className="text-slate-600 mb-6 text-sm">
          For <span className="font-medium">{dataset.title}</span>
        </p>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {dataset && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-lg shadow p-5">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="My ranking"
                className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm"
              />
            </div>

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
            <div className="mt-4 flex justify-end">
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "Computing…" : "Create ranking"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
