interface RankColorResult {
  className: string;
  style: { backgroundColor: string; color: string };
}

/**
 * Returns Tailwind CSS classes and inline styles for rank badge based on absolute rank
 * Using inline styles to ensure colors aren't overridden by dark mode
 * @param rank - The player's rank (1 = best)
 * @param totalPlayers - Total number of players (unused, kept for API compatibility)
 */
export function getRankColor(rank: number, _totalPlayers: number): string {
  const result = getRankColorWithStyle(rank, _totalPlayers);
  return result.className;
}

export function getRankColorWithStyle(rank: number, _totalPlayers: number): RankColorResult {
  if (rank <= 15) {
    // Rank 1-15 - Elite (green)
    return {
      className: "bg-green-100 text-green-700",
      style: { backgroundColor: "#dcfce7", color: "#15803d" }
    };
  } else if (rank <= 30) {
    // Rank 16-30 - Good (yellow)
    return {
      className: "bg-yellow-100 text-yellow-700",
      style: { backgroundColor: "#fef9c3", color: "#a16207" }
    };
  } else if (rank <= 100) {
    // Rank 31-100 - Average (orange)
    return {
      className: "bg-orange-100 text-orange-700",
      style: { backgroundColor: "#ffedd5", color: "#c2410c" }
    };
  } else {
    // Rank 101+ - Below average (red)
    return {
      className: "bg-red-100 text-red-600",
      style: { backgroundColor: "#fee2e2", color: "#dc2626" }
    };
  }
}
