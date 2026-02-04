interface PlayerStats {
  tackles: number;
  solo_tackles: number;
  assists: number;
  sacks: number;
  qb_hits: number;
  tackles_for_loss: number;
  passes_defended: number;
  interceptions: number;
  forced_fumbles: number;
  fumble_recoveries: number;
  defensive_tds: number;
}

interface StatsTooltipProps {
  stats: PlayerStats;
  playerName: string;
  ranks?: Record<string, number>;
}

function getOrdinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export default function StatsTooltip({ stats, playerName, ranks }: StatsTooltipProps) {
  const formatStat = (value: number) => {
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  };

  const formatWithRank = (value: number, statKey: string) => {
    const formatted = formatStat(value);
    if (ranks && ranks[statKey] !== undefined) {
      return (
        <>
          <span className="font-medium">{formatted}</span>
          <span className="text-xs text-slate-400 ml-1">({getOrdinal(ranks[statKey])})</span>
        </>
      );
    }
    return <span className="font-medium">{formatted}</span>;
  };

  return (
    <div className="absolute z-50 bg-slate-800 text-white rounded-lg shadow-xl p-4 min-w-[280px] -translate-x-1/2 left-1/2 mt-2">
      <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-slate-800"></div>
      <h4 className="font-semibold text-sm mb-3 text-slate-200 border-b border-slate-600 pb-2">
        {playerName} - Raw Stats
      </h4>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">Tackles:</span>
          {formatWithRank(stats.tackles, "tackles")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">Solo:</span>
          {formatWithRank(stats.solo_tackles, "solo_tackles")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">Assists:</span>
          {formatWithRank(stats.assists, "assists")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">Sacks:</span>
          {formatWithRank(stats.sacks, "sacks")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">QB Hits:</span>
          {formatWithRank(stats.qb_hits, "qb_hits")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">TFL:</span>
          {formatWithRank(stats.tackles_for_loss, "tackles_for_loss")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">PD:</span>
          {formatWithRank(stats.passes_defended, "passes_defended")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">INTs:</span>
          {formatWithRank(stats.interceptions, "interceptions")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">FF:</span>
          {formatWithRank(stats.forced_fumbles, "forced_fumbles")}
        </div>
        <div className="flex justify-between items-baseline">
          <span className="text-slate-400">FR:</span>
          {formatWithRank(stats.fumble_recoveries, "fumble_recoveries")}
        </div>
        <div className="flex justify-between items-baseline col-span-2 border-t border-slate-600 pt-2 mt-1">
          <span className="text-slate-400">Def TDs:</span>
          {formatWithRank(stats.defensive_tds, "defensive_tds")}
        </div>
      </div>
    </div>
  );
}
