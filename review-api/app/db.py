"""Read-only access for the Review API. All state *mutation* (approve/reject)
goes through the Orchestrator's HTTP API instead of writing to Postgres
directly from here -- one writer for run/gate state, this service only reads
to render what a human needs to see.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import psycopg
from psycopg.rows import dict_row

from app.config import settings
from app.pipeline import ARTIFACT_DISPLAY_NAME, ARTIFACT_TYPE_TO_NODE

# Which prior artifact types give a reviewer full context at each gate, per
# AGENT_INSTRUCTIONS.md Section 8's "Presented evidence" for H1-H5.
GATE_CONTEXT_ARTIFACT_TYPES = {
    "H1": ["s1_normalized_requirement", "s2_ambiguity_analysis"],
    "H2": ["s3_test_cases", "s4_test_data"],
    "H3": ["s5_automation_model", "s5_compiled_playwright"],
    "H4": [
        "s6_execution_result",
        "s7_classification",
        "s8_boundary_scan",
        "s9_report",
        "s9_allure_results",
    ],
    "H5": [
        "s10_release_summary",
        "s8_boundary_scan",
        "s9_report",
        "s7_classification",
    ],
}


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(settings.database_url, row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM runs WHERE run_id = %s", (run_id,)).fetchone()


def get_pending_review(run_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM human_reviews
            WHERE run_id = %s AND decision = 'pending'
            ORDER BY created_at DESC LIMIT 1
            """,
            (run_id,),
        ).fetchone()


def get_latest_artifact_by_type(run_id: str, artifact_type: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM artifacts
            WHERE run_id = %s AND type = %s
            ORDER BY version DESC, created_at DESC LIMIT 1
            """,
            (run_id, artifact_type),
        ).fetchone()


def get_artifact(run_id: str, artifact_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM artifacts
            WHERE run_id = %s AND artifact_id = %s
            """,
            (run_id, artifact_id),
        ).fetchone()


def get_review_history(run_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM human_reviews WHERE run_id = %s ORDER BY created_at ASC", (run_id,)
        ).fetchall()


def list_artifacts(run_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT artifact_id, run_id, type, version, storage_uri, created_at
            FROM artifacts
            WHERE run_id = %s
            ORDER BY created_at ASC, type ASC, version ASC
            """,
            (run_id,),
        ).fetchall()


def list_skill_executions(run_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT execution_id, run_id, skill, status, model, created_at, escalation_reason
            FROM skill_executions
            WHERE run_id = %s
            ORDER BY created_at ASC
            """,
            (run_id,),
        ).fetchall()


def latest_skill_failure(run_id: str) -> Optional[dict[str, Any]]:
    """Most recent failed/escalated skill row with a reason (for UI banners)."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT skill, status, model, escalation_reason, created_at
            FROM skill_executions
            WHERE run_id = %s
              AND (
                status IN ('failed', 'escalated')
                OR (escalation_reason IS NOT NULL AND escalation_reason <> '')
              )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()


def list_test_cases(run_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT tc.test_case_id, tc.run_id, tc.version, tc.source_requirement_id, tc.layer,
                   tc.obligation, tc.expected_result, tc.expected_result_basis, tc.duplicate_of,
                   tc.created_at,
                   (
                     SELECT te.status FROM test_executions te
                     WHERE te.run_id = tc.run_id AND te.test_case_id = tc.test_case_id
                     ORDER BY te.created_at DESC LIMIT 1
                   ) AS last_execution_status
            FROM test_cases tc
            WHERE tc.run_id = %s
              AND tc.version = (
                SELECT MAX(tc2.version) FROM test_cases tc2
                WHERE tc2.run_id = tc.run_id AND tc2.test_case_id = tc.test_case_id
              )
            ORDER BY tc.test_case_id ASC
            """,
            (run_id,),
        ).fetchall()


def list_test_executions(run_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT execution_id, run_id, test_case_id, correlation_id, status,
                   classification, retry_attempts, evidence_manifest, created_at
            FROM test_executions
            WHERE run_id = %s
            ORDER BY created_at ASC
            """,
            (run_id,),
        ).fetchall()


def list_test_cases_cross_run(*, limit: int = 100, run_id: Optional[str] = None) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    clauses = [
        """tc.version = (
            SELECT MAX(tc2.version) FROM test_cases tc2
            WHERE tc2.run_id = tc.run_id AND tc2.test_case_id = tc.test_case_id
        )"""
    ]
    params: list[Any] = []
    if run_id:
        clauses.append("tc.run_id = %s")
        params.append(run_id)
    where = " AND ".join(clauses)
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(
            f"""
            SELECT tc.test_case_id, tc.run_id, tc.version, tc.source_requirement_id, tc.layer,
                   tc.obligation, tc.expected_result, tc.expected_result_basis, tc.duplicate_of,
                   tc.created_at,
                   (
                     SELECT te.status FROM test_executions te
                     WHERE te.run_id = tc.run_id AND te.test_case_id = tc.test_case_id
                     ORDER BY te.created_at DESC LIMIT 1
                   ) AS last_execution_status
            FROM test_cases tc
            WHERE {where}
            ORDER BY tc.created_at DESC
            LIMIT %s
            """,
            params,
        ).fetchall()


def list_test_executions_cross_run(*, limit: int = 100, run_id: Optional[str] = None) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    clauses: list[str] = []
    params: list[Any] = []
    if run_id:
        clauses.append("run_id = %s")
        params.append(run_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(
            f"""
            SELECT execution_id, run_id, test_case_id, correlation_id, status,
                   classification, retry_attempts, evidence_manifest, created_at
            FROM test_executions
            {where}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            params,
        ).fetchall()


