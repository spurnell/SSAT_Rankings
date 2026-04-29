"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  API_BASE_URL,
  AvailableStatsResponse,
  CategoryInfo,
  CategoryStatGroup,
  CustomCategory,
  CustomCategoryStatSource,
  PlayerDetail,
  calculateRankings,
  fetchAvailableStats,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { createSavedRanking, SaveRankingPayload } from "@/lib/authApi";
import RankingsResultsTable from "@/components/RankingsResultsTable";
import SaveRankingModal, { ShareMode } from "@/components/SaveRankingModal";
import PlayerProfilePanel from "@/components/PlayerProfilePanel";
import MobileProfileSheet from "@/components/MobileProfileSheet";
import { calculateStatRanks } from "@/lib/playerRanks";

const POSITION_GROUPS = [
  { id: "DEF", name: "Defensive Players" },
  { id: "QB", name: "Quarterbacks" },
  { id: "RB", name: "Running Backs" },
  { id: "WR", name: "Wide Receivers" },
  { id: "TE", name: "Tight Ends" },
  { id: "K", name: "Kickers" },
];

const MAX_SUBCATEGORIES = 5;
const INITIAL_SUBCATEGORIES = 3;

// 5 distinct hues for sub-category color chips. Tailwind class triplets.
const SUBCAT_COLORS: Array<{ ring: string; bg: string; text: string; chip: string }> = [
  { ring: "ring-blue-500", bg: "bg-blue-100", text: "text-blue-800", chip: "bg-blue-500" },
  { ring: "ring-emerald-500", bg: "bg-emerald-100", text: "text-emerald-800", chip: "bg-emerald-500" },
  { ring: "ring-amber-500", bg: "bg-amber-100", text: "text-amber-800", chip: "bg-amber-500" },
  { ring: "ring-purple-500", bg: "bg-purple-100", text: "text-purple-800", chip: "bg-purple-500" },
  { ring: "ring-rose-500", bg: "bg-rose-100", text: "text-rose-800", chip: "bg-rose-500" },
];

interface SubCategoryState {
  id: string;
  name: string;
  weight: number;
}

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

function initialSubCategories(): SubCategoryState[] {
  return Array.from({ length: INITIAL_SUBCATEGORIES }, (_, i) => ({
    id: makeId(),
    name: `Category ${i + 1}`,
    weight: 1 / INITIAL_SUBCATEGORIES,
  }));
}

