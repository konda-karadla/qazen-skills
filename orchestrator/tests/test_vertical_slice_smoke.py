"""Phase 0–3 acceptance test: the full vertical slice
S1->S2->[H1]->S3->S4->[H2]->S5->[H3]->S6->S7->S8->S9->[H4]->S10->[H5]->S11
runs end to end against a real Postgres checkpointer and the LLM Gateway's
mock provider, pausing at exactly H1/H2/H3/H4/H5 and nowhere else, and
resuming only on explicit gate approval.

Requires: infra docker compose up (Postgres reachable), LLM Gateway running
with LLM_PROVIDER=mock on LLM_GATEWAY_URL (see app.config defaults).

S6 stays on the gateway mock fixture here (S6_EXECUTION_MODE=mock) so CI stays
offline; real Playwright + MinIO is exercised separately.
"""
import os

import pytest

# Must be set before app.config / graph import paths that read settings.
os.environ["S6_EXECUTION_MODE"] = "mock"
os.environ.setdefault("CI_GATE_MODE", "mock")

from app import db
from app.runner import (
    approve_gate_and_resume,
    reject_gate,
    request_changes_and_revise,
    start_run,
)


def test_vertical_slice_pauses_at_each_gate_and_completes():
    result = start_run({"raw": "Demo BRD: users must log in with valid credentials and reach the dashboard."})
    run_id = result["run_id"]
    assert result["next"] == ["s3"]

    result = approve_gate_and_resume(run_id, "H1", reviewer="qa-lead")
    assert result["next"] == ["s5"]

    result = approve_gate_and_resume(run_id, "H2", reviewer="qa-lead")
    assert result["next"] == ["s6"]

    result = approve_gate_and_resume(run_id, "H3", reviewer="qa-engineer")
    assert result["next"] == ["s10"]
    s9 = result["state"]["s9_output"]
    assert s9["aggregate_metrics"]["passed"] == 1
    assert "Execution Summary" in s9["human_readable_summary"]
    assert result["state"].get("s7_output") is not None
    assert result["state"].get("s8_output") is not None
    assert result["state"]["s8_output"]["clean_confirmation"]

    result = approve_gate_and_resume(run_id, "H4", reviewer="qa-lead")
    assert result["next"] == ["s11"]
    s10 = result["state"]["s10_output"]
    assert s10["pass_fail_summary"]["passed"] == 1
    assert "factual_narrative" in s10
    assert "recommend" not in s10["factual_narrative"].lower()

    result = approve_gate_and_resume(run_id, "H5", reviewer="release-owner")
    assert result["next"] == []
    s11 = result["state"]["s11_output"]
    assert s11["status_pushed"] in ("pass", "fail", "blocked")
    assert s11["push_mode"] == "mock"
    assert s11["linked_summary"]["artifact_type"] == "s10_release_summary"


def test_rejecting_a_gate_halts_the_run_without_advancing():
    result = start_run({"raw": "Demo BRD: users must log in with valid credentials and reach the dashboard."})
    run_id = result["run_id"]
    assert result["next"] == ["s3"]

    reject_gate(run_id, "H1", reviewer="qa-lead", comment="ambiguity unresolved")

    with pytest.raises(ValueError):
        # A rejected gate has no pending review left -- cannot approve-and-resume it.
        approve_gate_and_resume(run_id, "H1", reviewer="qa-lead")


def test_request_changes_at_h1_revises_and_pauses_again():
    result = start_run({"raw": "Demo BRD: users must log in with valid credentials and reach the dashboard."})
    run_id = result["run_id"]
    assert result["next"] == ["s3"]
    first_pending = db.get_latest_review(run_id, "H1")
    assert first_pending is not None and first_pending["decision"] == "pending"
    first_review_id = str(first_pending["review_id"])

    result = request_changes_and_revise(
        run_id, "H1", reviewer="qa-lead", comment="Clarify password rules"
    )
    assert result["next"] == ["s3"]
    assert result["state"].get("review_feedback") == "Clarify password rules"

    second_pending = db.get_latest_review(run_id, "H1")
    assert second_pending is not None
    assert second_pending["decision"] == "pending"
    assert str(second_pending["review_id"]) != first_review_id
    assert second_pending["artifact_version"] >= 2

    # Can still approve after revision and advance past H1.
    result = approve_gate_and_resume(run_id, "H1", reviewer="qa-lead")
    assert result["next"] == ["s5"]