def list_compiled_script_artifacts_cross_run(
    *, limit: int = 50, run_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Latest s5_compiled_playwright artifact per run (or one run), newest first."""
    limit = max(1, min(int(limit), 200))
    clauses = [
        "type = 's5_compiled_playwright'",
        """version = (
            SELECT MAX(a2.version) FROM artifacts a2
            WHERE a2.run_id = artifacts.run_id AND a2.type = 's5_compiled_playwright'
        )""",
    ]
    params: list[Any] = []
    if run_id:
        clauses.append("run_id = %s")
        params.append(run_id)
    where = " AND ".join(clauses)
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(
            f"""
            SELECT artifact_id, run_id, version, content, created_at
            FROM artifacts
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            params,
        ).fetchall()


def list_knowledge_items(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT knowledge_id, domain, rule, status, source, supersedes, created_at
            FROM knowledge_items
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()


def list_pending_reviews(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT hr.review_id, hr.run_id, hr.gate, hr.artifact_version, hr.created_at AS waiting_since,
                   r.requirement_id, r.status AS run_status, r.current_stage
            FROM human_reviews hr
            JOIN runs r ON r.run_id = hr.run_id
            WHERE hr.decision = 'pending'
            ORDER BY hr.created_at ASC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()


def list_recent_reviews(limit: int = 50) -> list[dict[str, Any]]:
    """Non-pending decisions for Reviews queue (most recent first)."""
    limit = max(1, min(int(limit), 200))
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT hr.review_id, hr.run_id, hr.gate, hr.decision, hr.reviewer, hr.comment,
                   hr.artifact_version, hr.created_at, hr.decided_at,
                   r.requirement_id, r.status AS run_status, r.current_stage
            FROM human_reviews hr
            JOIN runs r ON r.run_id = hr.run_id
            WHERE hr.decision IS NOT NULL AND hr.decision <> 'pending'
            ORDER BY COALESCE(hr.decided_at, hr.created_at) DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()


def count_runs_by_status() -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*)::int AS n FROM runs GROUP BY status"
        ).fetchall()
    return {r["status"]: r["n"] for r in rows}


def count_pending_reviews() -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*)::int AS n FROM human_reviews WHERE decision = 'pending'"
        ).fetchone()
    return int(row["n"]) if row else 0


def execution_stats() -> dict[str, Any]:
    """Aggregate test_executions with S9-aligned classified pass-rate semantics.

    Pass rate denominator = pass + fail_classified (excludes unclassified failures).
    """
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
              COUNT(*)::int AS tests_executed,
              COUNT(*) FILTER (WHERE status = 'pass')::int AS passed,
              COUNT(*) FILTER (WHERE status = 'fail')::int AS failed,
              COUNT(*) FILTER (WHERE status = 'skip')::int AS skipped,
              COUNT(*) FILTER (
                WHERE status = 'fail'
                  AND classification IS NOT NULL
                  AND classification <> 'UNCLASSIFIED_PENDING_TRIAGE'
              )::int AS failed_classified,
              COUNT(*) FILTER (
                WHERE status = 'fail'
                  AND (classification IS NULL OR classification = 'UNCLASSIFIED_PENDING_TRIAGE')
              )::int AS failed_unclassified
            FROM test_executions
            """
        ).fetchone()
    if not row:
        return {
            "tests_executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failed_classified": 0,
            "failed_unclassified": 0,
            "pass_rate": None,
        }
    passed = row["passed"] or 0
    failed_classified = row["failed_classified"] or 0
    denom = passed + failed_classified
    pass_rate = (passed / denom) if denom > 0 else None
    return {
        "tests_executed": row["tests_executed"] or 0,
        "passed": passed,
        "failed": row["failed"] or 0,
        "skipped": row["skipped"] or 0,
        "failed_classified": failed_classified,
        "failed_unclassified": row["failed_unclassified"] or 0,
        "pass_rate": pass_rate,
    }


def list_runs(
    *,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    stage: Optional[str] = None,
) -> tuple[list[dict[str, Any]], int]:
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("r.status = %s")
        params.append(status)
    if stage:
        clauses.append("r.current_stage = %s")
        params.append(stage)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_conn() as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*)::int AS n FROM runs r {where}",
            params,
        ).fetchone()
        total = int(total_row["n"]) if total_row else 0
        rows = conn.execute(
            f"""
            SELECT r.run_id, r.requirement_id, r.status, r.current_stage,
                   r.framework_version, r.rulebook_version, r.model_version,
                   r.created_at, r.updated_at,
                   (
                     SELECT hr.gate FROM human_reviews hr
                     WHERE hr.run_id = r.run_id AND hr.decision = 'pending'
                     ORDER BY hr.created_at DESC LIMIT 1
                   ) AS pending_gate
            FROM runs r
            {where}
            ORDER BY r.updated_at DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        ).fetchall()
    return rows, total


