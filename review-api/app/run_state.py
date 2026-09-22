"""Canonical run → UI state mapping (Python twin of web/src/lib/runState.ts)."""
from __future__ import annotations

from typing import Any, Optional

from app.pipeline import (
    ARTIFACT_TYPE_TO_NODE,
    EXPLICIT_RUNNING_STAGES,
    HUMAN_GATES,
    PIPELINE_NODE_INDEX,
    PIPELINE_NODES,
)


def _parse_gate_suffix(stage: str, suffix: str) -> Optional[str]:
    for gate in HUMAN_GATES:
        if stage == f"{gate}{suffix}":
            return gate
    return None


def _nodes_from_artifacts(artifacts: list[dict[str, Any]]) -> set[str]:
    present: set[str] = set()
    for a in artifacts:
        node = ARTIFACT_TYPE_TO_NODE.get(a.get("type", ""))
        if node:
            present.add(node)
    return present


def _latest_decision(reviews: list[dict[str, Any]], gate: str) -> Optional[str]:
    found: Optional[str] = None
    for r in reviews:
        if r.get("gate") == gate:
            found = r.get("decision")
    return found


def _approved_gates(reviews: list[dict[str, Any]]) -> set[str]:
    return {g for g in HUMAN_GATES if _latest_decision(reviews, g) == "approved"}


def resolve_current_node_id(
    *,
    status: str,
    current_stage: Optional[str],
    pending_gate: Optional[str] = None,
    artifacts: Optional[list[dict[str, Any]]] = None,
    reviews: Optional[list[dict[str, Any]]] = None,
) -> str:
    stage = current_stage or ""
    artifacts = artifacts or []
    reviews = reviews or []

    rejected = _parse_gate_suffix(stage, "_rejected")
    if rejected:
        return rejected

    revising = _parse_gate_suffix(stage, "_revising")
    if revising:
        return revising

    if pending_gate in HUMAN_GATES:
        return pending_gate

    pending_stage = _parse_gate_suffix(stage, "_pending")
    if pending_stage:
        return pending_stage

    if status == "completed" or stage == "S11":
        return "S11"

    if stage in EXPLICIT_RUNNING_STAGES:
        return stage

    present = _nodes_from_artifacts(artifacts)
    approved = _approved_gates(reviews)
    for node in PIPELINE_NODES:
        nid = node["id"]
        if node["kind"] == "human":
            if nid not in approved:
                return nid
            continue
        if nid not in present:
            return nid
    return "S11"


def _list_pill(ui_status: str) -> dict[str, str]:
    mapping = {
        "awaiting_review": ("awaiting_review", "Paused – Awaiting Review"),
        "revising": ("in_progress", "In Progress"),
        "running": ("in_progress", "In Progress"),
        "completed": ("completed", "Completed"),
        "rejected": ("rejected", "Rejected"),
        "cancelled": ("cancelled", "Cancelled"),
        "failed": ("failed", "Failed"),
    }
    key, label = mapping.get(ui_status, ("failed", "Failed"))
    return {"key": key, "label": label}


def _build_pipeline_nodes(current_id: str, ui_status: str, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current_index = PIPELINE_NODE_INDEX[current_id]
    approved = _approved_gates(reviews)
    nodes: list[dict[str, Any]] = []
    for index, defn in enumerate(PIPELINE_NODES):
        nid = defn["id"]
        if ui_status == "rejected" and index == current_index:
            state = "failed"
        elif ui_status == "completed" or (ui_status != "failed" and index < current_index):
            if defn["kind"] == "human" and (nid in approved or index < current_index):
                state = "approved"
            else:
                state = "completed"
        elif index == current_index:
            state = "failed" if ui_status == "failed" and defn["kind"] != "human" else "current"
        else:
            state = "pending"
        nodes.append(
            {
                "id": nid,
                "label": defn["label"],
                "shortLabel": defn["short_label"],
                "kind": defn["kind"],
                "state": state,
            }
        )
    return nodes


def derive_run_ui_state(
    *,
    status: str,
    current_stage: Optional[str],
    pending_gate: Optional[str] = None,
    artifacts: Optional[list[dict[str, Any]]] = None,
    reviews: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    artifacts = artifacts or []
    reviews = reviews or []
    stage = current_stage or ""
    current_node_id = resolve_current_node_id(
        status=status,
        current_stage=current_stage,
        pending_gate=pending_gate,
        artifacts=artifacts,
        reviews=reviews,
    )
    node_def = PIPELINE_NODES[PIPELINE_NODE_INDEX[current_node_id]]

    rejected_gate = _parse_gate_suffix(stage, "_rejected")
    revising_gate = _parse_gate_suffix(stage, "_revising")
    pending_from_stage = _parse_gate_suffix(stage, "_pending")
    pending = pending_gate if pending_gate in HUMAN_GATES else pending_from_stage

    action_gate: Optional[str] = None
    action_required = False
    run_health = "on_track"
    primary_cta = "none"

    if status == "cancelled":
        ui_status = "cancelled"
        run_health = "failed"
    elif rejected_gate or (status == "failed" and current_node_id in HUMAN_GATES):
        ui_status = "rejected"
        run_health = "failed"
        action_gate = rejected_gate or (current_node_id if current_node_id in HUMAN_GATES else None)
    elif status == "failed":
        ui_status = "failed"
        run_health = "failed"
    elif revising_gate:
        ui_status = "revising"
        action_gate = revising_gate
    elif pending and (status == "paused" or pending_from_stage or pending_gate):
        ui_status = "awaiting_review"
        action_required = True
        action_gate = pending
        run_health = "blocked"
        primary_cta = "open_review"
    elif status == "completed":
        ui_status = "completed"
        primary_cta = "view_report"
    else:
        ui_status = "running"

    return {
        "uiStatus": ui_status,
        "currentNodeId": current_node_id,
        "currentLabel": node_def["label"],
        "actionRequired": action_required,
        "actionGate": action_gate,
        "runHealth": run_health,
        "primaryCta": primary_cta,
        "stopRunAvailable": False,
        "shareAction": "copy_url",
        "pipelineNodes": _build_pipeline_nodes(current_node_id, ui_status, reviews),
        "listStatusPill": _list_pill(ui_status),
        "progressMessage": _progress_message(ui_status, stage),
    }


_PROGRESS_BY_STAGE = {
    "S1": "Normalizing the requirement…",
    "S2": "Analyzing ambiguities…",
    "S3": "Generating test cases…",
    "S4": "Generating test data…",
    "S5": "Generating automation…",
    "Compile": "Compiling Playwright…",
    "S6": "Running tests…",
    "S7": "Classifying failures…",
    "S8": "Scanning boundaries…",
    "S9": "Building the report…",
    "S10": "Writing the release summary…",
}


def _progress_message(ui_status: str, stage: str) -> Optional[str]:
    if ui_status == "revising" and _parse_gate_suffix(stage, "_revising"):
        return "Revising the prior phase, then this gate will reopen."
    if ui_status == "running":
        return _PROGRESS_BY_STAGE.get(stage)
    return None
