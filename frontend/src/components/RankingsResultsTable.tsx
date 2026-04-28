"use client";

import { useMemo, useState } from "react";

type SortDir = "asc" | "desc";
type SortKey = string;

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

function getScoreColor(score: number) {
  if (score >= 90) return "text-green-600 font-semibold";
  if (score >= 80) return "text-blue-600";
  if (score >= 70) return "text-slate-600";
  return "text-red-600";
}

const formatScore = (s: number) => s.toFixed(1);

export interface RankingsResultsPlayer {
  id: number;
  name: string;
  team: string;
  position: string;
  games_played: number;
  overall_score: number;
  category_scores: Record<string, number>;
}

export interface RankingsCategoryColumn {
  id: string;
  name: string;
}

interface Props {
  players: RankingsResultsPlayer[];
  categories: RankingsCategoryColumn[];
  exportFilenameBase?: string;
  /** Selected ids for the click-to-open profile panel pattern. First id gets blue ring, second orange. */
  selectedPlayerIds?: number[];
  /** When set, rows become clickable and trigger this callback. */
  onRowClick?: (playerId: number) => void;
}

export default function RankingsResultsTable({
  players,
  categories,
  exportFilenameBase = "rankings",
  selectedPlayerIds,
  onRowClick,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: SortDir } | null>(null);

  function handleSort(key: SortKey) {
    setSortConfig((current) => {
      if (current?.key === key) {
        return current.direction === "desc" ? { key, direction: "asc" } : null;
      }
      return { key, direction: "desc" };
    });
  }

  const getSortIndicator = (key: SortKey) => {
    if (sortConfig?.key !== key) return null;
    return sortConfig.direction === "asc" ? " ↑" : " ↓";
  };

  const filteredAndSorted = useMemo(() => {
    let result = players;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((p) => p.name.toLowerCase().includes(q));
    }
    if (!sortConfig) return result;

    return [...result].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;
      switch (sortConfig.key) {
        case "name":
          aVal = a.name; bVal = b.name; break;
        case "team":
          aVal = a.team; bVal = b.team; break;
        case "position":
          aVal = a.position; bVal = b.position; break;
        case "games_played":
          aVal = a.games_played; bVal = b.games_played; break;
        case "overall_score":
          aVal = a.overall_score; bVal = b.overall_score; break;
        default:
          aVal = a.category_scores[sortConfig.key] || 0;
          bVal = b.category_scores[sortConfig.key] || 0;
      }
      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
  }, [players, searchQuery, sortConfig]);

  function exportCSV() {
    if (players.length === 0) return;
    const headers = ["Rank", "Player", "Team", "Pos", "GP", "Overall", ...categories.map((c) => c.name)];
    const rows = filteredAndSorted.map((p, i) => [
      i + 1,
      p.name,
      p.team,
      p.position,
      p.games_played,
      p.overall_score.toFixed(1),
      ...categories.map((c) => (p.category_scores[c.id] || 0).toFixed(1)),
    ]);
    const csv = [
      headers.join(","),
      ...rows.map((r) => r.map((v) => (typeof v === "string" && v.includes(",") ? `"${v}"` : v)).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${exportFilenameBase}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
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
          {filteredAndSorted.length} players
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Rank</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("name")}>
                Player{getSortIndicator("name")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("team")}>
                Team{getSortIndicator("team")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("position")}>
                Pos{getSortIndicator("position")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("games_played")}>
                GP{getSortIndicator("games_played")}
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("overall_score")}>
                Overall{getSortIndicator("overall_score")}
              </th>
              {categories.map((cat) => (
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
            {filteredAndSorted.map((player, index) => {
              const isFirstSelected = selectedPlayerIds?.[0] === player.id;
              const isSecondSelected = selectedPlayerIds?.[1] === player.id;
              const rowClasses = [
                "hover:bg-slate-50 transition-colors",
                onRowClick ? "cursor-pointer" : "",
                isFirstSelected ? "bg-blue-50 ring-2 ring-blue-500 ring-inset" : "",
                isSecondSelected ? "bg-orange-50 ring-2 ring-orange-500 ring-inset" : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
              <tr
                key={player.id}
                className={rowClasses}
                onClick={onRowClick ? () => onRowClick(player.id) : undefined}
              >
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900">{index + 1}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900">{player.name}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{player.team}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{player.position}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{player.games_played}</td>
                <td className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(player.overall_score)}`}>
                  {formatScore(player.overall_score)}
                </td>
                {categories.map((cat) => (
                  <td
                    key={cat.id}
                    className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(player.category_scores[cat.id] || 0)}`}
                  >
                    {formatScore(player.category_scores[cat.id] || 0)}
                  </td>
                ))}
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filteredAndSorted.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          No players found matching the criteria.
        </div>
      )}
    </div>
  );
}
