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

// ---------- Custom-data (user-upload) rankings ----------

export interface ColumnSchemaEntry {
  name: string;
  dtype: "numeric" | "text";
}

export interface DatasetSegmentSummary {
  id: number;
  label: string;
  source_filename: string | null;
  row_count: number;
  created_at: string;
}

export interface DatasetSummary {
  id: number;
  title: string;
  name_column: string;
  segment_count: number;
  total_rows: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetDetail {
  id: number;
  title: string;
  name_column: string;
  column_schema: ColumnSchemaEntry[];
  segments: DatasetSegmentSummary[];
  created_at: string;
  updated_at: string;
}

export interface SchemaDrift {
  added: ColumnSchemaEntry[];
  missing: string[];
  type_mismatches: Array<{ name: string; dataset_dtype: string; segment_dtype: string }>;
}

export interface SegmentUploadResponse {
  segment: DatasetSegmentSummary;
  drift: SchemaDrift;
  duplicates: string[];
}

export interface DatasetRankingStat {
  name: string;
  lower_is_better: boolean;
}

export interface DatasetRankingCategory {
  id: string;
  name: string;
  weight: number;
  stats: DatasetRankingStat[];
}

export type DatasetRankingMode = "single" | "cumulative" | "per_game";

export interface DatasetRankingSummary {
  id: number;
  dataset_id: number;
  title: string;
  mode: DatasetRankingMode;
  segment_ids: number[];
  share_mode: "none" | "live" | "frozen";
  share_slug: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetRankingResultRow {
  entity_key: string;
  entity_name: string;
  overall_score: number;
  category_scores: Record<string, number>;
  stats: Record<string, number>;
  contributing_segments: string[];
  games?: number | null;
}

export interface DatasetRankingDetail extends DatasetRankingSummary {
  categories: DatasetRankingCategory[];
  games_column: string | null;
  min_rows: number;
  results: DatasetRankingResultRow[];
}

export interface DatasetRankingCreatePayload {
  title: string;
  categories: DatasetRankingCategory[];
  mode: DatasetRankingMode;
  segment_ids: number[];
  games_column?: string | null;
  min_rows?: number;
}

export interface SharedDatasetRankingView {
  title: string;
  dataset_title: string;
  mode: DatasetRankingMode;
  share_mode: "live" | "frozen";
  categories: DatasetRankingCategory[];
  results: DatasetRankingResultRow[];
  results_computed_at: string | null;
}

const CUSTOM_DATA = `${API_BASE_URL}/api/custom-data`;

export async function listDatasets(): Promise<DatasetSummary[]> {
  return json<DatasetSummary[]>(await fetch(`${CUSTOM_DATA}/datasets`, withCreds));
}

export async function getDataset(id: number): Promise<DatasetDetail> {
  return json<DatasetDetail>(await fetch(`${CUSTOM_DATA}/datasets/${id}`, withCreds));
}

export async function createDataset(args: {
  file: File;
  title: string;
  name_column: string;
  segment_label: string;
}): Promise<DatasetDetail> {
  const form = new FormData();
  form.append("file", args.file);
  form.append("title", args.title);
  form.append("name_column", args.name_column);
  form.append("segment_label", args.segment_label);
  return json<DatasetDetail>(
    await fetch(`${CUSTOM_DATA}/datasets`, {
      method: "POST",
      body: form,
      ...withCreds,
    })
  );
}

export async function deleteDataset(id: number): Promise<void> {
  const res = await fetch(`${CUSTOM_DATA}/datasets/${id}`, {
    method: "DELETE",
    ...withCreds,
  });
  if (!res.ok) throw new Error(`${res.status}`);
}

export async function appendSegment(args: {
  dataset_id: number;
  file: File;
  segment_label: string;
  on_drift?: "accept" | "strict";
}): Promise<SegmentUploadResponse> {
  const form = new FormData();
  form.append("file", args.file);
  form.append("segment_label", args.segment_label);
  form.append("on_drift", args.on_drift ?? "accept");
  return json<SegmentUploadResponse>(
    await fetch(`${CUSTOM_DATA}/datasets/${args.dataset_id}/segments`, {
      method: "POST",
      body: form,
      ...withCreds,
    })
  );
}

export async function deleteSegment(
  dataset_id: number,
  segment_id: number
): Promise<void> {
  const res = await fetch(
    `${CUSTOM_DATA}/datasets/${dataset_id}/segments/${segment_id}`,
    { method: "DELETE", ...withCreds }
  );
  if (!res.ok) throw new Error(`${res.status}`);
}

export async function createDatasetRanking(
  dataset_id: number,
  payload: DatasetRankingCreatePayload
): Promise<DatasetRankingDetail> {
  return json<DatasetRankingDetail>(
    await fetch(`${CUSTOM_DATA}/datasets/${dataset_id}/rankings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      ...withCreds,
    })
  );
}

export async function listDatasetRankings(): Promise<DatasetRankingSummary[]> {
  return json<DatasetRankingSummary[]>(
    await fetch(`${CUSTOM_DATA}/rankings`, withCreds)
  );
}

export async function getDatasetRanking(id: number): Promise<DatasetRankingDetail> {
  return json<DatasetRankingDetail>(
    await fetch(`${CUSTOM_DATA}/rankings/${id}`, withCreds)
  );
}

export async function updateDatasetRanking(
  id: number,
  payload: Partial<DatasetRankingCreatePayload>
): Promise<DatasetRankingDetail> {
  return json<DatasetRankingDetail>(
    await fetch(`${CUSTOM_DATA}/rankings/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      ...withCreds,
    })
  );
}

export async function deleteDatasetRanking(id: number): Promise<void> {
  const res = await fetch(`${CUSTOM_DATA}/rankings/${id}`, {
    method: "DELETE",
    ...withCreds,
  });
  if (!res.ok) throw new Error(`${res.status}`);
}

export async function updateDatasetRankingShare(
  id: number,
  share_mode: "none" | "live" | "frozen"
): Promise<DatasetRankingDetail> {
  return json<DatasetRankingDetail>(
    await fetch(`${CUSTOM_DATA}/rankings/${id}/share`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ share_mode }),
      ...withCreds,
    })
  );
}

export async function getSharedDatasetRanking(
  slug: string
): Promise<SharedDatasetRankingView> {
  return json<SharedDatasetRankingView>(
    await fetch(`${CUSTOM_DATA}/shared/${slug}`)
  );
}
