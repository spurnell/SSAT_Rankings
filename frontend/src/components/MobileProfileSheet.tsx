"use client";

import { useState } from "react";
import RadarChart from "./RadarChart";
import ProfileStatsTable from "./ProfileStatsTable";
import { CategoryInfo, PlayerDetail } from "@/lib/api";

interface MobileProfileSheetProps {
  players: PlayerDetail[];
  categories: CategoryInfo[];
  ranks: Record<string, number>[];
  totalPlayers: number;
  onClose: () => void;
}

export default function MobileProfileSheet({
  players,
  categories,
  ranks,
  totalPlayers,
  onClose,
}: MobileProfileSheetProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const player1 = players[0];
  const player2 = players[1];
  const isComparing = players.length === 2;

  return (
    <>
      {/* Backdrop when expanded */}
      {isExpanded && (
        <div
          className="fixed inset-0 bg-black/30 z-40"
          onClick={() => setIsExpanded(false)}
        />
      )}

      {/* Bottom Sheet */}
      <div
        className={`fixed bottom-0 left-0 right-0 bg-white rounded-t-2xl shadow-2xl z-50 transition-all duration-300 ease-out ${
          isExpanded ? "h-[75vh]" : "h-16"
        }`}
      >
        {/* Minimized Header Bar */}
        <div
          className="flex items-center justify-between px-4 h-16 cursor-pointer"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {/* Drag handle indicator */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 w-10 h-1 bg-slate-300 rounded-full" />

          {/* Player info */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-semibold text-slate-900 truncate">
                {player1.name}
              </span>
              <span className="text-blue-600 font-bold">
                {player1.overall_score.toFixed(1)}
              </span>
            </div>
            {isComparing && (
              <>
                <span className="text-slate-400">vs</span>
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-semibold text-slate-900 truncate">
                    {player2.name}
                  </span>
                  <span className="text-orange-600 font-bold">
                    {player2.overall_score.toFixed(1)}
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {/* Expand/collapse indicator */}
            <svg
              className={`w-5 h-5 text-slate-400 transition-transform ${
                isExpanded ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 15l7-7 7 7"
              />
            </svg>

            {/* Close button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
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
        </div>

        {/* Expanded Content */}
        {isExpanded && (
          <div className="px-4 pb-6 overflow-y-auto h-[calc(75vh-4rem)]">
            {/* Radar Chart */}
            <div className="mb-6">
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
              <div className="bg-slate-50 rounded-lg p-4">
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
        )}
      </div>
    </>
  );
}