export default function CustomBuilderPage() {
  const { user } = useAuth();

  const [selectedGroup, setSelectedGroup] = useState("DEF");
  const [available, setAvailable] = useState<AvailableStatsResponse | null>(null);
  const [availableLoading, setAvailableLoading] = useState(false);

  const [subCats, setSubCats] = useState<SubCategoryState[]>(initialSubCategories);
  const [activeSubCatId, setActiveSubCatId] = useState<string>(() => "");
  // assignments: statKey ("source::name") → subCatId
  const [assignments, setAssignments] = useState<Record<string, string>>({});

  const [minGames, setMinGames] = useState(1);
  const [positionFilter, setPositionFilter] = useState("All");

  const [players, setPlayers] = useState<PlayerDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveMessage, setSaveMessage] = useState<
    { kind: "ok" | "err"; text: string; url?: string } | null
  >(null);

  const [selectedPlayerIds, setSelectedPlayerIds] = useState<number[]>([]);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const statRanks = useMemo(() => calculateStatRanks(players), [players]);

  const selectedPlayers = useMemo(
    () =>
      selectedPlayerIds
        .map((id) => players.find((p) => p.id === id))
        .filter((p): p is PlayerDetail => p !== undefined),
    [players, selectedPlayerIds]
  );

  const handleRowClick = (playerId: number) => {
    setSelectedPlayerIds((current) => {
      if (current.includes(playerId)) return current.filter((id) => id !== playerId);
      if (current.length < 2) return [...current, playerId];
      return [current[0], playerId];
    });
  };

  // Make sure we always have an active sub-category selected.
  useEffect(() => {
    if (!subCats.find((s) => s.id === activeSubCatId)) {
      setActiveSubCatId(subCats[0]?.id ?? "");
    }
  }, [subCats, activeSubCatId]);

  const loadAvailable = useCallback(
    async (groupId: string, pos: string) => {
      setAvailableLoading(true);
      setError(null);
      try {
        const data = await fetchAvailableStats(groupId, pos);
        setAvailable(data);
        // Prune assignments whose stat key is no longer in the available set
        // — e.g. switching DEF position from DL to CB drops every
        // pff_front7 stat, and switching position group entirely drops
        // anything that doesn't exist in the new universe.
        const allowedKeys = new Set(
          data.sources.flatMap((s) => s.stats.map((st) => st.key))
        );
        setAssignments((prev) => {
          const next: Record<string, string> = {};
          for (const [key, subId] of Object.entries(prev)) {
            if (allowedKeys.has(key)) next[key] = subId;
          }
          return next;
        });
      } catch {
        setError("Failed to load available stats. Is the backend running?");
      } finally {
        setAvailableLoading(false);
      }
    },
    [],
  );

  // Refetch on group or position change. Also clear stale results so the
  // table doesn't show a ranking computed against the previous filter.
  useEffect(() => {
    void loadAvailable(selectedGroup, positionFilter);
    setPlayers([]);
  }, [selectedGroup, positionFilter, loadAvailable]);

  // Reset position filter to "All" when the position group changes — the
  // previous filter (e.g. "DL") may not exist in the new group's options.
  useEffect(() => {
    setPositionFilter("All");
  }, [selectedGroup]);

  const subCatColor = (id: string) => {
    const idx = subCats.findIndex((s) => s.id === id);
    return SUBCAT_COLORS[idx >= 0 ? idx % SUBCAT_COLORS.length : 0];
  };

  const subPositions: string[] | null = useMemo(() => {
    // Sub-position filter only makes sense for DEF and only when standard data
    // is being used. Hide it otherwise.
    if (selectedGroup !== "DEF") return null;
    return ["All", "DL", "EDGE", "LB", "CB", "S"];
  }, [selectedGroup]);

  const normalizedWeights = useMemo(() => {
    const total = subCats.reduce((acc, s) => acc + (s.weight || 0), 0);
    if (total <= 0) return subCats.map(() => 0);
    return subCats.map((s) => s.weight / total);
  }, [subCats]);

  const totalAssignedStats = Object.keys(assignments).length;

  const toggleStat = (stat: { source: CustomCategoryStatSource; name: string }) => {
    if (!activeSubCatId) return;
    const key = `${stat.source}::${stat.name}`;
    setAssignments((prev) => {
      const next = { ...prev };
      if (next[key] === activeSubCatId) {
        // Already in active sub-category → unassign
        delete next[key];
      } else {
        next[key] = activeSubCatId;
      }
      return next;
    });
  };

  const removeAssignment = (key: string) => {
    setAssignments((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const renameSubCat = (id: string, name: string) => {
    setSubCats((prev) => prev.map((s) => (s.id === id ? { ...s, name } : s)));
  };

  const updateSubCatWeight = (id: string, weight: number) => {
    setSubCats((prev) => prev.map((s) => (s.id === id ? { ...s, weight } : s)));
  };

  const addSubCategory = () => {
    if (subCats.length >= MAX_SUBCATEGORIES) return;
    const newId = makeId();
    setSubCats((prev) => [
      ...prev,
      { id: newId, name: `Category ${prev.length + 1}`, weight: 1 / (prev.length + 1) },
    ]);
    setActiveSubCatId(newId);
  };

  const removeSubCategory = (id: string) => {
    if (subCats.length <= 1) return;
    setSubCats((prev) => prev.filter((s) => s.id !== id));
    setAssignments((prev) => {
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(prev)) {
        if (v !== id) next[k] = v;
      }
      return next;
    });
  };

  const buildPayloadCategories = useCallback((): CustomCategory[] => {
    return subCats.map((s, i) => {
      const stats = Object.entries(assignments)
        .filter(([, subId]) => subId === s.id)
        .map(([key]) => {
          const [source, name] = key.split("::") as [CustomCategoryStatSource, string];
          return { source, name };
        });
      return {
        id: s.id,
        name: s.name.trim() || `Category ${i + 1}`,
        weight: normalizedWeights[i],
        stats,
      };
    });
  }, [subCats, assignments, normalizedWeights]);

  const validate = (): string | null => {
    const cats = buildPayloadCategories();
    const nonEmpty = cats.filter((c) => c.stats.length > 0);
    if (nonEmpty.length === 0) {
      return "Add at least one stat to a category before calculating.";
    }
    const totalWeight = nonEmpty.reduce((acc, c) => acc + c.weight, 0);
    if (totalWeight <= 0) {
      return "All sub-category weights are zero. Move at least one slider above zero.";
    }
    return null;
  };

  const handleCalculate = async () => {
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const cats = buildPayloadCategories().filter((c) => c.stats.length > 0);
      const data = await calculateRankings({
        position_group: selectedGroup,
        categories: cats,
        min_games: minGames,
        position:
          selectedGroup === "DEF" && positionFilter !== "All" ? positionFilter : undefined,
      });
      setPlayers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to calculate rankings.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: { title: string; share_mode: ShareMode }) => {
    const v = validate();
    if (v) {
      setError(v);
      throw new Error(v);
    }
    const cats = buildPayloadCategories().filter((c) => c.stats.length > 0);
    const payload: SaveRankingPayload = {
      title: values.title,
      share_mode: values.share_mode,
      position_group: selectedGroup,
      categories: cats,
      min_games: minGames,
      position_filter:
        selectedGroup === "DEF" && positionFilter !== "All" ? positionFilter : undefined,
    };
    try {
      const saved = await createSavedRanking(payload);
      setSaveModalOpen(false);
      if (saved.share_slug) {
        const origin = typeof window !== "undefined" ? window.location.origin : API_BASE_URL;
        setSaveMessage({
          kind: "ok",
          text: "Saved — share URL:",
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
  };

  const resultCategoryColumns = useMemo(
    () =>
      buildPayloadCategories()
        .filter((c) => c.stats.length > 0)
        .map((c) => ({ id: c.id, name: c.name })),
    [buildPayloadCategories]
  );

  // Stat groups for the player profile panel — keyed by user-defined sub-category.
  // Each sub-cat's `statKeys` are the un-namespaced stat names (the player's
  // `stats` dict uses un-namespaced names, see process_custom_category_rankings).
  const statGroups = useMemo<CategoryStatGroup[]>(
    () =>
      subCats
        .map((s) => ({
          id: s.id,
          name: s.name,
          statKeys: Object.entries(assignments)
            .filter(([, subId]) => subId === s.id)
            .map(([key]) => key.split("::")[1]),
        }))
        .filter((g) => g.statKeys.length > 0),
    [subCats, assignments]
  );

  // Radar axes — same source, names mirror the user's category names so the
  // chart and the section headers are labelled identically.
  const radarCategories = useMemo<CategoryInfo[]>(
    () =>
      subCats
        .filter((s) =>
          Object.values(assignments).includes(s.id)
        )
        .map((s) => ({ id: s.id, name: s.name })),
    [subCats, assignments]
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Link
          href="/dashboard"
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          &larr; Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold text-slate-900 mt-2">
          Build your own categories
        </h1>
        <p className="text-slate-600 mt-2">
          Pick stats from the grid below, drop them into up to {MAX_SUBCATEGORIES}{" "}
          sub-categories, and tune the weights.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Position Group
            </label>
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              className="block w-48 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            >
              {POSITION_GROUPS.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Min Games
            </label>
            <input
              type="number"
              min={1}
              max={17}
              value={minGames}
              onChange={(e) =>
                setMinGames(Math.min(parseInt(e.target.value) || 1, 17))
              }
              className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            />
          </div>

          {subPositions && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Position
              </label>
              <select
                value={positionFilter}
                onChange={(e) => setPositionFilter(e.target.value)}
                className="block w-36 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
              >
                {subPositions.map((pos) => (
                  <option key={pos} value={pos}>
                    {pos === "All" ? "All Positions" : pos}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
        {/* Sub-categories editor */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Sub-categories</h2>
            <button
              onClick={addSubCategory}
              disabled={subCats.length >= MAX_SUBCATEGORIES}
              className="text-sm px-3 py-1.5 rounded-md border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              + Add ({subCats.length}/{MAX_SUBCATEGORIES})
            </button>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Click a sub-category to make it the target. Then click stats from
            the grid to assign them.
          </p>

          <div className="space-y-3">
            {subCats.map((s, i) => {
              const isActive = s.id === activeSubCatId;
              const color = SUBCAT_COLORS[i % SUBCAT_COLORS.length];
              const pct = (normalizedWeights[i] * 100).toFixed(0);
              const stats = Object.entries(assignments)
                .filter(([, subId]) => subId === s.id)
                .map(([key]) => key);
              return (
                <div
                  key={s.id}
                  className={`rounded-lg border p-3 transition ${
                    isActive
                      ? `${color.bg} ring-2 ${color.ring} border-transparent`
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setActiveSubCatId(s.id)}
                      className={`w-3 h-3 rounded-full ${color.chip} flex-shrink-0`}
                      aria-label="Make active"
                    />
                    <input
                      type="text"
                      value={s.name}
                      onChange={(e) => renameSubCat(s.id, e.target.value)}
                      onFocus={() => setActiveSubCatId(s.id)}
                      className="flex-1 bg-transparent text-sm font-medium text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1 py-0.5"
                    />
                    <span className="text-xs font-mono text-slate-600 w-10 text-right">
                      {pct}%
                    </span>
                    <button
                      onClick={() => removeSubCategory(s.id)}
                      disabled={subCats.length <= 1}
                      className="text-slate-400 hover:text-red-600 text-sm px-1 disabled:opacity-30 disabled:cursor-not-allowed"
                      title={subCats.length <= 1 ? "At least one sub-category required" : "Remove"}
                    >
                      ✕
                    </button>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={s.weight}
                    onChange={(e) => updateSubCatWeight(s.id, parseFloat(e.target.value))}
                    className="w-full mt-2 h-2 accent-blue-600"
                  />
                  <div className="flex flex-wrap gap-1 mt-2 min-h-[1.5rem]">
                    {stats.length === 0 ? (
                      <span className="text-xs text-slate-400 italic">
                        No stats assigned yet
                      </span>
                    ) : (
                      stats.map((key) => {
                        const [, statName] = key.split("::");
                        const display =
                          available?.sources
                            .flatMap((src) => src.stats)
                            .find((st) => `${st.source}::${st.name}` === key)
                            ?.display_name ?? statName;
                        return (
                          <span
                            key={key}
                            className={`inline-flex items-center gap-1 text-xs ${color.bg} ${color.text} rounded-full px-2 py-0.5`}
                          >
                            {display}
                            <button
                              onClick={() => removeAssignment(key)}
                              className="hover:text-red-700"
                              aria-label={`Remove ${display}`}
                            >
                              ×
                            </button>
                          </span>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Stat bubble grid */}
        <div className="lg:col-span-3 bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Available stats</h2>
            <div className="text-xs text-slate-500">
              {totalAssignedStats} stat{totalAssignedStats === 1 ? "" : "s"} assigned
            </div>
          </div>

          {availableLoading ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              Loading stats…
            </div>
          ) : !available ? (
            <div className="text-sm text-slate-500">No stats available.</div>
          ) : (
            <div className="space-y-5">
              {available.sources.map((src) => (
                <div key={src.source}>
                  <div className="text-xs font-semibold tracking-wide uppercase text-slate-500 mb-2">
                    {src.label}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {src.stats.map((stat) => {
                      const key = `${stat.source}::${stat.name}`;
                      const assignedTo = assignments[key];
                      const color = assignedTo ? subCatColor(assignedTo) : null;
                      return (
                        <button
                          key={key}
                          onClick={() => toggleStat(stat)}
                          disabled={!activeSubCatId}
                          title={
                            assignedTo
                              ? `Assigned to ${
                                  subCats.find((s) => s.id === assignedTo)?.name ?? "—"
                                }`
                              : `Click to add to active sub-category`
                          }
                          className={`group relative inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition ${
                            color
                              ? `${color.bg} ${color.text} border-transparent`
                              : "bg-white text-slate-700 border-slate-300 hover:border-blue-400 hover:bg-blue-50"
                          } disabled:opacity-40 disabled:cursor-not-allowed`}
                        >
                          {color && (
                            <span
                              className={`w-2 h-2 rounded-full ${color.chip}`}
                            />
                          )}
                          {stat.display_name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <button
            onClick={handleCalculate}
            disabled={loading || totalAssignedStats === 0}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Calculating…" : "Calculate Rankings"}
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
            className="px-6 py-2 text-sm font-medium text-white bg-emerald-600 rounded-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save
          </button>
          {!user && (
            <Link
              href="/sign-in"
              className="text-sm text-blue-600 hover:text-blue-800 underline"
            >
              Sign in to save
            </Link>
          )}
        </div>
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
            <a
              href={saveMessage.url}
              className="underline break-all block mt-1"
            >
              {saveMessage.url}
            </a>
          )}
        </div>
      )}

      {selectedPlayers.length > 0 && !isMobile && (
        <div className="sticky top-0 z-10 mb-6">
          <PlayerProfilePanel
            players={selectedPlayers}
            categories={radarCategories}
            ranks={selectedPlayers.map((p) => statRanks.get(p.id) || {})}
            totalPlayers={players.length}
            onClose={() => setSelectedPlayerIds([])}
            statGroups={statGroups}
          />
        </div>
      )}
      {selectedPlayers.length > 0 && isMobile && (
        <MobileProfileSheet
          players={selectedPlayers}
          categories={radarCategories}
          ranks={selectedPlayers.map((p) => statRanks.get(p.id) || {})}
          totalPlayers={players.length}
          onClose={() => setSelectedPlayerIds([])}
          statGroups={statGroups}
        />
      )}

      {players.length > 0 && (
        <RankingsResultsTable
          players={players}
          categories={resultCategoryColumns}
          exportFilenameBase={`custom_${selectedGroup}_builder`}
          selectedPlayerIds={selectedPlayerIds}
          onRowClick={handleRowClick}
        />
      )}

      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Calculating custom rankings…</p>
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
