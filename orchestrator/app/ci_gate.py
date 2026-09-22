"""Deterministic S11 CI/CD gate adapter.

Applies suite-configured thresholds after H5 approval and pushes status:
- CI_GATE_MODE=mock (default): record only
- CI_GATE_MODE=http: POST JSON payload to cicd_endpoint (Jenkins webhook / generic receiver)

The LLM never decides pass/fail.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

_CONFIG_PATH = Path(__file__).resolve().parent / "ci_gate_config.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "min_pass_rate": 0.95,
    "fail_on_unresolved_security": True,
    "fail_on_critical_test_failed": True,
    "critical_test_ids": [],
    "critical_test_tags": [],
    "require_suite_executed": True,
    "cicd_endpoint": "mock://local/ci-gate",
}


def load_ci_gate_config(path: Optional[Path] = None) -> dict[str, Any]:
    cfg_path = path or _CONFIG_PATH
    if not cfg_path.exists():
        return dict(_DEFAULT_CONFIG)
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    merged = dict(_DEFAULT_CONFIG)
    merged.update(data)
    return merged


def evaluate_and_push(
    *,
    run_id: str,
    h5_approved: bool,
    s9_output: Optional[dict[str, Any]] = None,
    s8_output: Optional[dict[str, Any]] = None,
    s6_output: Optional[dict[str, Any]] = None,
    s10_output: Optional[dict[str, Any]] = None,
    s10_artifact_id: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    cfg = dict(config) if config is not None else load_ci_gate_config()
    mode = (os.environ.get("CI_GATE_MODE") or "mock").strip().lower()
    endpoint = str(cfg.get("cicd_endpoint") or os.environ.get("CI_GATE_ENDPOINT") or "")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    threshold_applied = {
        "min_pass_rate": cfg.get("min_pass_rate"),
        "fail_on_unresolved_security": bool(cfg.get("fail_on_unresolved_security", True)),
        "fail_on_critical_test_failed": bool(cfg.get("fail_on_critical_test_failed", True)),
        "critical_test_ids": list(cfg.get("critical_test_ids") or []),
        "require_suite_executed": bool(cfg.get("require_suite_executed", True)),
    }

    linked_summary = {
        "run_id": run_id,
        "artifact_type": "s10_release_summary",
        "artifact_id": s10_artifact_id,
    }

    fail_reasons: list[str] = []
    escalation_note = ""
    status = "pass"
    http_status_code: Optional[int] = None

    if not h5_approved:
        status = "blocked"
        escalation_note = "H5 sign-off is not confirmed; CI status was not pushed."
    elif cfg.get("min_pass_rate") is None:
        status = "blocked"
        escalation_note = "No pass/fail threshold (min_pass_rate) is configured for this suite."
    else:
        results = list((s6_output or {}).get("results") or [])
        if threshold_applied["require_suite_executed"] and not results:
            status = "fail"
            fail_reasons.append("required_suite_not_executed: S6 results are empty.")

        if threshold_applied["fail_on_critical_test_failed"]:
            critical_ids = set(str(x) for x in threshold_applied["critical_test_ids"])
            for r in results:
                tc = str(r.get("test_case_id") or "")
                if tc in critical_ids and r.get("status") == "fail":
                    status = "fail"
                    fail_reasons.append(f"critical_test_failed: {tc}")

        metrics = dict((s9_output or {}).get("aggregate_metrics") or {})
        pass_rate = float(metrics.get("pass_rate") or 0.0)
        min_rate = float(threshold_applied["min_pass_rate"])
        if pass_rate < min_rate:
            status = "fail"
            fail_reasons.append(
                f"pass_rate_below_threshold: pass_rate={pass_rate} < min_pass_rate={min_rate}"
            )

        if threshold_applied["fail_on_unresolved_security"]:
            for v in (s8_output or {}).get("violations") or []:
                if str(v.get("severity") or "").lower() == "deny":
                    status = "fail"
                    fail_reasons.append(
                        f"unresolved_security_violation: {v.get('action')}"
                    )

    payload = {
        "run_id": run_id,
        "status": status,
        "threshold_applied": threshold_applied,
        "fail_reasons": fail_reasons,
        "linked_summary": linked_summary,
        "push_timestamp": now,
        "factual_excerpt": (s10_output or {}).get("factual_narrative") or "",
    }

    if status != "blocked" and not escalation_note:
        if mode == "mock":
            pass
        elif mode == "http":
            if not endpoint or endpoint.startswith("mock://"):
                status = "blocked"
                escalation_note = (
                    "CI_GATE_MODE=http requires a real cicd_endpoint "
                    "(set ci_gate_config.json or CI_GATE_ENDPOINT)."
                )
            else:
                try:
                    headers = {"Content-Type": "application/json"}
                    token = (os.environ.get("CI_GATE_TOKEN") or "").strip()
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    resp = httpx.post(endpoint, json=payload, headers=headers, timeout=30.0)
                    http_status_code = resp.status_code
                    if resp.status_code >= 400:
                        status = "blocked"
                        escalation_note = (
                            f"CI endpoint unreachable or rejected push "
                            f"(HTTP {resp.status_code})."
                        )
                except httpx.HTTPError as exc:
                    status = "blocked"
                    escalation_note = f"CI endpoint unreachable: {exc.__class__.__name__}"
        else:
            status = "blocked"
            escalation_note = (
                f"CI_GATE_MODE={mode} is not supported; use mock or http."
            )

    out: dict[str, Any] = {
        "run_id": run_id,
        "threshold_applied": threshold_applied,
        "status_pushed": status,
        "cicd_endpoint": endpoint or "mock://local/ci-gate",
        "push_timestamp": now,
        "linked_summary": linked_summary,
        "push_mode": mode if mode in ("mock", "http") else mode,
        "fail_reasons": fail_reasons,
    }
    if escalation_note:
        out["escalation_note"] = escalation_note
    if http_status_code is not None:
        out["http_status_code"] = http_status_code
    return out
