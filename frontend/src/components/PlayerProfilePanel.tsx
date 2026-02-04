"use client";

import RadarChart from "./RadarChart";
import ProfileStatsTable from "./ProfileStatsTable";
import { CategoryInfo, PlayerDetail } from "@/lib/api";

interface PlayerProfilePanelProps {
  players: PlayerDetail[];
  categories: CategoryInfo[];
  ranks: Record<string, number>[];
  totalPlayers: number;
  onClose: () => void;
}

export default function PlayerProfilePanel({
  players,
  categories,
  ranks,
  totalPlayers,
  onClose,
}: PlayerProfilePanelProps) {
  const player1 = players[0];
  const player2 = players[1];
  const isComparing = players.length === 2;

  return (
    <div className="bg-white rounded-lg shadow-lg border border-slate-200 mb-6">
      {/* Header */}
      <div className="flex items-center justify-end px-4 py-2 border-b border-slate-200">
        <button
          onClick={onClose}
          className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
          aria-label="Close player profile"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Radar Chart */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">
              Category Scores
            </h3>
            <div className="bg-slate-50 rounded-lg p-4">
              <RadarChart
                categoryScores={player1.category_scores}
                categories={categories}
                playerName={player1.name}
                player2={
                  player2
                    ? {
                        scores: player2.category_scores,
                        name: player2.name,
                      }
                    : undefined
                }
              />
              <div className="text-center mt-2">
                <span className="text-2xl font-bold text-blue-600">
                  {player1.overall_score.toFixed(1)}
                </span>
                {isComparing && (
                  <>
                    <span className="text-slate-400 mx-2">vs</span>
                    <span className="text-2xl font-bold text-orange-600">
                      {player2.overall_score.toFixed(1)}
                    </span>
                  </>
                )}
                <span className="text-sm text-slate-500 ml-1">Overall</span>
              </div>
            </div>
          </div>

          {/* Stats Table */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">
              Detailed Stats
            </h3>
            <div className="bg-slate-50 rounded-lg p-4 max-h-[320px] overflow-y-auto">
              <ProfileStatsTable
                stats={player1.stats}
                ranks={ranks[0]}
                totalPlayers={totalPlayers}
                player1Name={player1.name}
                player2Name={player2?.name}
                player2Stats={player2?.stats}
                player2Ranks={ranks[1]}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
