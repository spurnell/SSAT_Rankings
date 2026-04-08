"use client";

import { useState, useEffect, useMemo } from "react";
import PlayerProfilePanel from "./PlayerProfilePanel";
import MobileProfileSheet from "./MobileProfileSheet";
import CategoryStatsTooltip from "./CategoryStatsTooltip";
import { fetchRankings, fetchCareerRankings, fetchPositionGroups, fetchAvailableSeasons, PositionGroup, PlayerDetail, CategoryInfo } from "@/lib/api";
import { LOWER_IS_BETTER_STATS } from "@/lib/statLabels";

type SortKey = string;

const CAREER_POSITION_GROUPS = ["DEF", "QB", "RB", "WR", "TE", "K"];
const PFF_AVAILABLE_SEASON = 2025;

function calculateStatRanks(players: PlayerDetail[]): Map<number, Record<string, number>> {
  if (players.length === 0) return new Map();

  // Get all stat keys from first player
  const statKeys = Object.keys(players[0]?.stats || {});
  const rankMap = new Map<number, Record<string, number>>();

  for (const stat of statKeys) {
    const lowerIsBetter = LOWER_IS_BETTER_STATS.has(stat);
    const sorted = [...players].sort((a, b) => {
      const av = a.stats[stat] || 0;
      const bv = b.stats[stat] || 0;
      return lowerIsBetter ? av - bv : bv - av;
    });
    sorted.forEach((player, index) => {
      if (!rankMap.has(player.id)) rankMap.set(player.id, {});
      rankMap.get(player.id)![stat] = index + 1;
    });
  }
  return rankMap;
}

interface RankingsTableProps {
  mode?: "season" | "career";
}

