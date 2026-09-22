"""Thin psycopg3 access layer over the Phase 0 schema
(infra/sql/001_init.sql) -- runs, artifacts, skill_executions, human_reviews.

Deliberately not an ORM: the schema is small and stable enough that raw SQL
is clearer, and it keeps this service's only dependency on the DB shape
explicit and in one place.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import psycopg
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(settings.database_url, row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def create_run(
    run_id: str,
    requirement_id: str,
    *,
    base_url: str | None = None,
    environment: str | None = None,
    branch: str | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, requirement_id, status, framework_version,
                               rulebook_version, model_version,
                               base_url, environment, branch)
            VALUES (%s, %s, 'running', %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id,
                requirement_id,
                settings.framework_version,
                settings.rulebook_version,
                settings.model_version,
                _optional_text(base_url),
                _optional_text(environment),
                _optional_text(branch),
            ),
        )


def update_run(run_id: str, *, status: str | None = None, current_stage: str | None = None) -> None:
    fields, values = [], []
    if status is not None:
        fields.append("status = %s")
        values.append(status)
    if current_stage is not None:
        fields.append("current_stage = %s")
        values.append(current_stage)
    if not fields:
        return
    fields.append("updated_at = now()")
    values.append(run_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE runs SET {', '.join(fields)} WHERE run_id = %s", values)


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM runs WHERE run_id = %s", (run_id,)).fetchone()


def next_artifact_version(run_id: str, artifact_type: str) -> int:
    """Return MAX(version)+1 for (run_id, type), or 1 if none exist yet."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version), 0) + 1 AS next_version
            FROM artifacts
            WHERE run_id = %s AND type = %s
            """,
            (run_id, artifact_type),
        ).fetchone()
        return int(row["next_version"])


def next_test_cases_batch_version(run_id: str) -> int:
    """Return next version for a full S3 test_cases rewrite of this run."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version), 0) + 1 AS next_version
            FROM test_cases
            WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()
        return int(row["next_version"])


def save_artifact(
    run_id: str,
    artifact_type: str,
    content: dict[str, Any],
    version: int | None = None,
) -> str:
    """Persist an artifact. When version is omitted, auto-bumps MAX+1 for redo safety."""
    ver = version if version is not None else next_artifact_version(run_id, artifact_type)
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO artifacts (run_id, type, version, content)
            VALUES (%s, %s, %s, %s)
            RETURNING artifact_id, version
            """,
            (run_id, artifact_type, ver, json.dumps(content)),
        ).fetchone()
        return str(row["artifact_id"])


def get_artifact_version(artifact_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT version FROM artifacts WHERE artifact_id = %s",
            (artifact_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Artifact {artifact_id} not found")
        return int(row["version"])


def save_skill_execution(
    run_id: str,
    skill: str,
    *,
    status: str,
    model: str,
    output_ref: str | None = None,
    escalation_reason: str | None = None,
) -> str:
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO skill_executions (run_id, skill, model, status, output_ref, escalation_reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING execution_id
            """,
            (run_id, skill, model, status, output_ref, escalation_reason),
        ).fetchone()
        return str(row["execution_id"])


def create_pending_review(
    run_id: str,
    gate: str,
    artifact_id: str,
    artifact_version: int | None = None,
) -> str:
    ver = artifact_version if artifact_version is not None else get_artifact_version(artifact_id)
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO human_reviews (run_id, gate, artifact_id, artifact_version, decision)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING review_id
            """,
            (run_id, gate, artifact_id, ver),
        ).fetchone()
        return str(row["review_id"])


def get_latest_review(run_id: str, gate: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM human_reviews
            WHERE run_id = %s AND gate = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (run_id, gate),
        ).fetchone()


def decide_review(review_id: str, decision: str, reviewer: str, comment: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE human_reviews
            SET decision = %s, reviewer = %s, comment = %s, decided_at = now()
            WHERE review_id = %s
            """,
            (decision, reviewer, comment, review_id),
        )


def get_artifact(artifact_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM artifacts WHERE artifact_id = %s", (artifact_id,)).fetchone()
