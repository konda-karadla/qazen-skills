"""Allure 2 results writer layered on S9.

Writes Allure-compatible `*-result.json` (+ environment.properties) from S6
execution results and optional S7 classifications. Does not invent metrics —
status and labels come from deterministic pipeline data.

HTML report generation is optional: if the `allure` CLI is on PATH,
`allure generate` runs into `reports/allure-report/<run_id>/`.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from app.config import REPO_ROOT

STATUS_MAP = {
    "pass": "passed",
    "passed": "passed",
    "fail": "failed",
    "failed": "failed",
    "skip": "skipped",
    "skipped": "skipped",
}


def write_allure_results(
    *,
    run_id: str,
    s6_output: dict[str, Any],
    s7_output: Optional[dict[str, Any]] = None,
    s5_output: Optional[dict[str, Any]] = None,
    s9_output: Optional[dict[str, Any]] = None,
    results_root: Optional[Path] = None,
    generate_html: Optional[bool] = None,
) -> dict[str, Any]:
    """Write Allure results for a run. Returns metadata (paths, counts)."""
    enabled = (os.environ.get("ALLURE_ENABLED") or "true").strip().lower()
    if enabled in ("0", "false", "no", "off"):
        return {
            "run_id": run_id,
            "enabled": False,
            "results_dir": None,
            "report_dir": None,
            "result_files": [],
            "test_count": 0,
        }

    root = results_root or (REPO_ROOT / "reports" / "allure-results" / run_id)
    root.mkdir(parents=True, exist_ok=True)

    classification_by_tc = _classification_map(s7_output)
    layer = None
    if s5_output and isinstance(s5_output.get("layer"), str):
        layer = s5_output["layer"]

    env = dict(s6_output.get("environment_metadata") or {})
    evidence_by_tc = _evidence_by_tc(s6_output)
    now_ms = int(time.time() * 1000)

    result_files: list[str] = []
    results = list(s6_output.get("results") or [])
    for idx, row in enumerate(results):
        tc = str(row.get("test_case_id") or f"unknown-{idx}")
        status = STATUS_MAP.get(str(row.get("status") or "").lower(), "unknown")
        duration = row.get("duration_ms")
        start = now_ms + idx
        stop = start + (int(duration) if duration is not None else 0)

        labels = [
            {"name": "framework", "value": "qazen"},
            {"name": "suite", "value": f"run:{run_id}"},
            {"name": "testMethod", "value": tc},
            {"name": "package", "value": "qazen.s6"},
        ]
        if layer:
            labels.append({"name": "layer", "value": layer})
            labels.append({"name": "feature", "value": layer})
        cls = classification_by_tc.get(tc)
        if cls:
            labels.append({"name": "tag", "value": f"classification:{cls}"})
            labels.append({"name": "severity", "value": cls})

        test_uuid = str(uuid.uuid4())
        history_id = hashlib.md5(f"{run_id}:{tc}".encode("utf-8")).hexdigest()
        test_case_id = hashlib.md5(tc.encode("utf-8")).hexdigest()

        attachments = _write_uri_attachments(root, evidence_by_tc.get(tc) or [])

        payload: dict[str, Any] = {
            "uuid": test_uuid,
            "historyId": history_id,
            "testCaseId": test_case_id,
            "name": tc,
            "fullName": f"qazen.s6.{tc}",
            "status": status,
            "stage": "finished",
            "start": start,
            "stop": stop,
            "labels": labels,
            "links": [],
            "parameters": [],
            "steps": [],
            "attachments": attachments,
        }
        if status == "failed":
            detail = f"Test {tc} failed."
            if cls:
                detail += f" S7 classification: {cls}."
            payload["statusDetails"] = {"message": detail, "trace": ""}

        file_name = f"{test_uuid}-result.json"
        (root / file_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        result_files.append(file_name)

    _write_environment(root, run_id=run_id, env=env, s9_output=s9_output)

    report_dir: Optional[str] = None
    html_requested = (
        generate_html
        if generate_html is not None
        else (os.environ.get("ALLURE_GENERATE_HTML") or "true").strip().lower()
        not in ("0", "false", "no", "off")
    )
    if html_requested:
        report_dir = _try_generate_html(run_id, root)

    return {
        "run_id": run_id,
        "enabled": True,
        "results_dir": str(root),
        "report_dir": report_dir,
        "result_files": result_files,
        "test_count": len(result_files),
        "environment_file": "environment.properties",
    }


def append_allure_to_summary(summary: str, allure_meta: dict[str, Any]) -> str:
    if not allure_meta.get("enabled"):
        return summary
    lines = [summary.rstrip(), "", "Allure:"]
    lines.append(f"  Results:  {allure_meta.get('results_dir')}")
    if allure_meta.get("report_dir"):
        lines.append(f"  Report:   {allure_meta.get('report_dir')}")
    else:
        lines.append(
            "  Report:   (not generated — install Allure CLI and set ALLURE_GENERATE_HTML=true)"
        )
    lines.append(f"  Tests:    {allure_meta.get('test_count', 0)}")
    return "\n".join(lines)


def _classification_map(s7_output: Optional[dict[str, Any]]) -> dict[str, str]:
    if not s7_output:
        return {}
    out: dict[str, str] = {}
    for item in s7_output.get("classifications") or []:
        tc = item.get("test_case_id")
        cls = item.get("classification")
        if tc and cls:
            out[str(tc)] = str(cls)
    return out


def _evidence_by_tc(s6_output: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for item in s6_output.get("evidence_manifest") or []:
        tc = str(item.get("test_case_id") or "")
        if not tc:
            continue
        out.setdefault(tc, []).append(
            {
                "artifact_type": str(item.get("artifact_type") or "evidence"),
                "storage_uri": str(item.get("storage_uri") or ""),
            }
        )
    return out


def _write_uri_attachments(root: Path, evidence: list[dict[str, str]]) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for item in evidence:
        uri = item.get("storage_uri") or ""
        if not uri:
            continue
        att_uuid = str(uuid.uuid4())
        # Store URI pointer as text so reports work without downloading MinIO objects.
        file_name = f"{att_uuid}-attachment.txt"
        (root / file_name).write_text(uri, encoding="utf-8")
        attachments.append(
            {
                "name": item.get("artifact_type") or "evidence",
                "type": "text/plain",
                "source": file_name,
            }
        )
    return attachments


def _write_environment(
    root: Path,
    *,
    run_id: str,
    env: dict[str, Any],
    s9_output: Optional[dict[str, Any]],
) -> None:
    lines = [
        f"run_id={run_id}",
        f"browser_version={env.get('browser_version', '')}",
        f"os={env.get('os', '')}",
        f"runtime_version={env.get('runtime_version', '')}",
        f"app_build={env.get('app_build', '')}",
        f"viewport={env.get('viewport', '')}",
    ]
    if s9_output and s9_output.get("aggregate_metrics"):
        m = s9_output["aggregate_metrics"]
        lines.append(f"pass_rate={m.get('pass_rate', '')}")
        lines.append(f"total={m.get('total', '')}")
    (root / "environment.properties").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _try_generate_html(run_id: str, results_dir: Path) -> Optional[str]:
    allure_bin = shutil.which("allure")
    if not allure_bin:
        return None
    report_dir = REPO_ROOT / "reports" / "allure-report" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [allure_bin, "generate", str(results_dir), "-o", str(report_dir), "--clean"],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return str(report_dir)
    except (subprocess.SubprocessError, OSError):
        return None
