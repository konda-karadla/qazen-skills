from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import START

from app import db
from app.config import settings
from app.gateway_client import LlmGatewayError, SkillEscalatedError
from app.graph import compile_graph

logger = logging.getLogger(__name__)

# Gate name -> the langgraph node it pauses before.
GATE_TO_NEXT_NODE = {"H1": "s3", "H2": "s5", "H3": "s6", "H4": "s10", "H5": "s11"}

# Gate -> as_node predecessor so update_state makes `next` the first node to redo.
GATE_REVISE_AS_NODE: dict[str, Any] = {
    "H1": START,
    "H2": "s2",
    "H3": "s4",
    "H4": "s5",
    "H5": "s9",
}

# Cap concurrent graph starts so a local Ollama instance is not stampeded.
_RUN_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="qazen-run")


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _record_graph_failure(run_id: str, exc: BaseException) -> None:
    """Persist a visible failure reason for the Review UI, then mark the run failed."""
    skill = "pipeline"
    reason = str(exc)[:4000] or type(exc).__name__
    if isinstance(exc, SkillEscalatedError):
        skill = exc.skill_id
        reason = exc.reason[:4000]
    elif isinstance(exc, LlmGatewayError):
        skill = exc.skill_id
        reason = exc.reason[:4000]
    try:
        db.save_skill_execution(
            run_id,
            skill,
            status="failed",
            model=settings.model_version,
            escalation_reason=reason,
        )
    except Exception:
        logger.exception("Could not persist skill failure for run %s", run_id)
    try:
        db.update_run(run_id, status="failed")
    except Exception:
        logger.exception("Could not mark run %s as failed after graph error", run_id)


def _persist_run(
    requirement_input: dict[str, Any], requirement_id: Optional[str] = None
) -> tuple[str, dict[str, Any]]:
    run_id = str(uuid.uuid4())
    requirement_id = requirement_id or run_id
    db.create_run(
        run_id,
        requirement_id,
        base_url=requirement_input.get("base_url") if isinstance(requirement_input, dict) else None,
        environment=(
            requirement_input.get("environment") if isinstance(requirement_input, dict) else None
        ),
        branch=requirement_input.get("branch") if isinstance(requirement_input, dict) else None,
    )
    db.update_run(run_id, current_stage="S1", status="running")
    initial_state: dict[str, Any] = {
        "run_id": run_id,
        "requirement_id": requirement_id,
        "raw_input": requirement_input,
        "artifact_ids": {},
    }
    return run_id, initial_state


def _invoke_until_pause(run_id: str, initial_state: dict[str, Any]) -> dict[str, Any]:
    with PostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        checkpointer.setup()
        graph = compile_graph(checkpointer)
        result_state = graph.invoke(initial_state, config=_config(run_id))
        snapshot = graph.get_state(_config(run_id))

    return {"run_id": run_id, "state": result_state, "next": list(snapshot.next)}


