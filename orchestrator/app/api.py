"""Minimal Orchestrator HTTP surface -- manual trigger for v1 (CLI or this
API), designed so a Jira/webhook trigger can call the same start path
without touching the graph. HTTP POST /runs persists the run and returns
immediately; S1–S2 run on a worker thread. CLI start-run still waits until
the first gate. HTTP POST /resume and /request-changes record the decision and
return immediately; graph resume/revise runs on a worker thread.
The Review API never talks to Postgres/LangGraph directly.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import runner

app = FastAPI(title="QAZen Orchestrator", version="0.1.0")


class StartRunRequest(BaseModel):
    input: dict[str, Any]
    requirement_id: Optional[str] = None


class ResumeRequest(BaseModel):
    gate: str
    reviewer: str
    comment: Optional[str] = None


class RejectRequest(BaseModel):
    gate: str
    reviewer: str
    comment: Optional[str] = None
    decision: str = "rejected"


class RequestChangesRequest(BaseModel):
    gate: str
    reviewer: str
    comment: Optional[str] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/runs")
def create_run(request: StartRunRequest) -> dict:
    return runner.start_run_background(request.input, requirement_id=request.requirement_id)


@app.get("/runs/{run_id}")
def read_run(run_id: str) -> dict:
    snapshot = runner.get_run_snapshot(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return snapshot


@app.post("/runs/{run_id}/resume")
def resume(run_id: str, request: ResumeRequest) -> dict:
    try:
        return runner.approve_gate_and_resume_background(
            run_id, request.gate, request.reviewer, request.comment
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/runs/{run_id}/reject")
def reject(run_id: str, request: RejectRequest) -> dict:
    if request.decision != "rejected":
        raise HTTPException(
            status_code=400,
            detail="Use POST /runs/{run_id}/request-changes for changes_requested",
        )
    try:
        runner.reject_gate(run_id, request.gate, request.reviewer, request.comment, "rejected")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run_id": run_id, "gate": request.gate, "decision": "rejected"}


@app.post("/runs/{run_id}/request-changes")
def request_changes(run_id: str, request: RequestChangesRequest) -> dict:
    try:
        return runner.request_changes_and_revise_background(
            run_id, request.gate, request.reviewer, request.comment
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