# Back-compat alias used by older callers
def list_recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    rows, _ = list_runs(limit=limit, offset=0)
    return rows


def requirement_summary_for_run(run_id: str) -> Optional[str]:
    """Best-effort short requirement text from S1 artifact content."""
    artifact = get_latest_artifact_by_type(run_id, "s1_normalized_requirement")
    if not artifact:
        return None
    content = artifact.get("content") or {}
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return content[:240] if content else None
    if not isinstance(content, dict):
        return None
    for key in (
        "normalized_requirement",
        "requirement_text",
        "summary",
        "title",
        "obligation",
        "raw",
    ):
        val = content.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:500]
    # Nested common shapes
    req = content.get("requirement")
    if isinstance(req, dict):
        for key in ("text", "summary", "title", "description"):
            val = req.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:500]
    if isinstance(req, str) and req.strip():
        return req.strip()[:500]
    return None


def metadata_from_s1(run_id: str) -> dict[str, Any]:
    """Extract passthrough New Run metadata if preserved inside S1/raw structures."""
    artifact = get_latest_artifact_by_type(run_id, "s1_normalized_requirement")
    meta: dict[str, Any] = {}
    if not artifact:
        return meta
    content = artifact.get("content") or {}
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return meta
    if not isinstance(content, dict):
        return meta
    for key in ("environment", "branch", "base_url", "requirement_type", "labels"):
        if key in content:
            meta[key] = content[key]
    raw = content.get("raw_input") or content.get("source") or {}
    if isinstance(raw, dict):
        for key in ("environment", "branch", "base_url", "requirement_type", "labels", "raw"):
            if key in raw and key not in meta:
                meta[key] = raw[key]
    return meta


def _base_url_from_s6(run_id: str) -> Optional[str]:
    """Fallback: S6 environment_metadata.app_build when it looks like a URL."""
    artifact = get_latest_artifact_by_type(run_id, "s6_execution_result")
    if not artifact:
        return None
    content = artifact.get("content") or {}
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return None
    if not isinstance(content, dict):
        return None
    env = content.get("environment_metadata") or {}
    if not isinstance(env, dict):
        return None
    app_build = env.get("app_build")
    if isinstance(app_build, str) and app_build.strip().lower().startswith(("http://", "https://")):
        return app_build.strip()
    return None