def _invoke_until_pause_safe(run_id: str, initial_state: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        return _invoke_until_pause(run_id, initial_state)
    except Exception as exc:
        logger.exception("Background start_run failed for %s", run_id)
        _record_graph_failure(run_id, exc)
        return None


def start_run(requirement_input: dict[str, Any], requirement_id: Optional[str] = None) -> dict[str, Any]:
    run_id, initial_state = _persist_run(requirement_input, requirement_id)
    return _invoke_until_pause(run_id, initial_state)


def start_run_background(
    requirement_input: dict[str, Any], requirement_id: Optional[str] = None
) -> dict[str, Any]:
    """Insert the run row and invoke S1–S2 on a worker thread.

    HTTP POST /runs uses this so the UI can navigate immediately instead of
    waiting for local Ollama to finish the first gate.
    """
    run_id, initial_state = _persist_run(requirement_input, requirement_id)
    _RUN_EXECUTOR.submit(_invoke_until_pause_safe, run_id, initial_state)
    return {"run_id": run_id, "status": "running"}


def resume_run(run_id: str) -> dict[str, Any]:
    with PostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        checkpointer.setup()
        graph = compile_graph(checkpointer)
        result_state = graph.invoke(None, config=_config(run_id))
        snapshot = graph.get_state(_config(run_id))

    return {"run_id": run_id, "state": result_state, "next": list(snapshot.next)}


def _resume_run_safe(run_id: str) -> None:
    try:
        resume_run(run_id)
    except Exception as exc:
        logger.exception("Background resume failed for %s", run_id)
        _record_graph_failure(run_id, exc)


def _next_stage_after_gate(gate: str) -> str:
    node = GATE_TO_NEXT_NODE.get(gate)
    return node.upper() if node else "S1"


def _require_pending_review(run_id: str, gate: str) -> dict[str, Any]:
    review = db.get_latest_review(run_id, gate)
    if review is None or review["decision"] != "pending":
        raise ValueError(f"No pending review found for run {run_id} gate {gate}")
    return review


def _revise_invoke(run_id: str, as_node: Any, comment: Optional[str]) -> dict[str, Any]:
    values: dict[str, Any] = {"review_feedback": comment or ""}
    with PostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        checkpointer.setup()
        graph = compile_graph(checkpointer)
        graph.update_state(_config(run_id), values, as_node=as_node)
        result_state = graph.invoke(None, config=_config(run_id))
        snapshot = graph.get_state(_config(run_id))
    return {"run_id": run_id, "state": result_state, "next": list(snapshot.next)}


def _revise_invoke_safe(run_id: str, as_node: Any, comment: Optional[str]) -> None:
    try:
        _revise_invoke(run_id, as_node, comment)
    except Exception as exc:
        logger.exception("Background request-changes failed for %s", run_id)
        _record_graph_failure(run_id, exc)


def get_run_snapshot(run_id: str) -> Optional[dict[str, Any]]:
    with PostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        checkpointer.setup()
        graph = compile_graph(checkpointer)
        snapshot = graph.get_state(_config(run_id))
    if snapshot is None or snapshot.values == {}:
        return None
    return {"values": snapshot.values, "next": list(snapshot.next)}


def approve_gate_and_resume(run_id: str, gate: str, reviewer: str, comment: Optional[str] = None) -> dict[str, Any]:
    """CLI / smoke: record approval then wait until the graph pauses again."""
    review = _require_pending_review(run_id, gate)
    db.decide_review(str(review["review_id"]), "approved", reviewer, comment)
    return resume_run(run_id)


def approve_gate_and_resume_background(
    run_id: str, gate: str, reviewer: str, comment: Optional[str] = None
) -> dict[str, Any]:
    """HTTP POST /resume: record approval and return; graph resume runs in a worker.

    The pending-review check + decide_review stay on the request thread so a
    second approve 409s immediately. Only graph.invoke is deferred.
    """
    review = _require_pending_review(run_id, gate)
    db.decide_review(str(review["review_id"]), "approved", reviewer, comment)
    db.update_run(run_id, status="running", current_stage=_next_stage_after_gate(gate))
    _RUN_EXECUTOR.submit(_resume_run_safe, run_id)
    return {"run_id": run_id, "status": "running", "gate": gate, "decision": "approved"}


def reject_gate(
    run_id: str, gate: str, reviewer: str, comment: Optional[str] = None, decision: str = "rejected"
) -> None:
    """Hard-stop a run. Only `rejected` is accepted here; use request_changes_and_revise for revisions."""
    if decision != "rejected":
        raise ValueError("reject_gate only accepts decision='rejected'; use request_changes_and_revise for changes")
    review = db.get_latest_review(run_id, gate)
    if review is None or review["decision"] != "pending":
        raise ValueError(f"No pending review found for run {run_id} gate {gate}")
    db.decide_review(str(review["review_id"]), "rejected", reviewer, comment)
    db.update_run(run_id, status="failed", current_stage=f"{gate}_rejected")


def _prepare_request_changes(
    run_id: str, gate: str, reviewer: str, comment: Optional[str] = None
) -> Any:
    if gate not in GATE_REVISE_AS_NODE:
        raise ValueError(f"Unknown gate {gate}")
    review = _require_pending_review(run_id, gate)
    db.decide_review(str(review["review_id"]), "changes_requested", reviewer, comment)
    db.update_run(run_id, status="running", current_stage=f"{gate}_revising")
    return GATE_REVISE_AS_NODE[gate]


def request_changes_and_revise(
    run_id: str, gate: str, reviewer: str, comment: Optional[str] = None
) -> dict[str, Any]:
    """CLI / smoke: record changes_requested then wait until the same gate reopens."""
    as_node = _prepare_request_changes(run_id, gate, reviewer, comment)
    result = _revise_invoke(run_id, as_node, comment)
    result["gate"] = gate
    return result


def request_changes_and_revise_background(
    run_id: str, gate: str, reviewer: str, comment: Optional[str] = None
) -> dict[str, Any]:
    """HTTP POST /request-changes: record the decision and return; revise in a worker."""
    as_node = _prepare_request_changes(run_id, gate, reviewer, comment)
    _RUN_EXECUTOR.submit(_revise_invoke_safe, run_id, as_node, comment)
    return {
        "run_id": run_id,
        "status": "running",
        "gate": gate,
        "decision": "changes_requested",
    }
