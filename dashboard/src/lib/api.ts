const API_BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getApiKey(): string {
  return localStorage.getItem("leadgen_api_key") ?? "";
}

export function setApiKey(key: string) {
  if (key) localStorage.setItem("leadgen_api_key", key);
  else localStorage.removeItem("leadgen_api_key");
}

export function getStoredApiKey(): string {
  return getApiKey();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  const apiKey = getApiKey();
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    let message = res.statusText;
    let code: string | undefined;
    try {
      const body = await res.json();
      message = body?.error?.message ?? message;
      code = body?.error?.code;
    } catch {
      /* ignore */
    }
    throw new ApiError(message, res.status, code);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Lead {
  id: number;
  state: string;
  county: string;
  source_module: string;
  property_address: string;
  city: string | null;
  zip_code: string | null;
  parcel_id: string | null;
  distress_signals: string[] | null;
  deal_score: number | null;
  status: string;
  raw_data: Record<string, unknown> | null;
  created_at: string;
}

export interface LeadStats {
  total: number;
  by_county: Record<string, number>;
  by_status: Record<string, number>;
  by_signal: Record<string, number>;
}

export interface SourceInfo {
  key: string;
  name: string;
  state: string;
  county: string;
  description: string;
}

export interface FetchResult {
  source_key: string;
  county: string;
  leads_fetched: number;
  ingest?: { created: number; updated: number; skipped: number };
  sample: Array<Record<string, unknown>>;
  used_fixture_fallback: boolean;
  error?: string;
}

export interface Health {
  status: string;
  database: string;
  require_human_approval: boolean;
  target_states: string[];
  tx_counties: string[];
  fl_counties: string[];
  phase: number;
  version: string;
}

export const api = {
  health: () => request<Health>("/api/health"),
  stats: () => request<LeadStats>("/api/stats/leads"),
  sources: () => request<SourceInfo[]>("/api/sources"),
  fetchTx: (sources?: string[], persist = true) =>
    request<{ results: FetchResult[]; total_leads_in_db: number | null }>(
      "/api/sources/fetch-tx",
      {
        method: "POST",
        body: JSON.stringify({ sources, persist }),
      },
    ),
  leads: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    );
    return request<Paginated<Lead>>(`/api/leads?${qs}`);
  },
  lead: (id: number) => request<Lead>(`/api/leads/${id}`),
  approvalQueue: (page = 1) =>
    request<Paginated<{
      id: number;
      lead_id: number;
      channel: string;
      draft_subject: string | null;
      draft_body: string;
      status: string;
      created_at: string;
    }>>(`/api/approval-queue?page=${page}&page_size=25`),
};
