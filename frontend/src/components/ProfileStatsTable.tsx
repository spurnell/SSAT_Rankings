"use client";

import { getRankColorWithStyle } from "@/lib/colorUtils";

interface ProfileStatsTableProps {
  stats: Record<string, number>;
  ranks: Record<string, number>;
  totalPlayers: number;
  player1Name?: string;
  player2Name?: string;
  player2Stats?: Record<string, number>;
  player2Ranks?: Record<string, number>;
}

// Stat display names for all position groups
const STAT_LABELS: Record<string, string> = {
  // Defensive
  tackles: "Tackles",
  solo_tackles: "Solo Tackles",
  assists: "Assists",
  sacks: "Sacks",
  qb_hits: "QB Hits",
  tackles_for_loss: "TFL",
  passes_defended: "Passes Defended",
  interceptions: "Interceptions",
  forced_fumbles: "Forced Fumbles",
  fumble_recoveries: "Fumble Recoveries",
  defensive_tds: "Defensive TDs",
  // QB
  pass_attempts: "Pass Attempts",
  completions: "Completions",
  completion_pct: "Completion %",
  pass_yards: "Pass Yards",
  pass_tds: "Pass TDs",
  passer_rating: "Passer Rating",
  yards_per_attempt: "Yards/Attempt",
  first_downs: "First Downs",
  int_rate_inv: "INT Rate (inv)",
  sack_rate_inv: "Sack Rate (inv)",
  fumbles_inv: "Fumbles (inv)",
  // RB
  rush_attempts: "Rush Attempts",
  rush_yards: "Rush Yards",
  yards_per_carry: "Yards/Carry",
  rush_tds: "Rush TDs",
  longest_rush: "Longest Rush",
  fumbles: "Fumbles",
  receptions: "Receptions",
  rec_yards: "Rec Yards",
  rec_tds: "Rec TDs",
  targets: "Targets",
  touches: "Touches",
  yards_per_touch: "Yards/Touch",
  total_tds: "Total TDs",
  success_rate: "Success Rate",
  // WR/TE
  catch_rate: "Catch Rate",
  yards_per_reception: "Yards/Rec",
  yards_per_target: "Yards/Target",
  longest_rec: "Longest Rec",
  yards_after_catch: "YAC",
  // Kicker
  fg_made: "FG Made",
  fg_attempts: "FG Attempts",
  fg_pct: "FG %",
  fg_made_40_49: "FG 40-49",
  fg_made_50_plus: "FG 50+",
  long_fg: "Long FG",
  xp_made: "XP Made",
  xp_attempts: "XP Attempts",
  xp_pct: "XP %",
  total_points: "Total Points",
};

// Stats to hide (internal calculations)
const HIDDEN_STATS = new Set([
  "int_rate_inv",
  "sack_rate_inv",
  "fumbles_inv",
  "games_played",
]);

function getStatLabel(key: string): string {
  return STAT_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

export default function ProfileStatsTable({
  stats,
  ranks,
  totalPlayers,
  player1Name,
  player2Name,
  player2Stats,
  player2Ranks,
}: ProfileStatsTableProps) {
  const statKeys = Object.keys(stats).filter(k => !HIDDEN_STATS.has(k));
  const isComparing = player2Stats && player2Ranks;

  const formatValue = (value: number) => {
    if (typeof value !== "number") return value;
    if (Number.isInteger(value)) return value;
    return value.toFixed(1);
  };

  return (
    <div className="overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 px-2 font-medium text-slate-600">
              Stat
            </th>
            {isComparing ? (
              <>
                <th className="text-right py-2 px-1 font-medium text-blue-600">
                  {player1Name || "P1"}
                </th>
                <th className="text-right py-2 px-1 font-medium text-blue-600">
                  Rank
                </th>
                <th className="text-right py-2 px-1 font-medium text-orange-600">
                  {player2Name || "P2"}
                </th>
                <th className="text-right py-2 px-1 font-medium text-orange-600">
                  Rank
                </th>
              </>
            ) : (
              <>
                <th className="text-right py-2 px-2 font-medium text-slate-600">
                  Value
                </th>
                <th className="text-right py-2 px-2 font-medium text-slate-600">
                  Rank
                </th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {statKeys.map((key) => {
            const value = stats[key] || 0;
            const rank = ranks[key] || totalPlayers;
            const colorResult = getRankColorWithStyle(rank, totalPlayers);

            const value2 = player2Stats?.[key] || 0;
            const rank2 = player2Ranks?.[key] || totalPlayers;
            const colorResult2 = player2Ranks ? getRankColorWithStyle(rank2, totalPlayers) : null;

            // Highlight the better rank when comparing
            const p1Better = isComparing && rank < rank2;
            const p2Better = isComparing && rank2 < rank;

            return (
              <tr key={key} className="border-b border-slate-100 last:border-0">
                <td className="py-1.5 px-2 text-slate-700">
                  {getStatLabel(key)}
                </td>
                {isComparing ? (
                  <>
                    <td className="py-1.5 px-1 text-right font-medium text-slate-900">
                      {formatValue(value)}
                    </td>
                    <td className="py-1.5 px-1 text-right">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${p1Better ? "ring-1 ring-blue-400" : ""}`}
                        style={colorResult.style}
                      >
                        #{rank}
                      </span>
                    </td>
                    <td className="py-1.5 px-1 text-right font-medium text-slate-900">
                      {formatValue(value2)}
                    </td>
                    <td className="py-1.5 px-1 text-right">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${p2Better ? "ring-1 ring-orange-400" : ""}`}
                        style={colorResult2?.style}
                      >
                        #{rank2}
                      </span>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="py-1.5 px-2 text-right font-medium text-slate-900">
                      {formatValue(value)}
                    </td>
                    <td className="py-1.5 px-2 text-right">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                        style={colorResult.style}
                      >
                        #{rank}
                      </span>
                    </td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
