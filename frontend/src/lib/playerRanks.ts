import { PlayerDetail } from "@/lib/api";
import { LOWER_IS_BETTER_STATS } from "@/lib/statLabels";

/**
 * For each stat available on the player set, rank players 1..N (1 = best).
 * Returns a Map<playerId, Record<statName, rank>>.
 *
 * `LOWER_IS_BETTER_STATS` flips the sort direction for stats where smaller
 * values mean better performance (e.g. fumbles, sacks_taken).
 */
export function calculateStatRanks(
  players: PlayerDetail[]
): Map<number, Record<string, number>> {
  if (players.length === 0) return new Map();

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
