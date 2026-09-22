/** Canonical pipeline nodes for QAZen Run Detail / timeline. */

export type PipelineNodeKind = "ai" | "human" | "deterministic";

export type PipelineNodeId =
  | "S1"
  | "S2"
  | "H1"
  | "S3"
  | "S4"
  | "H2"
  | "S5"
  | "Compile"
  | "H3"
  | "S6"
  | "S7"
  | "S8"
  | "S9"
  | "H4"
  | "S10"
  | "H5"
  | "S11";

export type HumanGateId = "H1" | "H2" | "H3" | "H4" | "H5";

export interface PipelineNodeDef {
  id: PipelineNodeId;
  label: string;
  shortLabel: string;
  kind: PipelineNodeKind;
}

export const PIPELINE_NODES: readonly PipelineNodeDef[] = [
  { id: "S1", label: "S1 — Normalize", shortLabel: "Normalize", kind: "ai" },
  { id: "S2", label: "S2 — Analyze", shortLabel: "Analyze", kind: "ai" },
  { id: "H1", label: "H1 — Requirement Review", shortLabel: "Requirement Review", kind: "human" },
  { id: "S3", label: "S3 — Test Cases", shortLabel: "Test Cases", kind: "ai" },
  { id: "S4", label: "S4 — Test Data", shortLabel: "Test Data", kind: "ai" },
  { id: "H2", label: "H2 — Test Case Review", shortLabel: "Test Case Review", kind: "human" },
  { id: "S5", label: "S5 — Automation", shortLabel: "Automation", kind: "ai" },
  { id: "Compile", label: "Compile", shortLabel: "Compile", kind: "deterministic" },
  { id: "H3", label: "H3 — Script Review", shortLabel: "Script Review", kind: "human" },
  { id: "S6", label: "S6 — Execute", shortLabel: "Execute", kind: "ai" },
  { id: "S7", label: "S7 — Analyze", shortLabel: "Analyze", kind: "ai" },
  { id: "S8", label: "S8 — Security", shortLabel: "Security", kind: "deterministic" },
  { id: "S9", label: "S9 — Report", shortLabel: "Report", kind: "deterministic" },
  { id: "H4", label: "H4 — Execution Review", shortLabel: "Execution Review", kind: "human" },
  { id: "S10", label: "S10 — Summary", shortLabel: "Summary", kind: "deterministic" },
  { id: "H5", label: "H5 — Release Review", shortLabel: "Release Review", kind: "human" },
  { id: "S11", label: "S11 — CI Gate", shortLabel: "CI Gate", kind: "deterministic" },
] as const;

export const PIPELINE_NODE_INDEX: Record<PipelineNodeId, number> = Object.fromEntries(
  PIPELINE_NODES.map((n, i) => [n.id, i]),
) as Record<PipelineNodeId, number>;

/** Postgres artifacts.type → pipeline node */
export const ARTIFACT_TYPE_TO_NODE: Record<string, PipelineNodeId> = {
  s1_normalized_requirement: "S1",
  s2_ambiguity_analysis: "S2",
  s3_test_cases: "S3",
  s4_test_data: "S4",
  s5_automation_model: "S5",
  s5_compiled_playwright: "Compile",
  s6_execution_result: "S6",
  s7_classification: "S7",
  s8_boundary_scan: "S8",
  s9_report: "S9",
  s9_allure_results: "S9",
  s10_release_summary: "S10",
  s11_cicd_status: "S11",
};

export const HUMAN_GATES: readonly HumanGateId[] = ["H1", "H2", "H3", "H4", "H5"];

export function isHumanGate(id: string): id is HumanGateId {
  return (HUMAN_GATES as readonly string[]).includes(id);
}

export function getNodeDef(id: PipelineNodeId): PipelineNodeDef {
  return PIPELINE_NODES[PIPELINE_NODE_INDEX[id]];
}
