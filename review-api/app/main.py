"""Human Review API for gates H1-H5, plus QAZen Web UI.

Read endpoints implement docs/ui-api-contract.md (Phase 2).
Mutations proxy to Orchestrator — Review API does not write run/gate state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from uuid import UUID
import re

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from app import db
from app.config import settings
from app.pipeline import ARTIFACT_TYPE_TO_NODE
from app.run_state import derive_run_ui_state

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

_DEFAULT_TIMEOUT_SECONDS = 60.0

_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"


def _looks_like_llm_quota_or_auth(reason: str) -> bool:
    lower = reason.lower()
    needles = (
        "429",
        "rate limit",
        "quota",
        "token",
        "unauthorized",
        "401",
        "403",
        "invalid api key",
        "authentication",
        "insufficient_quota",
    )
    return any(n in lower for n in needles)


app = FastAPI(
    title="QAZen Review API",
    description="Human-in-the-loop API and QAZen Web UI for gates H1-H5.",
    version="0.5.0",
)


class DecisionRequest(BaseModel):
    reviewer: str
    comment: Optional[str] = None


class StartRunRequest(BaseModel):
    input: dict[str, Any]
    requirement_id: Optional[str] = None


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _serialize_review_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_id": str(row["review_id"]),
        "run_id": str(row["run_id"]),
        "gate": row.get("gate"),
        "artifact_id": str(row["artifact_id"]) if row.get("artifact_id") else None,
        "artifact_version": row.get("artifact_version"),
        "decision": row.get("decision"),
        "reviewer": row.get("reviewer"),
        "comment": row.get("comment"),
        "created_at": _iso(row.get("created_at")),
        "decided_at": _iso(row.get("decided_at")),
    }


def _build_ui_state_for_run(run_id: str, run: dict[str, Any], pending_gate: Optional[str]) -> dict[str, Any]:
    artifacts = [{"type": a["type"], "version": a["version"]} for a in db.list_artifacts(run_id)]
    reviews = [
        {"gate": r["gate"], "decision": r["decision"]} for r in db.get_review_history(run_id)
    ]
    return derive_run_ui_state(
        status=run.get("status") or "pending",
        current_stage=run.get("current_stage"),
        pending_gate=pending_gate,
        artifacts=artifacts,
        reviews=reviews,
    )


def _run_list_item(row: dict[str, Any], *, include_ui_state: bool = False) -> dict[str, Any]:
    run_id = str(row["run_id"])
    pending = row.get("pending_gate")
    meta = db.passthrough_metadata_for_run(row, run_id)
    item: dict[str, Any] = {
        "run_id": run_id,
        "requirement_id": row.get("requirement_id"),
        "requirement_summary": db.requirement_summary_for_run(run_id),
        "status": row.get("status"),
        "current_stage": row.get("current_stage"),
        "pending_gate": pending,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }
    item["environment"] = meta.get("environment")
    item["branch"] = meta.get("branch")
    item["base_url"] = meta.get("base_url")
    if include_ui_state:
        item["ui_state"] = derive_run_ui_state(
            status=row.get("status") or "pending",
            current_stage=row.get("current_stage"),
            pending_gate=pending,
            artifacts=[{"type": a["type"]} for a in db.list_artifacts(run_id)],
            reviews=[
                {"gate": r["gate"], "decision": r["decision"]}
                for r in db.get_review_history(run_id)
            ],
        )
    return item


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ui": "/ui/", "version": "0.5.0"}


# ---------------------------------------------------------------------------
# Dashboard / integrations / knowledge / pending reviews
# ---------------------------------------------------------------------------


@app.get("/dashboard/summary")
def dashboard_summary() -> dict[str, Any]:
    by_status = db.count_runs_by_status()
    stats = db.execution_stats()
    pass_rate = stats.get("pass_rate")
    return {
        "active_runs": int(by_status.get("running", 0)) + int(by_status.get("paused", 0)),
        "pending_reviews": db.count_pending_reviews(),
        "tests_executed": stats["tests_executed"],
        "failed_tests": stats["failed"],
        "runs_completed": int(by_status.get("completed", 0)),
        "pass_rate": pass_rate,
        "pass_rate_display": f"{pass_rate * 100:.1f}%" if pass_rate is not None else None,
        "pass_rate_basis": "Based on classified executable results",
        "pass_rate_note": (
            "Unclassified failures are excluded from the denominator (S9 rules)."
        ),
    }


@app.get("/reviews/pending")
def pending_reviews(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    rows = db.list_pending_reviews(limit=limit)
    items = []
    for row in rows:
        run_id = str(row["run_id"])
        artifacts = db.list_artifacts(run_id)
        items.append(
            {
                "review_id": str(row["review_id"]),
                "run_id": run_id,
                "gate": row.get("gate"),
                "requirement_summary": db.requirement_summary_for_run(run_id),
                "waiting_since": _iso(row.get("waiting_since")),
                "artifact_version": row.get("artifact_version"),
                "artifact_count": len(artifacts),
                "run_status": row.get("run_status"),
                "current_stage": row.get("current_stage"),
            }
        )
    return {"reviews": items}


@app.get("/reviews/recent")
def recent_reviews(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    rows = db.list_recent_reviews(limit=limit)
    items = []
    for row in rows:
        run_id = str(row["run_id"])
        items.append(
            {
                "review_id": str(row["review_id"]),
                "run_id": run_id,
                "gate": row.get("gate"),
                "decision": row.get("decision"),
                "reviewer": row.get("reviewer"),
                "comment": row.get("comment"),
                "requirement_summary": db.requirement_summary_for_run(run_id),
                "artifact_version": row.get("artifact_version"),
                "created_at": _iso(row.get("created_at")),
                "decided_at": _iso(row.get("decided_at")),
                "run_status": row.get("run_status"),
                "current_stage": row.get("current_stage"),
            }
        )
    return {"reviews": items}


@app.get("/knowledge")
def knowledge(limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    rows = db.list_knowledge_items(limit=limit)
    return {
        "writable": False,
        "message": "Human-confirmed rules will appear here. Application writes are not wired yet.",
        "items": [
            {
                "knowledge_id": str(r["knowledge_id"]),
                "domain": r.get("domain"),
                "rule": r.get("rule"),
                "status": r.get("status"),
                "source": r.get("source"),
                "supersedes": str(r["supersedes"]) if r.get("supersedes") else None,
                "created_at": _iso(r.get("created_at")),
            }
            for r in rows
        ],
    }


@app.get("/integrations/status")
def integrations_status() -> dict[str, Any]:
    ci_mode = (settings.ci_gate_mode or "mock").lower()
    if ci_mode == "http" and settings.ci_gate_endpoint:
        ci_label = "Configured"
        ci_detail = "HTTP gate endpoint set; production Jenkins credentials are not claimed."
    elif ci_mode == "http":
        ci_label = "Not Configured"
        ci_detail = "CI_GATE_MODE=http but CI_GATE_ENDPOINT is empty."
    else:
        ci_label = "Mock"
        ci_detail = "CI_GATE_MODE=mock — local evaluation only, no HTTP push."

    provider = settings.llm_provider or settings.llm_profile or "unknown"
    if (settings.llm_provider or "").lower() == "mock":
        llm_label = "Mock"
    else:
        llm_label = "Configured"

    llm_gateway: dict[str, Any] = {"label": llm_label, "provider": provider}
    try:
        health = httpx.get(f"{settings.llm_gateway_url}/health", timeout=3.0)
        if health.status_code < 400:
            body = health.json()
            llm_gateway["label"] = "Connected"
            llm_gateway["provider"] = body.get("provider") or provider
            llm_gateway["llm_profile"] = body.get("llm_profile")
            llm_gateway["openai_model"] = body.get("openai_model")
            llm_gateway["openai_base_url"] = body.get("openai_base_url")
        else:
            llm_gateway["label"] = "Not Configured"
            llm_gateway["detail"] = f"Gateway /health HTTP {health.status_code}"
    except Exception as exc:  # noqa: BLE001 — surface connectivity, not crash Settings
        llm_gateway["label"] = "Not Configured"
        llm_gateway["detail"] = f"Gateway unreachable ({type(exc).__name__})"

    minio_label = "Configured" if settings.minio_endpoint else "Not Configured"

    return {
        "ci": {"label": ci_label, "mode": ci_mode, "detail": ci_detail},
        "llm_gateway": llm_gateway,
        "minio": {"label": minio_label},
        "playwright": {
            "label": "Configured" if settings.s6_execution_mode else "Not Configured",
            "runner": "playwright_test",
            "mode": settings.s6_execution_mode,
            "mcp": False,
        },
        "knowledge_base": {"label": "Not Wired", "writable": False},
        "flaky_history": {
            "available": False,
            "message": "No historical flaky-test data loaded",
        },
        "stop_run": {
            "available": False,
            "message": "Cancellation not available yet",
        },
        "llm_setup_hint": (
            "Set LLM_PROFILE / OPENAI_API_KEY (or profile-specific keys) in the repo-root "
            ".env file, then restart the LLM Gateway on :8000. Keys are never accepted "
            "through this UI."
        ),
    }


# ---------------------------------------------------------------------------
# Cross-run test cases / scripts / executions (Phase 6)
# ---------------------------------------------------------------------------


def _serialize_test_case(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_case_id": r["test_case_id"],
        "run_id": str(r["run_id"]),
        "version": int(r["version"]),
        "source_requirement_id": r.get("source_requirement_id"),
        "layer": r.get("layer"),
        "obligation": r.get("obligation"),
        "expected_result": r.get("expected_result"),
        "expected_result_basis": r.get("expected_result_basis"),
        "duplicate_of": r.get("duplicate_of"),
        "last_execution_status": r.get("last_execution_status"),
        "created_at": _iso(r.get("created_at")),
    }


def _serialize_execution(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": str(r["execution_id"]),
        "run_id": str(r["run_id"]),
        "test_case_id": r.get("test_case_id"),
        "correlation_id": r.get("correlation_id"),
        "status": r.get("status"),
        "classification": r.get("classification"),
        "retry_attempts": r.get("retry_attempts"),
        "evidence_manifest": r.get("evidence_manifest"),
        "created_at": _iso(r.get("created_at")),
    }


@app.get("/test-cases")
def list_test_cases(
    limit: int = Query(100, ge=1, le=500),
    run_id: Optional[UUID] = None,
) -> dict[str, Any]:
    rid = str(run_id) if run_id else None
    rows = db.list_test_cases_cross_run(limit=limit, run_id=rid)
    return {"test_cases": [_serialize_test_case(r) for r in rows], "limit": limit}


@app.get("/scripts")
def list_scripts(
    limit: int = Query(100, ge=1, le=500),
    run_id: Optional[UUID] = None,
) -> dict[str, Any]:
    rid = str(run_id) if run_id else None
    rows = db.list_scripts_cross_run(limit=limit, run_id=rid)
    scripts = []
    for r in rows:
        item = {
            "script_id": r.get("script_id"),
            "run_id": r.get("run_id"),
            "test_case_id": r.get("test_case_id"),
            "file_name": r.get("file_name"),
            "framework": r.get("framework") or "playwright",
            "version": r.get("version"),
            "source": r.get("source"),
            "spec_path": r.get("spec_path"),
            "artifact_id": r.get("artifact_id"),
            "created_at": _iso(r.get("created_at")),
        }
        scripts.append(item)
    return {"scripts": scripts, "limit": limit}


@app.get("/executions")
def list_executions(
    limit: int = Query(100, ge=1, le=500),
    run_id: Optional[UUID] = None,
) -> dict[str, Any]:
    rid = str(run_id) if run_id else None
    rows = db.list_test_executions_cross_run(limit=limit, run_id=rid)
    return {"executions": [_serialize_execution(r) for r in rows], "limit": limit}


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


@app.post("/runs")
def start_run(request: StartRunRequest) -> dict[str, Any]:
    """Proxy to Orchestrator POST /runs — Review API does not write run state.

    Orchestrator returns `{run_id, status}` immediately; S1–S2 continue in the
    background. `input.raw` is required by the pipeline. Optional metadata keys
    (requirement_type, environment, base_url, branch, labels) are passthrough.
    """
    if not isinstance(request.input, dict) or not str(request.input.get("raw", "")).strip():
        raise HTTPException(status_code=400, detail="input.raw is required")
    body: dict[str, Any] = {"input": request.input}
    if request.requirement_id is not None:
        body["requirement_id"] = request.requirement_id
    response = httpx.post(
        f"{settings.orchestrator_url}/runs",
        json=body,
        timeout=_DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    stage: Optional[str] = None,
    include_ui_state: bool = False,
) -> dict[str, Any]:
    rows, total = db.list_runs(limit=limit, offset=offset, status=status, stage=stage)
    return {
        "runs": [_run_list_item(r, include_ui_state=include_ui_state) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/runs/{run_id}")
def get_run_detail(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    run = db.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")
    pending = db.get_pending_review(rid)
    pending_gate = pending["gate"] if pending else None
    meta = db.passthrough_metadata_for_run(run, rid)
    failure = db.latest_skill_failure(rid)
    last_skill_error = None
    if failure and failure.get("escalation_reason"):
        last_skill_error = {
            "skill": failure.get("skill"),
            "status": failure.get("status"),
            "model": failure.get("model"),
            "reason": failure.get("escalation_reason"),
            "created_at": _iso(failure.get("created_at")),
            "is_quota_or_auth": _looks_like_llm_quota_or_auth(str(failure.get("escalation_reason") or "")),
        }
    return {
        "run_id": rid,
        "requirement_id": run.get("requirement_id"),
        "status": run.get("status"),
        "current_stage": run.get("current_stage"),
        "pending_gate": pending_gate,
        "requirement_summary": db.requirement_summary_for_run(rid),
        "raw_input": meta or None,
        "environment": meta.get("environment"),
        "branch": meta.get("branch"),
        "base_url": meta.get("base_url"),
        "framework_version": run.get("framework_version"),
        "rulebook_version": run.get("rulebook_version"),
        "model_version": run.get("model_version"),
        "created_at": _iso(run.get("created_at")),
        "updated_at": _iso(run.get("updated_at")),
        "ui_state": _build_ui_state_for_run(rid, run, pending_gate),
        "last_skill_error": last_skill_error,
    }


@app.get("/runs/{run_id}/artifacts")
def list_run_artifacts(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    if db.get_run(rid) is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")
    rows = db.list_artifacts(rid)
    # Need content for compiled file names — fetch lightly
    artifacts = []
    for row in rows:
        full = db.get_artifact(rid, str(row["artifact_id"]))
        artifacts.append(db.serialize_artifact_row(full or row))
    return {"run_id": rid, "artifacts": artifacts}


@app.get("/runs/{run_id}/artifacts/{artifact_id}")
def get_run_artifact(run_id: UUID, artifact_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    aid = str(artifact_id)
    row = db.get_artifact(rid, aid)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Artifact {aid} not found for run {rid}")
    return {
        "artifact_id": aid,
        "run_id": rid,
        "type": row["type"],
        "stage": ARTIFACT_TYPE_TO_NODE.get(row["type"], row["type"]),
        "version": int(row["version"]),
        "content": row.get("content"),
        "storage_uri": row.get("storage_uri"),
        "created_at": _iso(row.get("created_at")),
    }


@app.get("/runs/{run_id}/timeline")
def get_run_timeline(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    run = db.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")

    events: list[dict[str, Any]] = []
    events.append(
        {
            "at": _iso(run.get("created_at")),
            "kind": "run_created",
            "stage": None,
            "title": "Run created",
            "detail": f"requirement_id={run.get('requirement_id')}",
            "actor": None,
            "decision": None,
            "artifact_version": None,
        }
    )

    for se in db.list_skill_executions(rid):
        events.append(
            {
                "at": _iso(se.get("created_at")),
                "kind": "skill",
                "stage": se.get("skill"),
                "title": f"{se.get('skill')} {se.get('status')}",
                "detail": se.get("escalation_reason"),
                "actor": se.get("model"),
                "decision": None,
                "artifact_version": None,
            }
        )

    for art in db.list_artifacts(rid):
        stage = ARTIFACT_TYPE_TO_NODE.get(art["type"], art["type"])
        kind = "compile" if art["type"] == "s5_compiled_playwright" else "stage"
        events.append(
            {
                "at": _iso(art.get("created_at")),
                "kind": kind,
                "stage": stage,
                "title": f"{stage} artifact v{art['version']}",
                "detail": art["type"],
                "actor": None,
                "decision": None,
                "artifact_version": int(art["version"]),
            }
        )

    for rev in db.get_review_history(rid):
        decision = rev.get("decision")
        title = f"{rev.get('gate')} {decision}"
        if decision == "pending":
            title = f"{rev.get('gate')} pending review"
        events.append(
            {
                "at": _iso(rev.get("decided_at") or rev.get("created_at")),
                "kind": "review",
                "stage": rev.get("gate"),
                "title": title,
                "detail": rev.get("comment"),
                "actor": rev.get("reviewer"),
                "decision": decision,
                "artifact_version": rev.get("artifact_version"),
            }
        )

    events.sort(key=lambda e: e.get("at") or "")
    return {"run_id": rid, "events": events}


@app.get("/runs/{run_id}/lineage")
def get_run_lineage(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    run = db.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")

    nodes: list[dict[str, Any]] = [
        {
            "node_id": "Requirement",
            "label": "Requirement",
            "artifact_type": None,
            "version": None,
            "status": "source",
        }
    ]
    # Latest version per artifact type in pipeline order preference
    latest_by_type: dict[str, dict[str, Any]] = {}
    for art in db.list_artifacts(rid):
        t = art["type"]
        prev = latest_by_type.get(t)
        if prev is None or int(art["version"]) >= int(prev["version"]):
            latest_by_type[t] = art

    order = [
        "s1_normalized_requirement",
        "s2_ambiguity_analysis",
        "s3_test_cases",
        "s4_test_data",
        "s5_automation_model",
        "s5_compiled_playwright",
        "s6_execution_result",
        "s7_classification",
        "s8_boundary_scan",
        "s9_report",
        "s10_release_summary",
        "s11_cicd_status",
    ]
    for atype in order:
        art = latest_by_type.get(atype)
        if not art:
            continue
        nodes.append(
            {
                "node_id": ARTIFACT_TYPE_TO_NODE.get(atype, atype),
                "label": ARTIFACT_TYPE_TO_NODE.get(atype, atype),
                "artifact_type": atype,
                "version": int(art["version"]),
                "status": db.artifact_list_status(rid, atype, int(art["version"])),
            }
        )
    return {"run_id": rid, "nodes": nodes}


@app.get("/runs/{run_id}/test-cases")
def get_run_test_cases(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    if db.get_run(rid) is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")
    rows = db.list_test_cases(rid)
    return {
        "run_id": rid,
        "test_cases": [_serialize_test_case({**r, "run_id": rid}) for r in rows],
    }


@app.get("/runs/{run_id}/scripts")
def get_run_scripts(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    if db.get_run(rid) is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")
    return {"run_id": rid, "scripts": db.scripts_from_compiled(rid)}


@app.get("/runs/{run_id}/executions")
def get_run_executions(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    if db.get_run(rid) is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")
    rows = db.list_test_executions(rid)
    return {
        "run_id": rid,
        "executions": [_serialize_execution({**r, "run_id": rid}) for r in rows],
    }


@app.get("/runs/{run_id}/review")
def get_review(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    run = db.get_run(rid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")

    pending = db.get_pending_review(rid)
    if pending is None:
        return {
            "run_id": rid,
            "run_status": run["status"],
            "current_stage": run["current_stage"],
            "pending_gate": None,
            "message": "No gate is currently awaiting review for this run.",
            "ui_state": _build_ui_state_for_run(rid, run, None),
        }

    gate = pending["gate"]
    evidence = {}
    for artifact_type in db.GATE_CONTEXT_ARTIFACT_TYPES.get(gate, []):
        artifact = db.get_latest_artifact_by_type(rid, artifact_type)
        if artifact:
            evidence[artifact_type] = artifact["content"]

    # H3: each Compile / S5 invoke is one artifact version; surface every unique file + model.
    if gate == "H3":
        compiled_scripts = db.scripts_from_compiled(rid)
        if compiled_scripts:
            evidence["compiled_scripts"] = [
                {
                    "file_name": s.get("file_name"),
                    "test_case_id": s.get("test_case_id"),
                    "script_id": s.get("script_id"),
                    "version": s.get("version"),
                    "source": s.get("source"),
                    "spec_path": s.get("spec_path"),
                }
                for s in compiled_scripts
            ]
        automation_models = db.automation_models_from_s5(rid)
        if automation_models:
            evidence["automation_models"] = automation_models

    return {
        "run_id": rid,
        "run_status": run["status"],
        "current_stage": run["current_stage"],
        "pending_gate": gate,
        "artifact_version": pending["artifact_version"],
        "review_id": str(pending["review_id"]),
        "evidence": evidence,
        "ui_state": _build_ui_state_for_run(rid, run, gate),
    }


@app.get("/runs/{run_id}/history")
def get_history(run_id: UUID) -> dict[str, Any]:
    rid = str(run_id)
    if db.get_run(rid) is None:
        raise HTTPException(status_code=404, detail=f"Run {rid} not found")
    return {
        "run_id": rid,
        "history": [_serialize_review_row(r) for r in db.get_review_history(rid)],
    }


def _require_pending_gate(run_id: str) -> str:
    pending = db.get_pending_review(run_id)
    if pending is None:
        raise HTTPException(status_code=409, detail=f"No pending gate for run {run_id}")
    return pending["gate"]


@app.post("/runs/{run_id}/approve")
def approve(run_id: UUID, request: DecisionRequest) -> dict[str, Any]:
    rid = str(run_id)
    gate = _require_pending_gate(rid)
    response = httpx.post(
        f"{settings.orchestrator_url}/runs/{rid}/resume",
        json={"gate": gate, "reviewer": request.reviewer, "comment": request.comment},
        timeout=_DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.post("/runs/{run_id}/reject")
def reject(run_id: UUID, request: DecisionRequest) -> dict[str, Any]:
    rid = str(run_id)
    gate = _require_pending_gate(rid)
    response = httpx.post(
        f"{settings.orchestrator_url}/runs/{rid}/reject",
        json={
            "gate": gate,
            "reviewer": request.reviewer,
            "comment": request.comment,
            "decision": "rejected",
        },
        timeout=_DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.post("/runs/{run_id}/request-changes")
def request_changes(run_id: UUID, request: DecisionRequest) -> dict[str, Any]:
    rid = str(run_id)
    gate = _require_pending_gate(rid)
    response = httpx.post(
        f"{settings.orchestrator_url}/runs/{rid}/request-changes",
        json={"gate": gate, "reviewer": request.reviewer, "comment": request.comment},
        timeout=_DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


# ---------------------------------------------------------------------------
# Skills (read-only skill.md viewer)
# ---------------------------------------------------------------------------


@app.get("/skills")
def list_skills() -> dict[str, Any]:
    if not _SKILLS_ROOT.is_dir():
        return {"skills": [], "root": str(_SKILLS_ROOT)}
    skills: list[dict[str, Any]] = []
    for path in sorted(_SKILLS_ROOT.iterdir()):
        if not path.is_dir():
            continue
        skill_md = path / "skill.md"
        if skill_md.is_file():
            skills.append({"id": path.name, "path": f"skills/{path.name}/skill.md"})
    skills.sort(key=lambda s: int(re.sub(r"\D", "", s["id"]) or "0"))
    return {"skills": skills}


@app.get("/skills/{skill_id}")
def get_skill(skill_id: str) -> dict[str, Any]:
    sid = skill_id.strip().upper()
    if not re.fullmatch(r"S([1-9]|1[0-1])", sid):
        raise HTTPException(status_code=400, detail="skill_id must be S1..S11")
    skill_md = _SKILLS_ROOT / sid / "skill.md"
    if not skill_md.is_file():
        raise HTTPException(status_code=404, detail=f"Skill {sid} not found")
    return {
        "id": sid,
        "path": f"skills/{sid}/skill.md",
        "markdown": skill_md.read_text(encoding="utf-8"),
    }


# ---------------------------------------------------------------------------
# SPA
# ---------------------------------------------------------------------------


def _spa_index() -> FileResponse:
    index = _STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="UI not built. Run: cd web && npm run build")
    return FileResponse(index)


@app.get("/ui")
@app.get("/ui/")
def ui_root() -> FileResponse:
    return _spa_index()


@app.get("/ui/{full_path:path}")
def ui_spa(full_path: str) -> FileResponse:
    if not _STATIC_DIR.is_dir():
        raise HTTPException(status_code=404, detail="UI static directory missing")
    candidate = (_STATIC_DIR / full_path).resolve()
    static_root = _STATIC_DIR.resolve()
    if not str(candidate).startswith(str(static_root)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if candidate.is_file():
        return FileResponse(candidate)
    return _spa_index()
