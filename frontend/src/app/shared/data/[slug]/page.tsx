"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import DatasetResultsTable from "@/components/custom_data/DatasetResultsTable";
import {
  SharedDatasetRankingView,
  getSharedDatasetRanking,
} from "@/lib/authApi";

export default function SharedDatasetRankingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug;
  const [data, setData] = useState<SharedDatasetRankingView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    (async () => {
      setLoading(true);
      try {
        setData(await getSharedDatasetRanking(slug));
      } catch (err) {
        setError(err instanceof Error ? err.message : "not found");
      } finally {
        setLoading(false);
      }
    })();
  }, [slug]);

  if (loading) {
    return <div className="max-w-7xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }
  if (error || !data) {
    return (
      <div className="max-w-md mx-auto px-4 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm">
          {error ?? "not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900">{data.title}</h1>
        <p className="text-sm text-slate-500 mt-1">
          {data.dataset_title} · {data.mode}
          {" · "}
          {data.share_mode === "frozen"
            ? data.results_computed_at
              ? `frozen snapshot from ${new Date(data.results_computed_at).toLocaleDateString()}`
              : "frozen snapshot"
            : "live — recomputed on each view"}
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-5">
        <DatasetResultsTable
          results={data.results}
          categories={data.categories}
          showSegments={data.mode !== "single"}
        />
      </div>
    </div>
  );
}
