/**
 * Review API / SPA TypeScript contracts for Phase 2+.
 * Aligns with docs/ui-api-contract.md
 */

import type { HumanGateId, PipelineNodeId } from "../lib/pipeline";
import type { DbRunStatus, RunUiState } from "../lib/runState";

export type RequirementType = "BRD" | "User Story" | "Jira" | "API Requirement" | "Other";

/** Supported + passthrough metadata for POST /runs */
export interface StartRunInput {
  raw: string;
  requirement_type?: RequirementType | string;
  environment?: string;
  base_url?: string;
  branch?: string;
  labels?: string[];
}

export interface StartRunRequest {
  input: StartRunInput;
  requirement_id?: string;
}

export interface DecisionRequest {
  reviewer: string;
  comment?: string;
}

export interface RunListItem {
  run_id: string;
  requirement_id?: string;
  requirement_summary?: string | null;
  status: DbRunStatus | string;
  current_stage: string | null;
  pending_gate: HumanGateId | string | null;
  environment?: string | null;
  branch?: string | null;
  base_url?: string | null;
  created_at: string | null;
  updated_at: string | null;
  /** Optional server-embedded mapping; client may recompute via deriveRunUiState */
  ui_state?: RunUiState;
}

export interface RunListResponse {
  runs: RunListItem[];
  total?: number;
  limit?: number;
  offset?: number;
}

export interface RunDetailResponse {
  run_id: string;
  requirement_id: string;
  status: DbRunStatus | string;
  current_stage: string | null;
  pending_gate: HumanGateId | string | null;
  requirement_summary?: string | null;
  raw_input?: StartRunInput | Record<string, unknown> | null;
  environment?: string | null;
  branch?: string | null;
  base_url?: string | null;
  framework_version?: string | null;
  rulebook_version?: string | null;
  model_version?: string | null;
  created_at: string | null;
  updated_at: string | null;
  ui_state: RunUiState;
  last_skill_error?: LastSkillError | null;
}

export interface ArtifactListItem {
  artifact_id: string;
  run_id: string;
  type: string;
  stage: PipelineNodeId | string;
  name: string;
  version: number;
  status: "Completed" | "Approved" | "Pending" | "Failed" | string;
  created_at: string | null;
  storage_uri?: string | null;
}

export interface ArtifactListResponse {
  run_id: string;
  artifacts: ArtifactListItem[];
}

export interface ArtifactDetailResponse {
  artifact_id: string;
  run_id: string;
  type: string;
  version: number;
  content: unknown;
  storage_uri?: string | null;
  created_at: string | null;
}

export type TimelineEventKind = "run_created" | "skill" | "compile" | "review" | "stage";

export interface TimelineEvent {
  at: string;
  kind: TimelineEventKind;
  stage?: string | null;
  title: string;
  detail?: string | null;
  actor?: string | null;
  decision?: string | null;
  artifact_version?: number | null;
}

export interface TimelineResponse {
  run_id: string;
  events: TimelineEvent[];
}

export interface LineageNode {
  node_id: PipelineNodeId | "Requirement";
  label: string;
  artifact_type?: string | null;
  version?: number | null;
  status: string;
}

export interface LineageResponse {
  run_id: string;
  nodes: LineageNode[];
}

export interface TestCaseListItem {
  test_case_id: string;
  run_id: string;
  version: number;
  source_requirement_id: string;
  layer: string;
  obligation?: string | null;
  expected_result?: string | null;
  expected_result_basis?: string | null;
  last_execution_status?: string | null;
  duplicate_of?: string | null;
  created_at?: string | null;
}

export interface ScriptListItem {
  script_id?: string;
  run_id?: string;
  test_case_id: string;
  file_name: string;
  framework: "playwright";
  version: number;
  source?: string;
  spec_path?: string;
  artifact_id?: string;
  review_status?: string | null;
  created_at?: string | null;
}

export interface ExecutionListItem {
  execution_id: string;
  run_id: string;
  test_case_id: string;
  correlation_id?: string | null;
  status: "pass" | "fail" | "skip" | string;
  classification?: string | null;
  retry_attempts?: number | null;
  evidence_manifest?: unknown;
  created_at: string | null;
}

export interface DashboardSummary {
  active_runs: number;
  pending_reviews: number;
  tests_executed: number;
  failed_tests: number;
  runs_completed: number;
  pass_rate: number | null;
  pass_rate_display: string | null;
  pass_rate_basis: string;
  pass_rate_note: string;
}

export interface PendingReviewItem {
  review_id: string;
  run_id: string;
  gate: HumanGateId | string;
  requirement_summary?: string | null;
  waiting_since: string | null;
  artifact_version?: number | null;
  artifact_count?: number | null;
  run_status?: string | null;
  current_stage?: string | null;
}

export interface RecentReviewItem {
  review_id: string;
  run_id: string;
  gate: HumanGateId | string;
  decision: string;
  reviewer?: string | null;
  comment?: string | null;
  requirement_summary?: string | null;
  artifact_version?: number | null;
  created_at: string | null;
  decided_at: string | null;
  run_status?: string | null;
  current_stage?: string | null;
}

export interface StartRunResponse {
  run_id: string;
  status?: string;
  state?: unknown;
  next?: string[];
}

export interface KnowledgeItem {
  knowledge_id: string;
  domain: string;
  rule: string;
  status: "confirmed" | "superseded" | string;
  source?: string | null;
  supersedes?: string | null;
  created_at: string | null;
}

export type IntegrationLabel = "Mock" | "Configured" | "Connected" | "Not Configured" | "Not Wired" | "Coming Soon";

export interface IntegrationsStatus {
  ci: {
    label: IntegrationLabel;
    mode?: string | null;
    detail?: string | null;
  };
  llm_gateway: {
    label: IntegrationLabel;
    provider?: string | null;
    llm_profile?: string | null;
    openai_model?: string | null;
    openai_base_url?: string | null;
    detail?: string | null;
  };
  minio: {
    label: IntegrationLabel;
  };
  playwright: {
    label: IntegrationLabel;
    runner: "playwright_test";
    mode?: string | null;
    mcp: false;
  };
  knowledge_base: {
    label: "Not Wired" | IntegrationLabel;
    writable: false;
  };
  flaky_history: {
    available: false;
    message: string;
  };
  stop_run: {
    available: false;
    message: string;
  };
  llm_setup_hint?: string | null;
}

export interface SkillListItem {
  id: string;
  path: string;
}

export interface SkillDetail {
  id: string;
  path: string;
  markdown: string;
}

export interface LastSkillError {
  skill?: string | null;
  status?: string | null;
  model?: string | null;
  reason: string;
  created_at?: string | null;
  is_quota_or_auth?: boolean;
}

export interface ReviewEvidenceResponse {
  run_id: string;
  run_status: string;
  current_stage: string | null;
  pending_gate: HumanGateId | string | null;
  artifact_version?: number | null;
  review_id?: string | null;
  evidence?: Record<string, unknown>;
  message?: string;
  ui_state?: RunUiState;
}
