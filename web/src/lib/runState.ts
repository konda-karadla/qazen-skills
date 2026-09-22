import {
  ARTIFACT_TYPE_TO_NODE,
  getNodeDef,
  HUMAN_GATES,
  isHumanGate,
  PIPELINE_NODE_INDEX,
  PIPELINE_NODES,
  type HumanGateId,
  type PipelineNodeId,
  type PipelineNodeKind,
} from "./pipeline";

export type DbRunStatus = "pending" | "running" | "paused" | "completed" | "failed" | "cancelled";

export type UiStatus =
  | "running"
  | "awaiting_review"
  | "revising"
  | "completed"
  | "failed"
  | "rejected"
  | "cancelled";

export type PipelineNodeState = "completed" | "current" | "pending" | "failed" | "approved";

export type RunHealth = "on_track" | "blocked" | "failed";

export type PrimaryCta = "open_review" | "view_report" | "none";

export type ListStatusPillKey =
  | "in_progress"
  | "awaiting_review"
  | "completed"
  | "failed"
  | "rejected"
  | "cancelled";

export interface ArtifactRef {
  type: string;
  version?: number;
}

export interface ReviewRef {
  gate: HumanGateId | string;
  decision: "pending" | "approved" | "rejected" | "changes_requested" | string;
}

export interface DeriveRunUiStateInput {
  status: DbRunStatus | string;
  current_stage: string | null | undefined;
  pending_gate?: HumanGateId | string | null;
  artifacts?: ArtifactRef[];
  reviews?: ReviewRef[];
}

export interface PipelineNodeUi {
  id: PipelineNodeId;
  label: string;
  shortLabel: string;
  kind: PipelineNodeKind;
  state: PipelineNodeState;
}

export interface ListStatusPill {
  key: ListStatusPillKey;
  label: string;
}

export interface RunUiState {
  uiStatus: UiStatus;
  currentNodeId: PipelineNodeId;
  currentLabel: string;
  actionRequired: boolean;
  actionGate: HumanGateId | null;
  runHealth: RunHealth;
  primaryCta: PrimaryCta;
  /** v1: Orchestrator has no cancel API — never show an active Stop. */
  stopRunAvailable: false;
  shareAction: "copy_url";
  pipelineNodes: PipelineNodeUi[];
  listStatusPill: ListStatusPill;
  /** Server-derived working copy; null when paused/terminal. */
  progressMessage: string | null;
}

const EXPLICIT_RUNNING_STAGES = new Set<PipelineNodeId>([
  "S1",
  "S2",
  "S3",
  "S4",
  "S5",
  "Compile",
  "S6",
  "S7",
  "S8",
  "S9",
  "S10",
  "S11",
]);

const PROGRESS_BY_STAGE: Partial<Record<PipelineNodeId, string>> = {
  S1: "Normalizing the requirement…",
  S2: "Analyzing ambiguities…",
  S3: "Generating test cases…",
  S4: "Generating test data…",
  S5: "Generating automation…",
  Compile: "Compiling Playwright…",
  S6: "Running tests…",
  S7: "Classifying failures…",
  S8: "Scanning boundaries…",
  S9: "Building the report…",
  S10: "Writing the release summary…",
};

export type PollFreshness = "live" | "updating" | "delayed";

/** Live = recent successful GET, not merely that a poll timer exists. */
export function pollFreshness(opts: {
  lastSuccessAt: number | null;
  consecutiveFailures: number;
  now?: number;
}): PollFreshness {
  if (opts.consecutiveFailures >= 2) return "delayed";
  if (opts.lastSuccessAt == null) return "updating";
  const age = (opts.now ?? Date.now()) - opts.lastSuccessAt;
  if (age < 5_000) return "live";
  if (age <= 15_000) return "updating";
  return "delayed";
}

export function formatUpdatedAgo(lastSuccessAt: number, now = Date.now()): string {
  const secs = Math.max(0, Math.floor((now - lastSuccessAt) / 1000));
  return secs === 0 ? "Updated just now" : `Updated ${secs}s ago`;
}

function parseGateSuffix(stage: string, suffix: "_pending" | "_revising" | "_rejected"): HumanGateId | null {
  for (const gate of HUMAN_GATES) {
    if (stage === `${gate}${suffix}`) return gate;
  }
  return null;
}

function nodesPresentFromArtifacts(artifacts: ArtifactRef[]): Set<PipelineNodeId> {
  const present = new Set<PipelineNodeId>();
  for (const a of artifacts) {
    const node = ARTIFACT_TYPE_TO_NODE[a.type];
    if (node) present.add(node);
  }
  return present;
}

function latestDecisionForGate(reviews: ReviewRef[], gate: HumanGateId): string | null {
  // Prefer the last matching review in array order (API returns chronological ASC).
  let found: string | null = null;
  for (const r of reviews) {
    if (r.gate === gate) found = r.decision;
  }
  return found;
}

function approvedGates(reviews: ReviewRef[]): Set<HumanGateId> {
  const set = new Set<HumanGateId>();
  for (const gate of HUMAN_GATES) {
    if (latestDecisionForGate(reviews, gate) === "approved") set.add(gate);
  }
  return set;
}

/**
 * Resolve which pipeline node is the frontier (current focus).
 */