export default function RankingsTable({ mode = "season" }: RankingsTableProps) {
  const isCareer = mode === "career";

  const [players, setPlayers] = useState<PlayerDetail[]>([]);
  const [positionGroups, setPositionGroups] = useState<PositionGroup[]>([]);
  const [selectedPositionGroup, setSelectedPositionGroup] = useState<string>(isCareer ? "QB" : "RB");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState("All");
  const [teamFilter, setTeamFilter] = useState("All");
  const [minGames, setMinGames] = useState(1);
  const [selectedPlayerIds, setSelectedPlayerIds] = useState<number[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [availableSeasons, setAvailableSeasons] = useState<number[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [sortConfig, setSortConfig] = useState<{
    key: SortKey;
    direction: "asc" | "desc";
  } | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  // Data source toggle (standard vs PFF variants)
  const [dataSource, setDataSource] = useState<string>("standard");

  // Category header hover state for stat-breakdown tooltip
  const [hoveredCategoryId, setHoveredCategoryId] = useState<string | null>(null);

  // Career-specific state
  const [careerMode, setCareerMode] = useState<"cumulative" | "per_game">("cumulative");
  const [minSeasons, setMinSeasons] = useState(3);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Get current position group config
  const currentGroup = useMemo(() => {
    return positionGroups.find(g => g.id === selectedPositionGroup);
  }, [positionGroups, selectedPositionGroup]);

  const currentCategories = useMemo(() => {
    if (dataSource === "pff" && currentGroup?.pff_categories) {
      return currentGroup.pff_categories;
    }
    if (dataSource === "pff_front7" && currentGroup?.pff_front7_categories) {
      return currentGroup.pff_front7_categories;
    }
    if (dataSource === "pff_secondary" && currentGroup?.pff_secondary_categories) {
      return currentGroup.pff_secondary_categories;
    }
    return currentGroup?.categories || [];
  }, [currentGroup, dataSource, selectedPositionGroup]);

  // Effective sub-positions based on data source (DEF PFF splits filter positions)
  const effectiveSubPositions = useMemo(() => {
    if (dataSource === "pff_front7") return ["All", "DL", "EDGE", "LB"];
    if (dataSource === "pff_secondary") return ["All", "CB", "S"];
    return currentGroup?.sub_positions || [];
  }, [currentGroup, dataSource]);

  // PFF data is only available for the 2025 season
  const pffAvailable = selectedSeason === null || selectedSeason === PFF_AVAILABLE_SEASON;

  // Fetch position groups on mount
  useEffect(() => {
    async function loadPositionGroups() {
      try {
        const groups = await fetchPositionGroups();
        if (isCareer) {
          setPositionGroups(groups.filter((g) => CAREER_POSITION_GROUPS.includes(g.id)));
        } else {
          setPositionGroups(groups);
        }
      } catch (err) {
        console.error("Failed to load position groups:", err);
        if (!isCareer) {
          // Fallback to DEF only
          setPositionGroups([{
            id: "DEF",
            name: "Defensive Players",
            categories: [
              { id: "run_defense", name: "Run Defense" },
              { id: "pass_rush", name: "Pass Rush" },
              { id: "coverage", name: "Coverage" },
              { id: "playmaking", name: "Playmaking" },
            ]
          }]);
        }
      }
    }
    loadPositionGroups();
  }, [isCareer]);

  // Fetch available seasons on mount (season mode only)
  useEffect(() => {
    if (isCareer) return;
    async function loadSeasons() {
      try {
        const seasons = await fetchAvailableSeasons();
        setAvailableSeasons(seasons);
        if (seasons.length > 0 && selectedSeason === null) {
          setSelectedSeason(seasons[0]); // Most recent season (descending)
        }
      } catch (err) {
        console.error("Failed to load available seasons:", err);
      }
    }
    loadSeasons();
  }, [isCareer]);

  // Fetch rankings when filters change
  useEffect(() => {
    async function loadRankings() {
      setLoading(true);
      try {
        let data: PlayerDetail[];
        if (isCareer) {
          data = await fetchCareerRankings({
            position_group: selectedPositionGroup,
            mode: careerMode,
            min_seasons: minSeasons,
            min_games: minGames,
          });
        } else {
          data = await fetchRankings({
            position_group: selectedPositionGroup,
            position: positionFilter !== "All" ? positionFilter : undefined,
            min_games: minGames,
            season: selectedSeason || undefined,
            source: dataSource !== "standard" ? dataSource : undefined,
          });
        }
        setPlayers(data);
        setError(null);
        // Reset selection when filters change
        setSelectedPlayerIds([]);
      } catch (err) {
        setError(
          isCareer
            ? "Unable to load career rankings. Make sure the backend is running."
            : "Unable to load rankings. Make sure the backend is running."
        );
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadRankings();
  }, [selectedPositionGroup, positionFilter, minGames, isCareer, careerMode, minSeasons, selectedSeason, dataSource]);

  // Reset position filter and data source when position group changes
  useEffect(() => {
    setPositionFilter("All");
    setDataSource("standard");
  }, [selectedPositionGroup]);

  // Auto-revert to standard if user picks a non-2025 season while a PFF source is active
  useEffect(() => {
    if (!pffAvailable && dataSource !== "standard") {
      setDataSource("standard");
    }
  }, [pffAvailable, dataSource]);

  // Reset position filter when data source changes (e.g. switching front7 <-> secondary)
  useEffect(() => {
    setPositionFilter("All");
  }, [dataSource]);

  // Auto-select top 2 players on initial load
  useEffect(() => {
    if (players.length >= 2 && selectedPlayerIds.length === 0) {
      setSelectedPlayerIds([players[0].id, players[1].id]);
    }
  }, [players, selectedPlayerIds.length]);

  const formatScore = (score: number) => score.toFixed(1);

  const teams = useMemo(() => {
    const uniqueTeams = Array.from(new Set(players.map((p) => p.team))).sort();
    return ["All", ...uniqueTeams];
  }, [players]);

  const statRanks = useMemo(() => calculateStatRanks(players), [players]);

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

  const filteredAndSortedPlayers = useMemo(() => {
    let result = players;

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter((p) => p.name.toLowerCase().includes(query));
    }

    if (teamFilter !== "All") {
      result = result.filter((p) => p.team === teamFilter);
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
        // Category score
        aVal = a.category_scores[sortConfig.key] || 0;
        bVal = b.category_scores[sortConfig.key] || 0;
      }

      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
  }, [players, searchQuery, teamFilter, sortConfig]);

  const selectedPlayers = useMemo(() => {
    return selectedPlayerIds
      .map((id) => players.find((p) => p.id === id))
      .filter((p): p is PlayerDetail => p !== undefined);
  }, [players, selectedPlayerIds]);

  const handleRowClick = (playerId: number) => {
    setSelectedPlayerIds((current) => {
      if (current.includes(playerId)) {
        return current.filter((id) => id !== playerId);
      } else if (current.length < 2) {
        return [...current, playerId];
      } else {
        return [current[0], playerId];
      }
    });
  };

  const getSortIndicator = (key: SortKey) => {
    if (sortConfig?.key !== key) return null;
    return sortConfig.direction === "asc" ? " ↑" : " ↓";
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-600 font-semibold";
    if (score >= 80) return "text-blue-600";
    if (score >= 70) return "text-slate-600";
    return "text-red-600";
  };

  // Short category names for table headers
  const getCategoryShortName = (cat: CategoryInfo): string => {
    const shortNames: Record<string, string> = {
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
      // QB PFF
      pff_accuracy: "Accuracy",
      pff_decision_making: "Decisions",
      pff_pocket_presence: "Pocket",
      pff_playmaking: "Playmaking",
      // RB PFF
      pff_rushing_efficiency: "Rush Eff",
      pff_explosiveness: "Explosive",
      pff_volume_production: "Volume",
      pff_ball_security: "Ball Sec",
      pff_rb_receiving: "Receiving",
      // WR PFF
      pff_route_running: "Routes",
      pff_hands_catching: "Hands",
      pff_wr_playmaking: "Playmaking",
      pff_wr_production: "Production",
      // TE PFF
      pff_te_receiving: "Receiving",
      pff_te_route_running: "Routes",
      pff_contested_catching: "Contested",
      pff_blocking: "Blocking",
      pff_te_playmaking: "Playmaking",
      // DEF PFF Front 7
      pff_pass_rush: "Pass Rush",
      pff_run_defense: "Run Def",
      pff_tackling: "Tackling",
      pff_f7_playmaking: "Playmaking",
      // DEF PFF Secondary
      pff_sec_coverage: "Coverage",
      pff_sec_tackling: "Tackling",
      pff_sec_playmaking: "Playmaking",
      pff_ball_hawking: "Ball Hawk",
      // K PFF
      pff_k_accuracy: "Accuracy",
      pff_range_power: "Range",
      pff_k_volume: "Volume",
      pff_kickoffs: "Kickoffs",
    };
    return shortNames[cat.id] || cat.name;
  };

  return (
    <div>
      {/* Player Profile Panel - Desktop */}
      {selectedPlayers.length > 0 && !isMobile && (
        <div className="sticky top-0 z-10">
          <PlayerProfilePanel
            players={selectedPlayers}
            categories={currentCategories}
            ranks={selectedPlayers.map((p) => statRanks.get(p.id) || {})}
            totalPlayers={players.length}
            onClose={() => setSelectedPlayerIds([])}
          />
        </div>
      )}

      {/* Player Profile Sheet - Mobile */}
      {selectedPlayers.length > 0 && isMobile && (
        <MobileProfileSheet
          players={selectedPlayers}
          categories={currentCategories}
          ranks={selectedPlayers.map((p) => statRanks.get(p.id) || {})}
          totalPlayers={players.length}
          onClose={() => setSelectedPlayerIds([])}
        />
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        {/* Player Search */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Search Player
          </label>
          <input
            type="text"
            placeholder="Search by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-48 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
          />
        </div>

        {/* Position Group Selector */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Position Group
          </label>
          <select
            value={selectedPositionGroup}
            onChange={(e) => setSelectedPositionGroup(e.target.value)}
            className="block w-40 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
          >
            {positionGroups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </div>

        {/* Season Selector (season mode only) */}
        {!isCareer && availableSeasons.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Season
            </label>
            <select
              value={selectedSeason || ""}
              onChange={(e) => setSelectedSeason(Number(e.target.value))}
              className="block w-32 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            >
              {availableSeasons.map((season) => (
                <option key={season} value={season}>
                  {season}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Data Source Toggle */}
        {!isCareer && currentGroup?.available_sources && currentGroup.available_sources.length > 1 && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Data Source
            </label>
            <div className="flex rounded-md overflow-hidden border border-slate-300">
              {currentGroup.available_sources.map((src, idx) => {
                const labels: Record<string, string> = {
                  standard: "Standard",
                  pff: "PFF",
                  pff_front7: "PFF Front 7",
                  pff_secondary: "PFF Secondary",
                };
                const isDisabled = !pffAvailable && src !== "standard";
                return (
                  <button
                    key={src}
                    onClick={() => setDataSource(src)}
                    disabled={isDisabled}
                    title={isDisabled ? `PFF data only available for ${PFF_AVAILABLE_SEASON}` : undefined}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      idx > 0 ? "border-l border-slate-300" : ""
                    } ${
                      dataSource === src
                        ? "bg-blue-600 text-white"
                        : "bg-white text-slate-700 hover:bg-slate-50"
                    } disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-white`}
                  >
                    {labels[src] || src}
                  </button>
                );
              })}
            </div>
            {!pffAvailable && (
              <p className="mt-1 text-xs text-slate-500">
                PFF data only available for {PFF_AVAILABLE_SEASON}
              </p>
            )}
          </div>
        )}

        {/* Sub-position filter (only for season mode with groups that have sub_positions) */}
        {!isCareer && effectiveSubPositions.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Position
            </label>
            <select
              value={positionFilter}
              onChange={(e) => setPositionFilter(e.target.value)}
              className="block w-40 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            >
              {effectiveSubPositions.map((pos) => (
                <option key={pos} value={pos}>
                  {pos === "All" ? "All Positions" : pos}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Career mode toggle */}
        {isCareer && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Mode
            </label>
            <div className="flex rounded-md overflow-hidden border border-slate-300">
              <button
                onClick={() => setCareerMode("cumulative")}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  careerMode === "cumulative"
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                Cumulative
              </button>
              <button
                onClick={() => setCareerMode("per_game")}
                className={`px-4 py-2 text-sm font-medium transition-colors border-l border-slate-300 ${
                  careerMode === "per_game"
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                Per Game
              </button>
            </div>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Team
          </label>
          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="block w-40 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
          >
            {teams.map((team) => (
              <option key={team} value={team}>
                {team === "All" ? "All Teams" : team}
              </option>
            ))}
          </select>
        </div>

        {/* Min Seasons (career only) */}
        {isCareer && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Min Seasons
            </label>
            <input
              type="number"
              min="1"
              max="25"
              value={minSeasons}
              onChange={(e) => setMinSeasons(parseInt(e.target.value) || 1)}
              className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Min Games{isCareer ? "" : " Played"}
          </label>
          <input
            type="number"
            min="1"
            max={isCareer ? 400 : 17}
            value={minGames}
            onChange={(e) => setMinGames(parseInt(e.target.value) || 1)}
            className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white text-slate-900 px-3 py-2 border"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">
            {isCareer ? "Loading career rankings... (first load may take a moment)" : "Loading rankings..."}
          </p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-600">{error}</p>
          <p className="text-sm text-red-500 mt-2">
            Run: cd backend && uvicorn app.main:app --reload
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
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
                  {!isCareer && (
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                      onClick={() => handleSort("position")}
                    >
                      Pos{getSortIndicator("position")}
                    </th>
                  )}
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
                  {/* Dynamic category columns */}
                  {currentCategories.map((cat) => (
                    <th
                      key={cat.id}
                      className="relative px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
                      onClick={() => handleSort(cat.id)}
                      onMouseEnter={() => setHoveredCategoryId(cat.id)}
                      onMouseLeave={() => setHoveredCategoryId(null)}
                    >
                      {getCategoryShortName(cat)}{getSortIndicator(cat.id)}
                      {hoveredCategoryId === cat.id && (
                        <CategoryStatsTooltip
                          category={cat}
                          className="absolute left-1/2 top-full mt-1 -translate-x-1/2 normal-case tracking-normal"
                        />
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {filteredAndSortedPlayers.map((player, index) => (
                  <tr
                    key={player.id}
                    className={`hover:bg-slate-50 relative cursor-pointer transition-colors ${
                      selectedPlayerIds[0] === player.id
                        ? "bg-blue-50 ring-2 ring-blue-500 ring-inset"
                        : selectedPlayerIds[1] === player.id
                        ? "bg-orange-50 ring-2 ring-orange-500 ring-inset"
                        : ""
                    }`}
                    onClick={() => handleRowClick(player.id)}
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
                    {!isCareer && (
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                        {player.position}
                      </td>
                    )}
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
                    {/* Dynamic category scores */}
                    {currentCategories.map((cat) => (
                      <td
                        key={cat.id}
                        className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                          player.category_scores[cat.id] || 80
                        )}`}
                      >
                        {formatScore(player.category_scores[cat.id] || 80)}
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
    </div>
  );
}
