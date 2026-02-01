"use client";

import { useState, useEffect } from "react";

interface Player {
  id: number;
  name: string;
  team: string;
  position: string;
  games_played: number;
  overall_score: number;
  run_defense_score: number;
  pass_rush_score: number;
  coverage_score: number;
  playmaking_score: number;
}

const positions = ["All", "DL", "EDGE", "LB", "CB", "S"];

export default function RankingsTable() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState("All");
  const [minGames, setMinGames] = useState(1);

  useEffect(() => {
    async function fetchRankings() {
      try {
        const params = new URLSearchParams();
        if (positionFilter !== "All") {
          params.append("position", positionFilter);
        }
        params.append("min_games", minGames.toString());

        const response = await fetch(
          `http://localhost:8000/api/rankings?${params.toString()}`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch rankings");
        }
        const data = await response.json();
        setPlayers(data);
        setError(null);
      } catch (err) {
        setError("Unable to load rankings. Make sure the backend is running.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchRankings();
  }, [positionFilter, minGames]);

  const formatScore = (score: number) => score.toFixed(1);

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-600 font-semibold";
    if (score >= 80) return "text-blue-600";
    if (score >= 70) return "text-slate-600";
    return "text-red-600";
  };

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Position
          </label>
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
            className="block w-40 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white px-3 py-2 border"
          >
            {positions.map((pos) => (
              <option key={pos} value={pos}>
                {pos === "All" ? "All Positions" : pos}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Min Games Played
          </label>
          <input
            type="number"
            min="1"
            max="17"
            value={minGames}
            onChange={(e) => setMinGames(parseInt(e.target.value) || 1)}
            className="block w-24 rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 bg-white px-3 py-2 border"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Loading rankings...</p>
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
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Player
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Team
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Pos
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    GP
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Overall
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Run Def
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Pass Rush
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Coverage
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Playmaking
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {players.map((player, index) => (
                  <tr key={player.id} className="hover:bg-slate-50">
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
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                        player.run_defense_score
                      )}`}
                    >
                      {formatScore(player.run_defense_score)}
                    </td>
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                        player.pass_rush_score
                      )}`}
                    >
                      {formatScore(player.pass_rush_score)}
                    </td>
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                        player.coverage_score
                      )}`}
                    >
                      {formatScore(player.coverage_score)}
                    </td>
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-center ${getScoreColor(
                        player.playmaking_score
                      )}`}
                    >
                      {formatScore(player.playmaking_score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {players.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No players found matching the criteria.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
