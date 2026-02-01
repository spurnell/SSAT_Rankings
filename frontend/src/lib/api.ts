const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Player {
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

export interface PlayerStats {
  tackles: number;
  solo_tackles: number;
  sacks: number;
  qb_hits: number;
  passes_defended: number;
  interceptions: number;
  forced_fumbles: number;
  fumble_recoveries: number;
  defensive_tds: number;
}

export interface PlayerDetail extends Player {
  stats: PlayerStats;
}

export async function fetchRankings(params?: {
  position?: string;
  min_games?: number;
}): Promise<Player[]> {
  const searchParams = new URLSearchParams();
  if (params?.position && params.position !== "All") {
    searchParams.append("position", params.position);
  }
  if (params?.min_games) {
    searchParams.append("min_games", params.min_games.toString());
  }

  const response = await fetch(`${API_BASE_URL}/api/rankings?${searchParams}`);
  if (!response.ok) {
    throw new Error("Failed to fetch rankings");
  }
  return response.json();
}

export async function fetchPlayer(id: number): Promise<PlayerDetail> {
  const response = await fetch(`${API_BASE_URL}/api/players/${id}`);
  if (!response.ok) {
    throw new Error("Failed to fetch player");
  }
  return response.json();
}

export async function comparePlayers(ids: number[]): Promise<PlayerDetail[]> {
  const idsParam = ids.join(",");
  const response = await fetch(`${API_BASE_URL}/api/compare?ids=${idsParam}`);
  if (!response.ok) {
    throw new Error("Failed to compare players");
  }
  return response.json();
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error("Backend is not healthy");
  }
  return response.json();
}