export function resolveCurrentNodeId(input: DeriveRunUiStateInput): PipelineNodeId {
  const stage = input.current_stage ?? "";
  const pending = input.pending_gate;

  const rejected = parseGateSuffix(stage, "_rejected");
  if (rejected) return rejected;

  const revising = parseGateSuffix(stage, "_revising");
  if (revising) return revising;

  if (pending && isHumanGate(String(pending))) return pending as HumanGateId;

  const pendingStage = parseGateSuffix(stage, "_pending");
  if (pendingStage) return pendingStage;

  if (input.status === "completed" || stage === "S11") return "S11";

  if (EXPLICIT_RUNNING_STAGES.has(stage as PipelineNodeId)) {
    return stage as PipelineNodeId;
  }

  // Infer from artifacts: first node without evidence / approval.
  const present = nodesPresentFromArtifacts(input.artifacts ?? []);
  const approved = approvedGates(input.reviews ?? []);

  for (const node of PIPELINE_NODES) {
    if (node.kind === "human") {
      if (!approved.has(node.id as HumanGateId)) return node.id;
      continue;
    }
    if (!present.has(node.id)) return node.id;
  }

  return "S11";
}

function buildPipelineNodes(
  currentId: PipelineNodeId,
  uiStatus: UiStatus,
  reviews: ReviewRef[],
): PipelineNodeUi[] {
  const currentIndex = PIPELINE_NODE_INDEX[currentId];
  const approved = approvedGates(reviews);

  return PIPELINE_NODES.map((def, index) => {
    let state: PipelineNodeState;

    if (uiStatus === "rejected" && index === currentIndex) {
      state = "failed";
    } else if (uiStatus === "completed" || (uiStatus !== "failed" && index < currentIndex)) {
      if (def.kind === "human" && approved.has(def.id as HumanGateId)) {
        state = "approved";
      } else if (def.kind === "human" && index < currentIndex) {
        // Gate passed even if history sparse (e.g. inferred)
        state = "approved";
      } else {
        state = "completed";
      }
    } else if (index === currentIndex) {
      state = uiStatus === "failed" && def.kind !== "human" ? "failed" : "current";
    } else {
      state = "pending";
    }

    return {
      id: def.id,
      label: def.label,
      shortLabel: def.shortLabel,
      kind: def.kind,
      state,
    };
  });
}

function listPill(uiStatus: UiStatus): ListStatusPill {
  switch (uiStatus) {
    case "awaiting_review":
      return { key: "awaiting_review", label: "Paused – Awaiting Review" };
    case "revising":
    case "running":
      return { key: "in_progress", label: "In Progress" };
    case "completed":
      return { key: "completed", label: "Completed" };
    case "rejected":
      return { key: "rejected", label: "Rejected" };
    case "cancelled":
      return { key: "cancelled", label: "Cancelled" };
    case "failed":
    default:
      return { key: "failed", label: "Failed" };
  }
}

/**
 * Canonical run → UI state mapping. Use this everywhere (Run Detail, lists, dashboard).
 */
export function deriveRunUiState(input: DeriveRunUiStateInput): RunUiState {
  const stage = input.current_stage ?? "";
  const reviews = input.reviews ?? [];
  const currentNodeId = resolveCurrentNodeId(input);
  const nodeDef = getNodeDef(currentNodeId);

  let uiStatus: UiStatus;
  let actionGate: HumanGateId | null = null;
  let actionRequired = false;
  let runHealth: RunHealth = "on_track";
  let primaryCta: PrimaryCta = "none";

  const rejectedGate = parseGateSuffix(stage, "_rejected");
  const revisingGate = parseGateSuffix(stage, "_revising");
  const pendingFromStage = parseGateSuffix(stage, "_pending");
  const pendingGate =
    (input.pending_gate && isHumanGate(String(input.pending_gate))
      ? (input.pending_gate as HumanGateId)
      : null) ?? pendingFromStage;

  if (input.status === "cancelled") {
    uiStatus = "cancelled";
    runHealth = "failed";
  } else if (rejectedGate || (input.status === "failed" && isHumanGate(currentNodeId))) {
    uiStatus = "rejected";
    runHealth = "failed";
    actionGate = rejectedGate ?? (isHumanGate(currentNodeId) ? currentNodeId : null);
  } else if (input.status === "failed") {
    uiStatus = "failed";
    runHealth = "failed";
  } else if (revisingGate) {
    uiStatus = "revising";
    actionGate = revisingGate;
    runHealth = "on_track";
  } else if (pendingGate && (input.status === "paused" || pendingFromStage || input.pending_gate)) {
    uiStatus = "awaiting_review";
    actionRequired = true;
    actionGate = pendingGate;
    runHealth = "blocked";
    primaryCta = "open_review";
  } else if (input.status === "completed") {
    uiStatus = "completed";
    primaryCta = "view_report";
    runHealth = "on_track";
  } else {
    uiStatus = "running";
    runHealth = "on_track";
  }

  const pipelineNodes = buildPipelineNodes(currentNodeId, uiStatus, reviews);

  return {
    uiStatus,
    currentNodeId,
    currentLabel: nodeDef.label,
    actionRequired,
    actionGate,
    runHealth,
    primaryCta,
    stopRunAvailable: false,
    shareAction: "copy_url",
    pipelineNodes,
    listStatusPill: listPill(uiStatus),
    progressMessage: progressMessageFor(uiStatus, stage),
  };
}

function progressMessageFor(uiStatus: UiStatus, stage: string): string | null {
  if (uiStatus === "revising" && parseGateSuffix(stage, "_revising")) {
    return "Revising the prior phase, then this gate will reopen.";
  }
  if (uiStatus === "running") {
    return PROGRESS_BY_STAGE[stage as PipelineNodeId] ?? null;
  }
  return null;
}
