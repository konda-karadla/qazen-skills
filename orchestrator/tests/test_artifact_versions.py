"""Unit tests for artifact / test_cases version bumping (revision-loop safety)."""
from __future__ import annotations

import os
import uuid

import pytest

os.environ.setdefault(
    "DATABASE_URL", "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
)

from app import db  # noqa: E402


@pytest.fixture
def run_id():
    rid = str(uuid.uuid4())
    db.create_run(rid, requirement_id=rid)
    return rid


def test_save_artifact_auto_bumps_version(run_id):
    assert db.next_artifact_version(run_id, "s1_normalized_requirement") == 1
    id1 = db.save_artifact(run_id, "s1_normalized_requirement", {"v": 1})
    assert db.get_artifact_version(id1) == 1
    assert db.next_artifact_version(run_id, "s1_normalized_requirement") == 2
    id2 = db.save_artifact(run_id, "s1_normalized_requirement", {"v": 2})
    assert db.get_artifact_version(id2) == 2
    assert id1 != id2


def test_create_pending_review_uses_artifact_version(run_id):
    a1 = db.save_artifact(run_id, "s2_ambiguity_analysis", {"n": 1})
    r1 = db.create_pending_review(run_id, "H1", a1)
    row1 = db.get_latest_review(run_id, "H1")
    assert str(row1["review_id"]) == r1
    assert row1["artifact_version"] == 1

    db.decide_review(r1, "changes_requested", "qa-lead", "fix tags")
    a2 = db.save_artifact(run_id, "s2_ambiguity_analysis", {"n": 2})
    r2 = db.create_pending_review(run_id, "H1", a2)
    row2 = db.get_latest_review(run_id, "H1")
    assert str(row2["review_id"]) == r2
    assert row2["decision"] == "pending"
    assert row2["artifact_version"] == 2


def test_next_test_cases_batch_version(run_id):
    assert db.next_test_cases_batch_version(run_id) == 1
    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO test_cases (test_case_id, run_id, version, source_requirement_id, layer,
                                     obligation, expected_result, expected_result_basis, duplicate_of)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            ("TC-001", run_id, 1, "REQ-1", "UI", "ob", "exp", "basis", None),
        )
    assert db.next_test_cases_batch_version(run_id) == 2
