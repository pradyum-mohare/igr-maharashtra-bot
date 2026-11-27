import type {
  DistrictOption,
  JobDetail,
  JobSummary,
  PropertyRecord,
  PropertyRecordDetail,
  SearchType,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (init?.body) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...headers,
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listDistricts: () => request<DistrictOption[]>("/api/metadata/districts"),
  listSros: (district: string) =>
    request<{ district: string; source: string; items: string[] }>(
      `/api/metadata/sros?district=${encodeURIComponent(district)}`
    ),
  listTahsils: (district: string) =>
    request<{ district: string; source: string; items: string[] }>(
      `/api/metadata/tahsils?district=${encodeURIComponent(district)}`
    ),
  listVillages: (district: string, tahsil: string) =>
    request<{ district: string; tahsil: string; source: string; items: string[] }>(
      `/api/metadata/villages?district=${encodeURIComponent(district)}&tahsil=${encodeURIComponent(tahsil)}`
    ),
  createJob: (payload: { search_type: SearchType; criteria: Record<string, unknown> }) =>
    request<JobSummary>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listJobs: (params?: { status?: string; search_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status && params.status !== "ALL") qs.set("status", params.status);
    if (params?.search_type && params.search_type !== "ALL") qs.set("search_type", params.search_type);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<JobSummary[]>(`/api/jobs${suffix}`);
  },
  getJobDetail: (jobId: string) => request<JobDetail>(`/api/jobs/${jobId}`),
  submitCaptcha: (jobId: string, solution: string) =>
    request<{ message: string; job_id: string }>(`/api/jobs/${jobId}/captcha`, {
      method: "POST",
      body: JSON.stringify({ solution }),
    }),
  refreshCaptcha: (jobId: string) =>
    request<{ message: string; job_id: string }>(`/api/jobs/${jobId}/captcha/refresh`, {
      method: "POST",
    }),
  cancelJob: (jobId: string) =>
    request<{ message: string; job_id: string }>(`/api/jobs/${jobId}/cancel`, {
      method: "POST",
    }),
  retryJob: (jobId: string) =>
    request<JobSummary>(`/api/jobs/${jobId}/retry`, {
      method: "POST",
    }),
  listRecords: (params?: { q?: string; year?: string; district?: string }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.year) qs.set("year", params.year);
    if (params?.district) qs.set("district", params.district);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<PropertyRecord[]>(`/api/records${suffix}`);
  },
  getRecordDetail: (recordId: string) => request<PropertyRecordDetail>(`/api/records/${recordId}`),
  getDocumentDownloadUrl: (docId: string) => `${API_BASE}/api/documents/${docId}/download`,
};
