import type {
  ArtifactDetailResponse,
  ArtifactListResponse,
  DashboardSummary,
  DecisionRequest,
  IntegrationsStatus,
  KnowledgeItem,
  LineageResponse,
  PendingReviewItem,
  RecentReviewItem,
  ReviewEvidenceResponse,
  RunDetailResponse,
  RunListResponse,
  ScriptListItem,
  SkillDetail,
  SkillListItem,
  StartRunRequest,
  StartRunResponse,
  TestCaseListItem,
  TimelineResponse,
  ExecutionListItem,
} from "./types";

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(formatApiError(status, body));
    this.status = status;
    this.body = body;
  }
}

function formatApiError(status: number, body: string): string {
  const trimmed = (body || "").trim();
  if (!trimmed) return `Request failed (${status})`;
  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      const parts = parsed.detail
        .map((d) => {
          if (typeof d === "string") return d;
          if (d && typeof d === "object" && "msg" in d) return String((d as { msg: string }).msg);
          return null;
        })
        .filter(Boolean);
      if (parts.length) return parts.join("; ");
    }
  } catch {
    /* not JSON */
  }
  if (trimmed.length > 180) return `Request failed (${status})`;
  return trimmed.startsWith("API ") ? trimmed : `API ${status}: ${trimmed}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  getDashboardSummary() {
    return request<DashboardSummary>("/dashboard/summary");
  },
  getPendingReviews(limit = 50) {
    return request<{ reviews: PendingReviewItem[] }>(`/reviews/pending?limit=${limit}`);
  },
  getRecentReviews(limit = 50) {
    return request<{ reviews: RecentReviewItem[] }>(`/reviews/recent?limit=${limit}`);
  },
  getIntegrationsStatus() {
    return request<IntegrationsStatus>("/integrations/status");
  },
  listSkills() {
    return request<{ skills: SkillListItem[] }>("/skills");
  },
  getSkill(skillId: string) {
    return request<SkillDetail>(`/skills/${encodeURIComponent(skillId)}`);
  },
  getKnowledge(limit = 100) {
    return request<{
      writable: false;
      message: string;
      items: KnowledgeItem[];
    }>(`/knowledge?limit=${limit}`);
  },
  listRuns(params?: { limit?: number; offset?: number; status?: string; stage?: string }) {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.offset != null) q.set("offset", String(params.offset));
    if (params?.status) q.set("status", params.status);
    if (params?.stage) q.set("stage", params.stage);
    const qs = q.toString();
    return request<RunListResponse>(`/runs${qs ? `?${qs}` : ""}`);
  },
  listTestCases(params?: { limit?: number; runId?: string }) {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.runId) q.set("run_id", params.runId);
    const qs = q.toString();
    return request<{ test_cases: TestCaseListItem[]; limit?: number }>(`/test-cases${qs ? `?${qs}` : ""}`);
  },
  listScripts(params?: { limit?: number; runId?: string }) {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.runId) q.set("run_id", params.runId);
    const qs = q.toString();
    return request<{ scripts: ScriptListItem[]; limit?: number }>(`/scripts${qs ? `?${qs}` : ""}`);
  },
  listExecutions(params?: { limit?: number; runId?: string }) {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.runId) q.set("run_id", params.runId);
    const qs = q.toString();
    return request<{ executions: ExecutionListItem[]; limit?: number }>(`/executions${qs ? `?${qs}` : ""}`);
  },
  startRun(body: StartRunRequest) {
    return request<StartRunResponse>("/runs", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  getRun(runId: string) {
    return request<RunDetailResponse>(`/runs/${runId}`);
  },
  getArtifacts(runId: string) {
    return request<ArtifactListResponse>(`/runs/${runId}/artifacts`);
  },
  getArtifact(runId: string, artifactId: string) {
    return request<ArtifactDetailResponse>(`/runs/${runId}/artifacts/${artifactId}`);
  },
  getTimeline(runId: string) {
    return request<TimelineResponse>(`/runs/${runId}/timeline`);
  },
  getLineage(runId: string) {
    return request<LineageResponse>(`/runs/${runId}/lineage`);
  },
  getTestCases(runId: string) {
    return request<{ run_id: string; test_cases: TestCaseListItem[] }>(`/runs/${runId}/test-cases`);
  },
  getScripts(runId: string) {
    return request<{ run_id: string; scripts: ScriptListItem[] }>(`/runs/${runId}/scripts`);
  },
  getExecutions(runId: string) {
    return request<{ run_id: string; executions: ExecutionListItem[] }>(`/runs/${runId}/executions`);
  },
  getReview(runId: string) {
    return request<ReviewEvidenceResponse>(`/runs/${runId}/review`);
  },
  approve(runId: string, body: DecisionRequest) {
    return request<unknown>(`/runs/${runId}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  reject(runId: string, body: DecisionRequest) {
    return request<unknown>(`/runs/${runId}/reject`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  requestChanges(runId: string, body: DecisionRequest) {
    return request<unknown>(`/runs/${runId}/request-changes`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};

export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function shortRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

const REVIEWER_KEY = "qazen.reviewer";

export function loadReviewer(): string {
  try {
    return localStorage.getItem(REVIEWER_KEY) || "qa-lead";
  } catch {
    return "qa-lead";
  }
}

export function saveReviewer(name: string) {
  try {
    localStorage.setItem(REVIEWER_KEY, name);
  } catch {
    /* ignore */
  }
}
