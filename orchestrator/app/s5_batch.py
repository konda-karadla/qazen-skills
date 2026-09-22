"""Prepare one S5 invoke per H2-approved test case.

S5's schema is a single automation_model (one test_case_id). The orchestrator
loops H2 cases so every TC gets a compiled spec before H3, instead of waiting
on Request Changes for the rest.
"""
from __future__ import annotations

from typing import Any


def unique_test_cases(s3_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Unique S3 cases in original order (first wins on duplicate ids)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for tc in (s3_output or {}).get("test_cases") or []:
        if not isinstance(tc, dict):
            continue
        tc_id = str(tc.get("test_case_id") or "").strip()
        if not tc_id or tc_id in seen:
            continue
        seen.add(tc_id)
        out.append(tc)
    return out


def payload_for_case(
    *,
    s3_output: dict[str, Any] | None,
    s4_output: dict[str, Any] | None,
    test_case: dict[str, Any],
    review_feedback: str | None = None,
) -> dict[str, Any]:
    """Gateway input that contains only this case + matching S4 datasets."""
    tc_id = str(test_case.get("test_case_id") or "").strip()
    s3 = dict(s3_output or {})
    s3["test_cases"] = [test_case]
    datasets = [
        ds
        for ds in (s4_output or {}).get("datasets") or []
        if isinstance(ds, dict) and ds.get("test_case_id") == tc_id
    ]
    s4 = dict(s4_output or {})
    if datasets:
        s4["datasets"] = datasets
    payload: dict[str, Any] = {
        "s3_output": s3,
        "s4_output": s4,
        "focus_test_case_id": tc_id,
    }
    if review_feedback:
        payload["review_feedback"] = review_feedback
    return payload


def align_s5_output(output: dict[str, Any], test_case_id: str) -> dict[str, Any]:
    """Force model ids onto the requested case so specs do not collide on TC-001."""
    aligned = dict(output)
    aligned["test_case_id"] = test_case_id
    aligned["script_id"] = f"SCR-{test_case_id}"
    model = dict(aligned.get("automation_model") or {})
    assertions = []
    for assertion in model.get("assertions") or []:
        if isinstance(assertion, dict):
            assertions.append({**assertion, "test_case_id": test_case_id})
        else:
            assertions.append(assertion)
    if assertions:
        model["assertions"] = assertions
        aligned["automation_model"] = model
    return aligned
