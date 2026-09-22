"""Pipeline node constants aligned with docs/ui-api-contract.md / web/src/lib/pipeline.ts."""
from __future__ import annotations

from typing import Literal

PipelineNodeId = Literal[
    "S1",
    "S2",
    "H1",
    "S3",
    "S4",
    "H2",
    "S5",
    "Compile",
    "H3",
    "S6",
    "S7",
    "S8",
    "S9",
    "H4",
    "S10",
    "H5",
    "S11",
]

HUMAN_GATES = ("H1", "H2", "H3", "H4", "H5")

PIPELINE_NODES: list[dict[str, str]] = [
    {"id": "S1", "label": "S1 — Normalize", "short_label": "Normalize", "kind": "ai"},
    {"id": "S2", "label": "S2 — Analyze", "short_label": "Analyze", "kind": "ai"},
    {"id": "H1", "label": "H1 — Requirement Review", "short_label": "Requirement Review", "kind": "human"},
    {"id": "S3", "label": "S3 — Test Cases", "short_label": "Test Cases", "kind": "ai"},
    {"id": "S4", "label": "S4 — Test Data", "short_label": "Test Data", "kind": "ai"},
    {"id": "H2", "label": "H2 — Test Case Review", "short_label": "Test Case Review", "kind": "human"},
    {"id": "S5", "label": "S5 — Automation", "short_label": "Automation", "kind": "ai"},
    {"id": "Compile", "label": "Compile", "short_label": "Compile", "kind": "deterministic"},
    {"id": "H3", "label": "H3 — Script Review", "short_label": "Script Review", "kind": "human"},
    {"id": "S6", "label": "S6 — Execute", "short_label": "Execute", "kind": "ai"},
    {"id": "S7", "label": "S7 — Analyze", "short_label": "Analyze", "kind": "ai"},
    {"id": "S8", "label": "S8 — Security", "short_label": "Security", "kind": "deterministic"},
    {"id": "S9", "label": "S9 — Report", "short_label": "Report", "kind": "deterministic"},
    {"id": "H4", "label": "H4 — Execution Review", "short_label": "Execution Review", "kind": "human"},
    {"id": "S10", "label": "S10 — Summary", "short_label": "Summary", "kind": "deterministic"},
    {"id": "H5", "label": "H5 — Release Review", "short_label": "Release Review", "kind": "human"},
    {"id": "S11", "label": "S11 — CI Gate", "short_label": "CI Gate", "kind": "deterministic"},
]

PIPELINE_NODE_INDEX = {n["id"]: i for i, n in enumerate(PIPELINE_NODES)}

ARTIFACT_TYPE_TO_NODE: dict[str, str] = {
    "s1_normalized_requirement": "S1",
    "s2_ambiguity_analysis": "S2",
    "s3_test_cases": "S3",
    "s4_test_data": "S4",
    "s5_automation_model": "S5",
    "s5_compiled_playwright": "Compile",
    "s6_execution_result": "S6",
    "s7_classification": "S7",
    "s8_boundary_scan": "S8",
    "s9_report": "S9",
    "s9_allure_results": "S9",
    "s10_release_summary": "S10",
    "s11_cicd_status": "S11",
}

ARTIFACT_DISPLAY_NAME: dict[str, str] = {
    "s1_normalized_requirement": "s1_normalized_requirement.json",
    "s2_ambiguity_analysis": "s2_ambiguity_analysis.json",
    "s3_test_cases": "s3_test_cases.json",
    "s4_test_data": "s4_test_data.json",
    "s5_automation_model": "s5_automation_model.json",
    "s5_compiled_playwright": "playwright_specs",
    "s6_execution_result": "s6_execution_result.json",
    "s7_classification": "s7_classification.json",
    "s8_boundary_scan": "s8_boundary_scan.json",
    "s9_report": "s9_report.json",
    "s9_allure_results": "s9_allure_results.json",
    "s10_release_summary": "s10_release_summary.json",
    "s11_cicd_status": "s11_cicd_status.json",
}

EXPLICIT_RUNNING_STAGES = frozenset(
    {"S1", "S2", "S3", "S4", "S5", "Compile", "S6", "S7", "S8", "S9", "S10", "S11"}
)
