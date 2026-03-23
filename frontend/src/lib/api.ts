const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Category info from API
export interface CategoryInfo {
  id: string;
  name: string;
}

// Position group info from API
export interface PositionGroup {
  id: string;
  name: string;
  categories: CategoryInfo[];
  sub_positions?: string[];
}

// New dynamic player interface
export interface Player {
  id: number;
  name: string;
  team: string;
  position: string;
  games_played: number;
  overall_score: number;
  position_group: string;
  category_scores: Record<string, number>;
}

export interface PlayerDetail extends Player {
  stats: Record<string, number>;
}

// Legacy interfaces for backward compatibility
export interface LegacyPlayer {
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

export interface LegacyPlayerDetail extends LegacyPlayer {
  stats: PlayerStats;
}

// Detailed category info (includes weight)
export interface CategoryDetailInfo {
  id: string;
  name: string;
  weight: number;
}

// Detailed position group config (from /api/position-config endpoint)
export interface PositionGroupDetail {
  id: string;
  name: string;
  categories: CategoryDetailInfo[];
  sub_positions: string[];
}

// Fetch position groups
export async function fetchPositionGroups(): Promise<PositionGroup[]> {
  const response = await fetch(`${API_BASE_URL}/api/position-groups`);
  if (!response.ok) {
    throw new Error("Failed to fetch position groups");
  }
  return response.json();
}

// Fetch available seasons
export async function fetchAvailableSeasons(): Promise<number[]> {
  const response = await fetch(`${API_BASE_URL}/api/available-seasons`);
  if (!response.ok) {
    throw new Error("Failed to fetch available seasons");
  }
  return response.json();
}

// Fetch rankings for a specific position group
export async function fetchRankings(params?: {
  position_group?: string;
  position?: string;
  min_games?: number;
  season?: number;
}): Promise<PlayerDetail[]> {
  const searchParams = new URLSearchParams();
  if (params?.position && params.position !== "All") {
    searchParams.append("position", params.position);
  }
  if (params?.min_games) {
    searchParams.append("min_games", params.min_games.toString());
  }
  if (params?.season) {
    searchParams.append("season", params.season.toString());
  }

  const positionGroup = params?.position_group || "DEF";
  const response = await fetch(
    `${API_BASE_URL}/api/rankings/${positionGroup}?${searchParams}`
  );
  if (!response.ok) {
    throw new Error("Failed to fetch rankings");
  }
  return response.json();
}

// Legacy fetch for backward compatibility (defensive players only)
export async function fetchLegacyRankings(params?: {
  position?: string;
  min_games?: number;
}): Promise<LegacyPlayerDetail[]> {
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

export async function fetchPlayer(id: number): Promise<LegacyPlayerDetail> {
  const response = await fetch(`${API_BASE_URL}/api/players/${id}`);
  if (!response.ok) {
    throw new Error("Failed to fetch player");
  }
  return response.json();
}

export async function comparePlayers(ids: number[]): Promise<LegacyPlayerDetail[]> {
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

// Fetch detailed position config (with weights)
export async function fetchPositionConfig(positionGroup: string): Promise<PositionGroupDetail> {
  const response = await fetch(`${API_BASE_URL}/api/position-config/${positionGroup}`);
  if (!response.ok) {
    throw new Error("Failed to fetch position config");
  }
  return response.json();
}

// Calculate rankings with custom weights
export async function calculateRankings(params: {
  position_group: string;
  weights: Record<string, number>;
  min_games?: number;
  position?: string;
  mode?: string;
  min_seasons?: number;
}): Promise<PlayerDetail[]> {
  const response = await fetch(`${API_BASE_URL}/api/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error("Failed to calculate rankings");
  }
  return response.json();
}

// Fetch career rankings
export async function fetchCareerRankings(params: {
  position_group: string;
  mode?: string;
  min_seasons?: number;
  min_games?: number;
}): Promise<PlayerDetail[]> {
  // Career rankings not yet implemented on backend — fall back to season rankings
  return fetchRankings({
    position_group: params.position_group,
    min_games: params.min_games,
  });
}

// Blog API types
export interface BlogPost {
  id: number;
  slug: string;
  title: string;
  excerpt: string | null;
  content: string;
  post_type: string;
  featured_players: string[] | null;
  tags: string[] | null;
  published_at: string | null;
  created_at: string;
  is_published: boolean;
}

export interface BlogPostListItem {
  id: number;
  slug: string;
  title: string;
  excerpt: string | null;
  post_type: string;
  featured_players: string[] | null;
  tags: string[] | null;
  published_at: string | null;
  created_at: string;
}

export async function fetchBlogPosts(params?: {
  limit?: number;
  offset?: number;
  post_type?: string;
}): Promise<BlogPostListItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) {
    searchParams.append("limit", params.limit.toString());
  }
  if (params?.offset) {
    searchParams.append("offset", params.offset.toString());
  }
  if (params?.post_type) {
    searchParams.append("post_type", params.post_type);
  }

  const response = await fetch(`${API_BASE_URL}/api/blog/posts?${searchParams}`);
  if (!response.ok) {
    throw new Error("Failed to fetch blog posts");
  }
  return response.json();
}

export async function fetchBlogPost(slug: string): Promise<BlogPost> {
  const response = await fetch(`${API_BASE_URL}/api/blog/posts/${slug}`);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Blog post not found");
    }
    throw new Error("Failed to fetch blog post");
  }
  return response.json();
}
