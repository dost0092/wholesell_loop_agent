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

export interface Contact {
  id: number;
  contact_type: string;
  value: string;
  line_type: string | null;
  validated: boolean;
  confidence_score: number;
  source: string | null;
  validation_details: Record<string, unknown> | null;
}

export interface Owner {
  id: number;
  name: string | null;
  mailing_address: string | null;
  is_llc: boolean;
  entity_name: string | null;
  confidence_score: number;
  source_list: string[] | null;
  contacts: Contact[];
}

export interface LeadDetail extends Lead {
  score_reasoning: string | null;
  motivation_summary: string | null;
  offer_strategy: string | null;
  estimated_arv: number | null;
  estimated_equity: number | null;
  owners: Owner[];
}

export interface PipelineResult {
  lead_id: number;
  status: string;
  steps: Record<string, unknown>;
}

export interface ApprovalItem {
  id: number;
  lead_id: number;
  channel: string;
  draft_subject: string | null;
  draft_body: string;
  status: string;
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
      { method: "POST", body: JSON.stringify({ sources, persist }) },
    ),
  fetchFl: (sources?: string[], persist = true) =>
    request<{ results: FetchResult[]; total_leads_in_db: number | null }>(
      "/api/sources/fetch-fl",
      { method: "POST", body: JSON.stringify({ sources, persist }) },
    ),
  fetchAll: (sources?: string[], persist = true) =>
    request<{ results: FetchResult[]; total_leads_in_db: number | null }>(
      "/api/sources/fetch-all",
      { method: "POST", body: JSON.stringify({ sources, persist }) },
    ),
  leads: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    );
    return request<Paginated<Lead>>(`/api/leads?${qs}`);
  },
  lead: (id: number) => request<LeadDetail>(`/api/leads/${id}`),

  scoreLead: (id: number) =>
    request<LeadDetail>(`/api/leads/${id}/score`, { method: "POST" }),
  traceLead: (id: number) =>
    request<LeadDetail>(`/api/leads/${id}/trace`, { method: "POST" }),
  validateLead: (id: number) =>
    request<LeadDetail>(`/api/leads/${id}/validate`, { method: "POST" }),
  draftLead: (id: number) =>
    request<ApprovalItem>(`/api/leads/${id}/draft`, { method: "POST" }),
  runPipeline: (id: number, draft = true) =>
    request<PipelineResult>(`/api/leads/${id}/pipeline?draft=${draft}`, {
      method: "POST",
    }),

  approvalQueue: (page = 1) =>
    request<Paginated<ApprovalItem>>(
      `/api/approval-queue?page=${page}&page_size=25`,
    ),
  approveItem: (id: number, body: { reviewer?: string; subject?: string; body?: string; send_now?: boolean }) =>
    request<{ id: number; status: string; sent_at: string | null }>(
      `/api/approval-queue/${id}/approve`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  rejectItem: (id: number, notes?: string) =>
    request<ApprovalItem>(`/api/approval-queue/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reviewer: "operator", notes }),
    }),
  sendItem: (id: number) =>
    request<{ id: number; status: string; sent_at: string | null }>(
      `/api/approval-queue/${id}/send`,
      { method: "POST" },
    ),
};
