"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { fetchPositionConfig, PositionGroupDetail } from "@/lib/api";
import { getSharedRanking, SharedRankingView } from "@/lib/authApi";
import RankingsResultsTable, {
  RankingsCategoryColumn,
  RankingsResultsPlayer,
} from "@/components/RankingsResultsTable";

export default function SharedRankingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug;

  const [data, setData] = useState<SharedRankingView | null>(null);
  const [config, setConfig] = useState<PositionGroupDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    (async () => {
      setLoading(true);
      try {
        const shared = await getSharedRanking(slug);
        setData(shared);
        try {
          setConfig(await fetchPositionConfig(shared.position_group));
        } catch {
          setConfig(null);
        }
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

  const players = data.results as unknown as RankingsResultsPlayer[];

  // Derive category columns from the first player's category_scores. When the
  // saved ranking includes user-defined categories, prefer those names;
  // otherwise fall back to the position config's labels.
  const categoryIds = players[0] ? Object.keys(players[0].category_scores ?? {}) : [];
  const nameMap: Record<string, string> = {};
  if (data.categories) {
    for (const cat of data.categories) nameMap[cat.id] = cat.name;
  } else if (config) {
    for (const cat of config.categories) nameMap[cat.id] = cat.name;
  }
  const categories: RankingsCategoryColumn[] = categoryIds.map((id) => ({
    id,
    name: nameMap[id] ?? id,
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900">{data.title}</h1>
        <p className="text-sm text-slate-500 mt-1">
          {data.share_mode === "frozen"
            ? data.results_computed_at
              ? `Frozen snapshot from ${new Date(data.results_computed_at).toLocaleDateString()}`
              : "Frozen snapshot"
            : "Live — recomputed on each view"}
        </p>
      </div>

      <RankingsResultsTable
        players={players}
        categories={categories}
        exportFilenameBase={`shared_${slug}`}
      />
    </div>
  );
}