def passthrough_metadata_for_run(run: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Prefer columns on `runs`, then S1 echo, then S6 app_build for base_url."""
    meta = metadata_from_s1(run_id)
    for key in ("base_url", "environment", "branch"):
        row_val = run.get(key)
        if isinstance(row_val, str) and row_val.strip():
            meta[key] = row_val.strip()
        elif key not in meta or meta.get(key) in (None, ""):
            # keep S1 value if present; otherwise leave unset for now
            pass
    if not meta.get("base_url"):
        s6_url = _base_url_from_s6(run_id)
        if s6_url:
            meta["base_url"] = s6_url
    return meta


def artifact_list_status(run_id: str, artifact_type: str, version: int) -> str:
    """Derive display status from linked human reviews when applicable."""
    gate_for_type = {
        "s1_normalized_requirement": "H1",
        "s2_ambiguity_analysis": "H1",
        "s3_test_cases": "H2",
        "s4_test_data": "H2",
        "s5_automation_model": "H3",
        "s5_compiled_playwright": "H3",
        "s6_execution_result": "H4",
        "s7_classification": "H4",
        "s8_boundary_scan": "H4",
        "s9_report": "H4",
        "s9_allure_results": "H4",
        "s10_release_summary": "H5",
    }
    gate = gate_for_type.get(artifact_type)
    if not gate:
        return "Completed"
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT decision FROM human_reviews
            WHERE run_id = %s AND gate = %s AND artifact_version = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (run_id, gate, version),
        ).fetchone()
    if not row:
        # Fall back to latest decision for gate
        pending = get_pending_review(run_id)
        if pending and pending.get("gate") == gate:
            return "Pending"
        hist = get_review_history(run_id)
        for r in reversed(hist):
            if r.get("gate") == gate:
                decision = r.get("decision")
                if decision == "approved":
                    return "Approved"
                if decision == "pending":
                    return "Pending"
                if decision == "rejected":
                    return "Failed"
                if decision == "changes_requested":
                    return "Completed"
                break
        return "Completed"
    decision = row["decision"]
    if decision == "approved":
        return "Approved"
    if decision == "pending":
        return "Pending"
    if decision == "rejected":
        return "Failed"
    return "Completed"


def serialize_artifact_row(row: dict[str, Any], *, include_status: bool = True) -> dict[str, Any]:
    atype = row["type"]
    version = int(row["version"])
    run_id = str(row["run_id"])
    name = ARTIFACT_DISPLAY_NAME.get(atype, f"{atype}.json")
    if atype == "s5_compiled_playwright":
        content = row.get("content")
        if isinstance(content, dict) and content.get("file_name"):
            name = content["file_name"]
    out: dict[str, Any] = {
        "artifact_id": str(row["artifact_id"]),
        "run_id": run_id,
        "type": atype,
        "stage": ARTIFACT_TYPE_TO_NODE.get(atype, atype),
        "name": name,
        "version": version,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "storage_uri": row.get("storage_uri"),
    }
    if include_status:
        out["status"] = artifact_list_status(run_id, atype, version)
    return out


def scripts_from_compiled(run_id: str) -> list[dict[str, Any]]:
    """Flatten s5_compiled_playwright artifacts into script list items.

    Each S5/Compile invoke stores one file as a new artifact version. Keep the
    newest row per file_name (fallback: test_case_id) so H3 / Scripts catalog
    show every compiled spec still on the run, not only the latest version.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT artifact_id, run_id, version, content, created_at
            FROM artifacts
            WHERE run_id = %s AND type = 's5_compiled_playwright'
            ORDER BY version DESC, created_at DESC
            """,
            (run_id,),
        ).fetchall()
    scripts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        for script in flatten_compiled_script_row(row):
            key = str(script.get("file_name") or script.get("test_case_id") or script.get("artifact_id") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            scripts.append(script)
    return scripts


def automation_models_from_s5(run_id: str) -> list[dict[str, Any]]:
    """Newest unique S5 automation model per test_case_id (across invoke versions)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT artifact_id, run_id, version, content, created_at
            FROM artifacts
            WHERE run_id = %s AND type = 's5_automation_model'
            ORDER BY version DESC, created_at DESC
            """,
            (run_id,),
        ).fetchall()
    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        content = row.get("content") or {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                continue
        if not isinstance(content, dict):
            continue
        key = str(content.get("test_case_id") or content.get("script_id") or row.get("artifact_id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        models.append(
            {
                "test_case_id": content.get("test_case_id"),
                "script_id": content.get("script_id"),
                "layer": content.get("layer"),
                "version": int(row["version"]),
                "artifact_id": str(row["artifact_id"]),
                "model": content,
            }
        )
    return models


def flatten_compiled_script_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    content = row.get("content") or {}
    if not isinstance(content, dict):
        return []
    version = int(row["version"])
    run_id = str(row["run_id"])
    artifact_id = str(row["artifact_id"])
    scripts: list[dict[str, Any]] = []
    if content.get("file_name") or content.get("source"):
        scripts.append(
            {
                "script_id": content.get("script_id"),
                "run_id": run_id,
                "test_case_id": content.get("test_case_id"),
                "file_name": content.get("file_name") or "spec.ts",
                "framework": "playwright",
                "version": version,
                "source": content.get("source"),
                "spec_path": content.get("spec_path"),
                "artifact_id": artifact_id,
                "created_at": row.get("created_at"),
            }
        )
        return scripts
    for spec in content.get("specs") or content.get("compiled_specs") or []:
        if not isinstance(spec, dict):
            continue
        scripts.append(
            {
                "script_id": spec.get("script_id"),
                "run_id": run_id,
                "test_case_id": spec.get("test_case_id"),
                "file_name": spec.get("file_name") or "spec.ts",
                "framework": "playwright",
                "version": version,
                "source": spec.get("source"),
                "spec_path": spec.get("spec_path"),
                "artifact_id": artifact_id,
                "created_at": row.get("created_at"),
            }
        )
    return scripts


def list_scripts_cross_run(*, limit: int = 100, run_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Flatten latest compiled Playwright specs across runs."""
    rows = list_compiled_script_artifacts_cross_run(limit=min(limit, 200), run_id=run_id)
    scripts: list[dict[str, Any]] = []
    for row in rows:
        scripts.extend(flatten_compiled_script_row(row))
        if len(scripts) >= limit:
            break
    return scripts[:limit]
