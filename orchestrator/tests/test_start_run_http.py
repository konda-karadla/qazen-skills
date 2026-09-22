"""HTTP POST /runs returns immediately; graph invoke runs in the background."""
from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
)

from fastapi.testclient import TestClient

from app import runner
from app.api import app


def test_post_runs_returns_without_waiting(monkeypatch):
    run_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    initial = {
        "run_id": run_id,
        "requirement_id": run_id,
        "raw_input": {"raw": "Users must log in."},
        "artifact_ids": {},
    }
    submitted: list[tuple] = []

    monkeypatch.setattr(
        runner,
        "_persist_run",
        lambda requirement_input, requirement_id=None: (run_id, initial),
    )
    monkeypatch.setattr(
        runner._RUN_EXECUTOR,
        "submit",
        lambda fn, *args: submitted.append((fn, args)),
    )

    client = TestClient(app)
    res = client.post("/runs", json={"input": {"raw": "Users must log in."}})
    assert res.status_code == 200
    body = res.json()
    assert body["run_id"] == run_id
    assert body["status"] == "running"
    assert "state" not in body
    assert submitted
    assert submitted[0][0] is runner._invoke_until_pause_safe
    assert submitted[0][1][0] == run_id


def test_post_resume_returns_without_waiting(monkeypatch):
    run_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    submitted: list[tuple] = []
    updates: list[tuple] = []

    monkeypatch.setattr(
        runner,
        "_require_pending_review",
        lambda rid, gate: {"review_id": "rev-1", "decision": "pending"},
    )
    monkeypatch.setattr(runner.db, "decide_review", lambda *args: None)
    monkeypatch.setattr(
        runner.db,
        "update_run",
        lambda rid, **kwargs: updates.append((rid, kwargs)),
    )
    monkeypatch.setattr(
        runner._RUN_EXECUTOR,
        "submit",
        lambda fn, *args: submitted.append((fn, args)),
    )

    client = TestClient(app)
    res = client.post(
        f"/runs/{run_id}/resume",
        json={"gate": "H1", "reviewer": "qa-lead", "comment": "ok"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "run_id": run_id,
        "status": "running",
        "gate": "H1",
        "decision": "approved",
    }
    assert "state" not in body
    assert updates == [(run_id, {"status": "running", "current_stage": "S3"})]
    assert submitted[0][0] is runner._resume_run_safe
    assert submitted[0][1] == (run_id,)


def test_post_request_changes_returns_without_waiting(monkeypatch):
    run_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    submitted: list[tuple] = []

    monkeypatch.setattr(
        runner,
        "_require_pending_review",
        lambda rid, gate: {"review_id": "rev-1", "decision": "pending"},
    )
    monkeypatch.setattr(runner.db, "decide_review", lambda *args: None)
    monkeypatch.setattr(runner.db, "update_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner._RUN_EXECUTOR,
        "submit",
        lambda fn, *args: submitted.append((fn, args)),
    )

    client = TestClient(app)
    res = client.post(
        f"/runs/{run_id}/request-changes",
        json={"gate": "H1", "reviewer": "qa-lead", "comment": "clarify"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "running"
    assert body["decision"] == "changes_requested"
    assert "state" not in body
    assert submitted[0][0] is runner._revise_invoke_safe
    assert submitted[0][1][0] == run_id


def test_resume_run_safe_marks_run_failed(monkeypatch):
    updates: list[tuple] = []

    def boom(run_id: str) -> dict:
        raise RuntimeError("gateway down")

    monkeypatch.setattr(runner, "resume_run", boom)
    monkeypatch.setattr(
        runner.db,
        "update_run",
        lambda run_id, **kwargs: updates.append((run_id, kwargs)),
    )

    runner._resume_run_safe("run-1")
    assert updates == [("run-1", {"status": "failed"})]


def test_invoke_until_pause_safe_marks_run_failed(monkeypatch):
    updates: list[tuple] = []

    def boom(run_id: str, initial_state: dict) -> dict:
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(runner, "_invoke_until_pause", boom)
    monkeypatch.setattr(
        runner.db,
        "update_run",
        lambda run_id, **kwargs: updates.append((run_id, kwargs)),
    )

    result = runner._invoke_until_pause_safe("run-1", {"run_id": "run-1"})
    assert result is None
    assert updates == [("run-1", {"status": "failed"})]
