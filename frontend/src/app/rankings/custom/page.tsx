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
} from "@/lib/api";

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
  weight: number; // raw weight before normalization
}

type SortKey = string;

function getScoreColor(score: number) {
  if (score >= 90) return "text-green-600 font-semibold";
  if (score >= 80) return "text-blue-600";
  if (score >= 70) return "text-slate-600";
  return "text-red-600";
}

const SHORT_NAMES: Record<string, string> = {
  run_defense: "Run Def",
  pass_rush: "Pass Rush",
  coverage: "Coverage",
  playmaking: "Playmaking",
  efficiency: "Efficiency",
  volume: "Volume",
  ball_security: "Ball Sec",
  scoring: "Scoring",
  receiving: "Receiving",
  accuracy: "Accuracy",
  clutch: "Clutch",
};

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

  const [selectedGroup, setSelectedGroup] = useState("DEF");
  const [config, setConfig] = useState<PositionGroupDetail | null>(null);
  const [categories, setCategories] = useState<CategoryState[]>([]);
  const [minGames, setMinGames] = useState(1);
  const [positionFilter, setPositionFilter] = useState("All");
  const [players, setPlayers] = useState<PlayerDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortConfig, setSortConfig] = useState<{
    key: SortKey;
    direction: "asc" | "desc";
  } | null>(null);

  // Season/Career mode state
  const [mode, setMode] = useState<"season" | "career">(initialMode);
  const [careerMode, setCareerMode] = useState<"cumulative" | "per_game">("cumulative");
  const [minSeasons, setMinSeasons] = useState(3);

  // Compute normalized weights
  const normalizedWeights = useMemo(() => {
    const enabled = categories.filter((c) => c.enabled);
    const total = enabled.reduce((sum, c) => sum + c.weight, 0);
    const result: Record<string, number> = {};
    for (const cat of categories) {
      if (!cat.enabled || total === 0) {
        result[cat.id] = 0;
      } else {
        result[cat.id] = cat.weight / total;
      }
    }
    return result;
  }, [categories]);

  const totalDisplayPct = useMemo(() => {
    const enabled = categories.filter((c) => c.enabled);
    if (enabled.length === 0) return 0;
    return 100;
  }, [categories]);

  // Load position config
  const loadConfig = useCallback(
    async (groupId: string) => {
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
        setSortConfig(null);
      } catch {
        setError("Failed to load position config. Is the backend running?");
      } finally {
        setConfigLoading(false);
      }
    },
    []
  );

  // Load config on first render and when group changes
  const handleGroupChange = useCallback(
    (groupId: string) => {
      setSelectedGroup(groupId);
      loadConfig(groupId);
    },
    [loadConfig]
  );

  // Load initial config
  useState(() => {
    loadConfig("DEF");
  });

  // Handle mode toggle
  const handleModeChange = (newMode: "season" | "career") => {
    setMode(newMode);
    setPlayers([]);
    setSortConfig(null);
    // Reset min games to sensible default for mode
    if (newMode === "career") {
      setMinGames(1);
    } else {
      setMinGames(1);
    }
  };

  const toggleCategory = (catId: string) => {
    setCategories((prev) =>
      prev.map((c) =>
        c.id === catId ? { ...c, enabled: !c.enabled } : c
      )
    );
  };

  const updateWeight = (catId: string, newWeight: number) => {
    setCategories((prev) =>
      prev.map((c) => (c.id === catId ? { ...c, weight: newWeight } : c))
    );
  };

  const resetToDefaults = () => {
    setCategories((prev) =>
      prev.map((c) => ({
        ...c,
        enabled: true,
        weight: c.defaultWeight,
      }))
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
      setSortConfig(null);
    } catch {
      setError("Failed to calculate rankings. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // Sort logic
  const handleSort = (key: SortKey) => {
    setSortConfig((current) => {
      if (current?.key === key) {
        return current.direction === "desc"
          ? { key, direction: "asc" }
          : null;
      }
      return { key, direction: "desc" };
    });
  };

  const getSortIndicator = (key: SortKey) => {
    if (sortConfig?.key !== key) return null;
    return sortConfig.direction === "asc" ? " \u2191" : " \u2193";
  };

  const enabledCategories = useMemo(
    () => categories.filter((c) => c.enabled),
    [categories]
  );

  const filteredAndSortedPlayers = useMemo(() => {
    let result = players;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((p) => p.name.toLowerCase().includes(q));
    }
    if (!sortConfig) return result;

    return [...result].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      if (sortConfig.key === "name") {
        aVal = a.name;
        bVal = b.name;
      } else if (sortConfig.key === "team") {
        aVal = a.team;
        bVal = b.team;
      } else if (sortConfig.key === "position") {
        aVal = a.position;
        bVal = b.position;
      } else if (sortConfig.key === "games_played") {
        aVal = a.games_played;
        bVal = b.games_played;
      } else if (sortConfig.key === "overall_score") {
        aVal = a.overall_score;
        bVal = b.overall_score;
      } else {
        aVal = a.category_scores[sortConfig.key] || 0;
        bVal = b.category_scores[sortConfig.key] || 0;
      }

      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
  }, [players, searchQuery, sortConfig]);

  const exportCSV = () => {
    if (players.length === 0) return;

    const headers = [
      "Rank",
      "Player",
      "Team",
      "Pos",
      "GP",
      "Overall",
      ...enabledCategories.map((c) => c.name),
    ];
    const rows = filteredAndSortedPlayers.map((p, i) => [
      i + 1,
      p.name,
      p.team,
      p.position,
      p.games_played,
      p.overall_score.toFixed(1),
      ...enabledCategories.map((c) =>
        (p.category_scores[c.id] || 0).toFixed(1)
      ),
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((r) =>
        r.map((v) => (typeof v === "string" && v.includes(",") ? `"${v}"` : v)).join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const modeLabel = mode === "career" ? `career_${careerMode}` : "season";
    link.download = `custom_rankings_${selectedGroup}_${modeLabel}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const formatScore = (score: number) => score.toFixed(1);

  const maxGames = mode === "career" ? 400 : 17;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Link
            href="/rankings"
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            &larr; Back to Rankings
          </Link>
        </div>
        <h1 className="text-3xl font-bold text-slate-900">Custom Rankings</h1>
        <p className="text-slate-600 mt-2">
          Toggle stat categories on/off and adjust their weights to create your
          own player rankings.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        {/* Season/Career Toggle */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="flex rounded-lg overflow-hidden border border-slate-300 w-fit">
            <button
              onClick={() => handleModeChange("season")}
              className={`px-5 py-2 text-sm font-medium transition-colors ${
                mode === "season"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Season
            </button>
            <button
              onClick={() => handleModeChange("career")}
              className={`px-5 py-2 text-sm font-medium transition-colors border-l border-slate-300 ${
                mode === "career"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Career
            </button>
          </div>

          {/* Career sub-toggle */}
          {mode === "career" && (
            <div className="flex rounded-lg overflow-hidden border border-slate-300 w-fit">
              <button
                onClick={() => { setCareerMode("cumulative"); setPlayers([]); }}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  careerMode === "cumulative"
                    ? "bg-slate-700 text-white"
                    : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                Cumulative
              </button>
              <button
                onClick={() => { setCareerMode("per_game"); setPlayers([]); }}
                className={`px-4 py-2 text-sm font-medium transition-colors border-l border-slate-300 ${
                  careerMode === "per_game"
                    ? "bg-slate-700 text-white"
                    : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                Per Game
              </button>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-4 mb-6">
          {/* Position Group Selector */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Position Group
            </label>
            <select
              value={selectedGroup}
              onChange={(e) => handleGroupChange(e.target.value)}
              className="block w-48 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            >
              {POSITION_GROUPS.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>

          {/* Min Games */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Min Games
            </label>
            <input
              type="number"
              min="1"
              max={maxGames}
              value={minGames}
              onChange={(e) => setMinGames(Math.min(parseInt(e.target.value) || 1, maxGames))}
              className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            />
          </div>

          {/* Min Seasons (career only) */}
          {mode === "career" && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Min Seasons
              </label>
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

          {/* Sub-position filter (season only) */}
          {mode === "season" && config?.sub_positions && config.sub_positions.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Position
              </label>
              <select
                value={positionFilter}
                onChange={(e) => setPositionFilter(e.target.value)}
                className="block w-36 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
              >
                {config.sub_positions.map((pos) => (
                  <option key={pos} value={pos}>
                    {pos === "All" ? "All Positions" : pos}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Category Cards */}
        {configLoading ? (
          <div className="text-center py-4 text-slate-500">
            Loading categories...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
              {categories.map((cat) => {
                const normalizedPct =
                  normalizedWeights[cat.id] !== undefined
                    ? (normalizedWeights[cat.id] * 100).toFixed(1)
                    : "0.0";
                return (
                  <div
                    key={cat.id}
                    className={`rounded-lg border p-4 transition-colors ${
                      cat.enabled
                        ? "border-blue-300 bg-blue-50"
                        : "border-slate-200 bg-slate-50 opacity-60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium text-slate-900 text-sm">
                        {cat.name}
                      </span>
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
                        onChange={(e) =>
                          updateWeight(cat.id, parseFloat(e.target.value))
                        }
                        disabled={!cat.enabled}
                        className="flex-1 h-2 accent-blue-600 disabled:opacity-40"
                      />
                      <span className="text-sm font-mono text-slate-700 w-14 text-right">
                        {normalizedPct}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Total Weight + Buttons */}
            <div className="flex flex-wrap items-center gap-4">
              <div className="text-sm text-slate-600">
                Total:{" "}
                <span
                  className={`font-semibold ${
                    totalDisplayPct === 100
                      ? "text-green-600"
                      : "text-amber-600"
                  }`}
                >
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
                disabled={
                  loading || categories.filter((c) => c.enabled).length === 0
                }
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Calculating..." : "Calculate Rankings"}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {players.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {/* Search + Export */}
          <div className="flex flex-wrap items-center gap-4 p-4 border-b border-slate-200">
            <input
              type="text"
              placeholder="Search by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-48 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border text-sm"
            />
            <button
              onClick={exportCSV}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
            >
              Export CSV
            </button>
            <span className="text-sm text-slate-500 ml-auto">
              {filteredAndSortedPlayers.length} players
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                    onClick={() => handleSort("name")}
                  >
                    Player{getSortIndicator("name")}
                  </th>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                    onClick={() => handleSort("team")}
                  >
                    Team{getSortIndicator("team")}
                  </th>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                    onClick={() => handleSort("position")}
                  >
                    Pos{getSortIndicator("position")}
                  </th>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                    onClick={() => handleSort("games_played")}
                  >
                    GP{getSortIndicator("games_played")}
                  </th>
                  <th
                    className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                    onClick={() => handleSort("overall_score")}
                  >
                    Overall{getSortIndicator("overall_score")}
                  </th>
                  {enabledCategories.map((cat) => (
                    <th
                      key={cat.id}
                      className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                      onClick={() => handleSort(cat.id)}
                    >
                      {SHORT_NAMES[cat.id] || cat.name}
                      {getSortIndicator(cat.id)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {filteredAndSortedPlayers.map((player, index) => (
                  <tr
                    key={player.id}
                    className="hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900">
                      {index + 1}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900">
                      {player.name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                      {player.team}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                      {player.position}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                      {player.games_played}
                    </td>
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                        player.overall_score
                      )}`}
                    >
                      {formatScore(player.overall_score)}
                    </td>
                    {enabledCategories.map((cat) => (
                      <td
                        key={cat.id}
                        className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                          player.category_scores[cat.id] || 0
                        )}`}
                      >
                        {formatScore(player.category_scores[cat.id] || 0)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredAndSortedPlayers.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No players found matching the criteria.
            </div>
          )}
        </div>
      )}

      {/* Loading state for calculate */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Calculating custom rankings...</p>
        </div>
      )}
    </div>
  );
}
