"use client";

import { useState, useMemo, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  fetchPositionConfig,
  calculateRankings,
  CategoryDetailInfo,
  PositionGroupDetail,
  PlayerDetail,
  API_BASE_URL,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { createSavedRanking, SaveRankingPayload } from "@/lib/authApi";
import RankingsResultsTable from "@/components/RankingsResultsTable";
import SaveRankingModal, { ShareMode } from "@/components/SaveRankingModal";

const POSITION_GROUPS = [
  { id: "DEF", name: "Defensive Players" },
  { id: "QB", name: "Quarterbacks" },
  { id: "RB", name: "Running Backs" },
  { id: "WR", name: "Wide Receivers" },
  { id: "TE", name: "Tight Ends" },
  { id: "K", name: "Kickers" },
];

interface CategoryState {
  id: string;
  name: string;
  defaultWeight: number;
  enabled: boolean;
  weight: number;
}

export default function CustomRankingsPage() {
  return (
    <Suspense fallback={<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><div className="text-center py-12 text-slate-500">Loading...</div></div>}>
      <CustomRankingsContent />
    </Suspense>
  );
}

function CustomRankingsContent() {
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("mode") === "career" ? "career" : "season";
  const { user } = useAuth();

  const [selectedGroup, setSelectedGroup] = useState("DEF");
  const [config, setConfig] = useState<PositionGroupDetail | null>(null);
  const [categories, setCategories] = useState<CategoryState[]>([]);
  const [minGames, setMinGames] = useState(1);
  const [positionFilter, setPositionFilter] = useState("All");
  const [players, setPlayers] = useState<PlayerDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [mode, setMode] = useState<"season" | "career">(initialMode);
  const [careerMode, setCareerMode] = useState<"cumulative" | "per_game">("cumulative");
  const [minSeasons, setMinSeasons] = useState(3);

  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ kind: "ok" | "err"; text: string; url?: string } | null>(null);

  const normalizedWeights = useMemo(() => {
    const enabled = categories.filter((c) => c.enabled);
    const total = enabled.reduce((sum, c) => sum + c.weight, 0);
    const result: Record<string, number> = {};
    for (const cat of categories) {
      result[cat.id] = !cat.enabled || total === 0 ? 0 : cat.weight / total;
    }
    return result;
  }, [categories]);

  const totalDisplayPct = useMemo(() => {
    const enabled = categories.filter((c) => c.enabled);
    return enabled.length === 0 ? 0 : 100;
  }, [categories]);

  const loadConfig = useCallback(async (groupId: string) => {
    setConfigLoading(true);
    setError(null);
    try {
      const data = await fetchPositionConfig(groupId);
      setConfig(data);
      setCategories(
        data.categories.map((cat: CategoryDetailInfo) => ({
          id: cat.id,
          name: cat.name,
          defaultWeight: cat.weight,
          enabled: true,
          weight: cat.weight,
        }))
      );
      setPlayers([]);
      setPositionFilter("All");
    } catch {
      setError("Failed to load position config. Is the backend running?");
    } finally {
      setConfigLoading(false);
    }
  }, []);

  const handleGroupChange = useCallback((groupId: string) => {
    setSelectedGroup(groupId);
    loadConfig(groupId);
  }, [loadConfig]);

  useState(() => {
    loadConfig("DEF");
  });

  const handleModeChange = (newMode: "season" | "career") => {
    setMode(newMode);
    setPlayers([]);
    setMinGames(1);
  };

  const toggleCategory = (catId: string) => {
    setCategories((prev) => prev.map((c) => (c.id === catId ? { ...c, enabled: !c.enabled } : c)));
  };

  const updateWeight = (catId: string, newWeight: number) => {
    setCategories((prev) => prev.map((c) => (c.id === catId ? { ...c, weight: newWeight } : c)));
  };

  const resetToDefaults = () => {
    setCategories((prev) =>
      prev.map((c) => ({ ...c, enabled: true, weight: c.defaultWeight }))
    );
  };

  const handleCalculate = async () => {
    const enabledCount = categories.filter((c) => c.enabled).length;
    if (enabledCount === 0) {
      setError("Enable at least one category.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const apiMode =
        mode === "career"
          ? careerMode === "per_game"
            ? "career_per_game"
            : "career_cumulative"
          : "season";

      const data = await calculateRankings({
        position_group: selectedGroup,
        weights: normalizedWeights,
        min_games: minGames,
        position: mode === "season" && positionFilter !== "All" ? positionFilter : undefined,
        mode: apiMode,
        min_seasons: mode === "career" ? minSeasons : undefined,
      });
      setPlayers(data);
    } catch {
      setError("Failed to calculate rankings. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const enabledCategories = useMemo(() => categories.filter((c) => c.enabled), [categories]);

  async function handleSave(values: { title: string; share_mode: ShareMode }) {
    const apiMode =
      mode === "career"
        ? careerMode === "per_game"
          ? "career_per_game"
          : "career_cumulative"
        : "season";

    const payload: SaveRankingPayload = {
      title: values.title,
      share_mode: values.share_mode,
      position_group: selectedGroup,
      weights: normalizedWeights,
      min_games: minGames,
      position_filter:
        mode === "season" && positionFilter !== "All" ? positionFilter : undefined,
      mode: apiMode,
      min_seasons: mode === "career" ? minSeasons : undefined,
    };

    try {
      const saved = await createSavedRanking(payload);
      setSaveModalOpen(false);
      if (saved.share_slug) {
        const origin =
          typeof window !== "undefined" ? window.location.origin : API_BASE_URL;
        setSaveMessage({
          kind: "ok",
          text: `Saved — share URL:`,
          url: `${origin}/shared/${saved.share_slug}`,
        });
      } else {
        setSaveMessage({ kind: "ok", text: "Saved to your dashboard." });
      }
    } catch (err) {
      setSaveMessage({
        kind: "err",
        text: err instanceof Error ? err.message : "save failed",
      });
      throw err;
    }
  }

  const maxGames = mode === "career" ? 400 : 17;
  const resultCategoryColumns = enabledCategories.map((c) => ({ id: c.id, name: c.name }));
  const exportFilenameBase = `custom_rankings_${selectedGroup}_${
    mode === "career" ? `career_${careerMode}` : "season"
  }`;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Link href="/rankings" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
            &larr; Back to Rankings
          </Link>
        </div>
        <h1 className="text-3xl font-bold text-slate-900">Custom Rankings</h1>
        <p className="text-slate-600 mt-2">
          Toggle stat categories on/off and adjust their weights to create your own player rankings.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="flex rounded-lg overflow-hidden border border-slate-300 w-fit">
            <button
              onClick={() => handleModeChange("season")}
              className={`px-5 py-2 text-sm font-medium transition-colors ${
                mode === "season" ? "bg-blue-600 text-white" : "bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Season
            </button>
            <button
              onClick={() => handleModeChange("career")}
              className={`px-5 py-2 text-sm font-medium transition-colors border-l border-slate-300 ${
                mode === "career" ? "bg-blue-600 text-white" : "bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Career
            </button>
          </div>

          {mode === "career" && (
            <div className="flex rounded-lg overflow-hidden border border-slate-300 w-fit">
              <button
                onClick={() => { setCareerMode("cumulative"); setPlayers([]); }}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  careerMode === "cumulative" ? "bg-slate-700 text-white" : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                Cumulative
              </button>
              <button
                onClick={() => { setCareerMode("per_game"); setPlayers([]); }}
                className={`px-4 py-2 text-sm font-medium transition-colors border-l border-slate-300 ${
                  careerMode === "per_game" ? "bg-slate-700 text-white" : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                Per Game
              </button>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Position Group</label>
            <select
              value={selectedGroup}
              onChange={(e) => handleGroupChange(e.target.value)}
              className="block w-48 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            >
              {POSITION_GROUPS.map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Min Games</label>
            <input
              type="number"
              min="1"
              max={maxGames}
              value={minGames}
              onChange={(e) => setMinGames(Math.min(parseInt(e.target.value) || 1, maxGames))}
              className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            />
          </div>

          {mode === "career" && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Min Seasons</label>
              <input
                type="number"
                min="1"
                max="30"
                value={minSeasons}
                onChange={(e) => setMinSeasons(parseInt(e.target.value) || 1)}
                className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
              />
            </div>
          )}

          {mode === "season" && config?.sub_positions && config.sub_positions.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Position</label>
              <select
                value={positionFilter}
                onChange={(e) => setPositionFilter(e.target.value)}
                className="block w-36 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
              >
                {config.sub_positions.map((pos) => (
                  <option key={pos} value={pos}>{pos === "All" ? "All Positions" : pos}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {configLoading ? (
          <div className="text-center py-4 text-slate-500">Loading categories...</div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
              {categories.map((cat) => {
                const normalizedPct =
                  normalizedWeights[cat.id] !== undefined ? (normalizedWeights[cat.id] * 100).toFixed(1) : "0.0";
                return (
                  <div
                    key={cat.id}
                    className={`rounded-lg border p-4 transition-colors ${
                      cat.enabled ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-slate-50 opacity-60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium text-slate-900 text-sm">{cat.name}</span>
                      <button
                        onClick={() => toggleCategory(cat.id)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          cat.enabled ? "bg-blue-600" : "bg-slate-300"
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            cat.enabled ? "translate-x-6" : "translate-x-1"
                          }`}
                        />
                      </button>
                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0.01"
                        max="1"
                        step="0.01"
                        value={cat.weight}
                        onChange={(e) => updateWeight(cat.id, parseFloat(e.target.value))}
                        disabled={!cat.enabled}
                        className="flex-1 h-2 accent-blue-600 disabled:opacity-40"
                      />
                      <span className="text-sm font-mono text-slate-700 w-14 text-right">{normalizedPct}%</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="text-sm text-slate-600">
                Total:{" "}
                <span className={`font-semibold ${totalDisplayPct === 100 ? "text-green-600" : "text-amber-600"}`}>
                  {totalDisplayPct}%
                </span>
              </div>
              <button
                onClick={resetToDefaults}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
              >
                Reset to Defaults
              </button>
              <button
                onClick={handleCalculate}
                disabled={loading || categories.filter((c) => c.enabled).length === 0}
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Calculating..." : "Calculate Rankings"}
              </button>
              <button
                onClick={() => setSaveModalOpen(true)}
                disabled={!user || players.length === 0}
                title={
                  !user
                    ? "Sign in to save rankings"
                    : players.length === 0
                    ? "Calculate rankings first"
                    : undefined
                }
                className="px-6 py-2 text-sm font-medium text-white bg-emerald-600 rounded-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Save
              </button>
              {!user && (
                <Link href="/sign-in" className="text-sm text-blue-600 hover:text-blue-800 underline">
                  Sign in to save
                </Link>
              )}
            </div>
          </>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {saveMessage && (
        <div
          className={`rounded-lg p-4 mb-6 text-sm ${
            saveMessage.kind === "ok"
              ? "bg-emerald-50 border border-emerald-200 text-emerald-900"
              : "bg-red-50 border border-red-200 text-red-600"
          }`}
        >
          <div>{saveMessage.text}</div>
          {saveMessage.url && (
            <a href={saveMessage.url} className="underline break-all block mt-1">
              {saveMessage.url}
            </a>
          )}
        </div>
      )}

      {players.length > 0 && (
        <RankingsResultsTable
          players={players}
          categories={resultCategoryColumns}
          exportFilenameBase={exportFilenameBase}
        />
      )}

      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Calculating custom rankings...</p>
        </div>
      )}

      <SaveRankingModal
        open={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSubmit={handleSave}
      />
    </div>
  );
}
