"use client";

import { Fragment } from "react";
import { CategoryStatGroup } from "@/lib/api";
import { getRankColorWithStyle } from "@/lib/colorUtils";
import { getStatLabel, HIDDEN_STATS } from "@/lib/statLabels";

interface ProfileStatsTableProps {
  stats: Record<string, number>;
  ranks: Record<string, number>;
  totalPlayers: number;
  player1Name?: string;
  player2Name?: string;
  player2Stats?: Record<string, number>;
  player2Ranks?: Record<string, number>;
  /**
   * When provided, stats are rendered under section headers — one per group.
   * Stats that don't appear in any group fall under an "Other" section so
   * nothing in `stats` is silently dropped. A stat that belongs to multiple
   * groups appears under each (this is the point — showing membership).
   */
  groups?: CategoryStatGroup[];
}

export default function ProfileStatsTable({
  stats,
  ranks,
  totalPlayers,
  player1Name,
  player2Name,
  player2Stats,
  player2Ranks,
  groups,
}: ProfileStatsTableProps) {
  const isComparing = player2Stats && player2Ranks;
  const colSpan = isComparing ? 5 : 3;

  const formatValue = (value: number) => {
    if (typeof value !== "number") return value;
    if (Number.isInteger(value)) return value;
    return value.toFixed(1);
  };

  const visibleStatKeys = Object.keys(stats).filter((k) => !HIDDEN_STATS.has(k));

  // Build the grouped rendering plan: a list of {label, statKeys}. When no
  // groups are provided, fall back to a single unlabeled section containing
  // every visible stat (preserves the legacy flat layout).
  const sections: { label: string | null; statKeys: string[] }[] = (() => {
    if (!groups || groups.length === 0) {
      return [{ label: null, statKeys: visibleStatKeys }];
    }
    const claimed = new Set<string>();
    const out: { label: string | null; statKeys: string[] }[] = [];
    for (const g of groups) {
      const keys = g.statKeys.filter(
        (k) => k in stats && !HIDDEN_STATS.has(k)
      );
      if (keys.length === 0) continue;
      keys.forEach((k) => claimed.add(k));
      out.push({ label: g.name, statKeys: keys });
    }
    const orphans = visibleStatKeys.filter((k) => !claimed.has(k));
    if (orphans.length > 0) {
      out.push({ label: "Other", statKeys: orphans });
    }
    return out;
  })();

  const renderRow = (key: string) => {
    const value = stats[key] || 0;
    const rank = ranks[key] || totalPlayers;
    const colorResult = getRankColorWithStyle(rank, totalPlayers);

    const value2 = player2Stats?.[key] || 0;
    const rank2 = player2Ranks?.[key] || totalPlayers;
    const colorResult2 = player2Ranks ? getRankColorWithStyle(rank2, totalPlayers) : null;

    const p1Better = isComparing && rank < rank2;
    const p2Better = isComparing && rank2 < rank;

    return (
      <tr key={key} className="border-b border-slate-100 last:border-0">
        <td className="py-1.5 px-2 text-slate-700">{getStatLabel(key)}</td>
        {isComparing ? (
          <>
            <td className="py-1.5 px-1 text-right font-medium text-slate-900">
              {formatValue(value)}
            </td>
            <td className="py-1.5 px-1 text-right">
              <span
                className={`inline-block px-1.5 py-0.5 rounded font-medium ${
                  p1Better ? "text-sm ring-2 ring-blue-600 shadow-md font-bold" : "text-xs"
                }`}
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
                className={`inline-block px-1.5 py-0.5 rounded font-medium ${
                  p2Better ? "text-sm ring-2 ring-orange-600 shadow-md font-bold" : "text-xs"
                }`}
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
  };

  return (
    <div className="overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 px-2 font-medium text-slate-600">Stat</th>
            {isComparing ? (
              <>
                <th className="text-right py-2 px-1 font-medium text-blue-600">
                  {player1Name || "P1"}
                </th>
                <th className="text-right py-2 px-1 font-medium text-blue-600">Rank</th>
                <th className="text-right py-2 px-1 font-medium text-orange-600">
                  {player2Name || "P2"}
                </th>
                <th className="text-right py-2 px-1 font-medium text-orange-600">Rank</th>
              </>
            ) : (
              <>
                <th className="text-right py-2 px-2 font-medium text-slate-600">Value</th>
                <th className="text-right py-2 px-2 font-medium text-slate-600">Rank</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {sections.map((section, i) => (
            <Fragment key={`section-${i}-${section.label ?? "flat"}`}>
              {section.label && (
                <tr className="bg-slate-100">
                  <td
                    colSpan={colSpan}
                    className="py-1 px-2 text-xs font-semibold uppercase tracking-wide text-slate-600"
                  >
                    {section.label}
                  </td>
                </tr>
              )}
              {section.statKeys.map(renderRow)}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
