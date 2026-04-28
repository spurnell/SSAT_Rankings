import { API_BASE_URL, CustomCategory } from "./api";

export interface AuthUser {
  id: number;
  email: string;
}

export interface SavedRankingSummary {
  id: number;
  title: string;
  position_group: string;
  share_mode: "none" | "live" | "frozen";
  share_slug: string | null;
  created_at: string;
  updated_at: string;
}

export interface SavedRankingDetail extends SavedRankingSummary {
  weights: Record<string, number> | null;
  categories: CustomCategory[] | null;
  min_games: number | null;
  position_filter: string | null;
  mode: string | null;
  min_seasons: number | null;
  source: string | null;
  results: Array<Record<string, unknown>>;
}

export interface SharedRankingView {
  title: string;
  position_group: string;
  share_mode: "live" | "frozen";
  categories: CustomCategory[] | null;
  results: Array<Record<string, unknown>>;
  results_computed_at: string | null;
}

export interface SaveRankingPayload {
  title: string;
  share_mode: "none" | "live" | "frozen";
  position_group: string;
  weights?: Record<string, number>;
  categories?: CustomCategory[];
  min_games?: number;
  position_filter?: string;
  mode?: string;
  min_seasons?: number;
  source?: string;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const withCreds: RequestInit = { credentials: "include" };

export async function requestMagicLink(email: string): Promise<void> {
  await json<{ ok: boolean }>(
    await fetch(`${API_BASE_URL}/api/auth/request-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    })
  );
}

export async function verifyToken(token: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE_URL}/api/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
    ...withCreds,
  });
  const body = await json<{ user: AuthUser }>(res);
  return body.user;
}

export async function getMe(): Promise<AuthUser | null> {
  const res = await fetch(`${API_BASE_URL}/api/auth/me`, withCreds);
  if (res.status === 401) return null;
  return json<AuthUser>(res);
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST", ...withCreds });
}

export async function listSavedRankings(): Promise<SavedRankingSummary[]> {
  return json<SavedRankingSummary[]>(
    await fetch(`${API_BASE_URL}/api/saved-rankings`, withCreds)
  );
}

export async function getSavedRanking(id: number): Promise<SavedRankingDetail> {
  return json<SavedRankingDetail>(
    await fetch(`${API_BASE_URL}/api/saved-rankings/${id}`, withCreds)
  );
}

export async function createSavedRanking(
  payload: SaveRankingPayload
): Promise<SavedRankingDetail> {
  return json<SavedRankingDetail>(
    await fetch(`${API_BASE_URL}/api/saved-rankings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      ...withCreds,
    })
  );
}

export async function updateSavedRanking(
  id: number,
  payload: Partial<SaveRankingPayload>
): Promise<SavedRankingDetail> {
  return json<SavedRankingDetail>(
    await fetch(`${API_BASE_URL}/api/saved-rankings/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      ...withCreds,
    })
  );
}

export async function deleteSavedRanking(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/saved-rankings/${id}`, {
    method: "DELETE",
    ...withCreds,
  });
  if (!res.ok) throw new Error(`${res.status}`);
}

export async function getSharedRanking(slug: string): Promise<SharedRankingView> {
  return json<SharedRankingView>(
    await fetch(`${API_BASE_URL}/api/shared/${slug}`)
  );
}
