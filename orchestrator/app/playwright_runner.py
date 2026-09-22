"""Run H3-approved compiled Playwright specs and map results to s6.schema.json."""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_DIR = REPO_ROOT / "playwright"
_TC_ID_RE = re.compile(r"TC-[A-Za-z0-9_-]+")
_SPEC_SUFFIXES = (".spec.ts", ".spec.js", ".spec.tsx", ".test.ts", ".ts")


class PlaywrightRunnerError(RuntimeError):
    pass


def _match_test_case_id(text: str | None) -> str | None:
    """Extract a TC-* id from a Playwright spec path or test title.

    Does not scrape Playwright output folders — those include the test title
    after the id (`TC-valid_login_1-…-chromium`) and a greedy match would
    swallow it. Artifact rows use `_test_case_id_for_artifact`.
    """
    if not text:
        return None
    stripped = str(text).strip()
    if _TC_ID_RE.fullmatch(stripped):
        return stripped
    name = Path(stripped.replace("\\", "/")).name
    lowered = name.lower()
    for suffix in _SPEC_SUFFIXES:
        if lowered.endswith(suffix):
            stem = name[: -len(suffix)]
            return stem if _TC_ID_RE.fullmatch(stem) else None
    if _TC_ID_RE.fullmatch(name):
        return name
    return None


def _test_case_id_for_artifact(path: str, known_ids: list[str], fallback: str) -> str:
    """Pick the result test_case_id that appears in an evidence relative path."""
    normalized = path.replace("\\", "/")
    hits = [tc for tc in known_ids if tc and tc in normalized]
    if hits:
        return max(hits, key=len)
    return _match_test_case_id(path) or fallback


def _ids_for_spec(
    spec: dict[str, Any],
    suite: dict[str, Any],
    s5_output: dict[str, Any],
) -> tuple[str, str]:
    """Map one Playwright spec to test_case_id / script_id.

    Compiler writes `{test_case_id}.spec.ts` and titles the test with that id.
    Do not stamp every spec with the latest S5 artifact — S6 globs the whole
    generated/<run_id>/ directory after request-changes compiles more cases.
    """
    fallback_tc = s5_output.get("test_case_id", "TC-UNKNOWN")
    candidates = (
        spec.get("title"),
        spec.get("file"),
        suite.get("file"),
        suite.get("title"),
    )
    test_case_id = None
    for candidate in candidates:
        if isinstance(candidate, str):
            test_case_id = _match_test_case_id(candidate)
            if test_case_id:
                break
    if not test_case_id:
        test_case_id = fallback_tc
    if test_case_id == s5_output.get("test_case_id") and s5_output.get("script_id"):
        script_id = s5_output["script_id"]
    else:
        script_id = f"SCR-{test_case_id}"
    return test_case_id, script_id


def _infer_artifact_type(path: Path) -> str | None:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg"} or "screenshot" in name:
        return "screenshot"
    if suffix in {".webm", ".mp4"} or "video" in name:
        return "video"
    if "trace" in name or suffix == ".zip":
        return "trace"
    if suffix == ".har" or "har" in name:
        return "har"
    return None


def _parse_json_report(
    report: dict[str, Any],
    *,
    s5_output: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (results, retry_log) from Playwright JSON reporter output."""
    fallback_tc = s5_output.get("test_case_id", "TC-UNKNOWN")
    fallback_script = s5_output.get("script_id", f"SCR-{fallback_tc}")
    results: list[dict[str, Any]] = []
    retry_log: list[dict[str, Any]] = []

    def walk_suite(suite: dict[str, Any]) -> None:
        for child in suite.get("suites") or []:
            walk_suite(child)
        for spec in suite.get("specs") or []:
            test_case_id, script_id = _ids_for_spec(spec, suite, s5_output)
            for test in spec.get("tests") or []:
                outcomes = test.get("results") or []
                attempts = max(1, len(outcomes))
                status = "skip"
                duration_ms = 0
                if outcomes:
                    last = outcomes[-1]
                    duration_ms = int(last.get("duration") or 0)
                    raw = (last.get("status") or "").lower()
                    if raw == "passed":
                        status = "pass"
                    elif raw in {"failed", "timedout", "interrupted"}:
                        status = "fail"
                    elif raw == "skipped":
                        status = "skip"
                    else:
                        status = "fail"
                results.append(
                    {
                        "test_case_id": test_case_id,
                        "script_id": script_id,
                        "status": status,
                        "duration_ms": duration_ms,
                    }
                )
                retry_log.append({"test_case_id": test_case_id, "attempts": attempts})

    for suite in report.get("suites") or []:
        walk_suite(suite)

    if not results:
        # Spec file present but reporter empty — treat as fail so S9 still runs.
        results.append(
            {
                "test_case_id": fallback_tc,
                "script_id": fallback_script,
                "status": "fail",
                "duration_ms": 0,
            }
        )
        retry_log.append({"test_case_id": fallback_tc, "attempts": 1})
    return results, retry_log


def run_playwright_suite(
    *,
    run_id: str,
    s5_output: dict[str, Any],
    compiled_specs: dict[str, Any],
    base_url: str | None = None,
) -> dict[str, Any]:
    """Execute compiled specs; upload evidence to MinIO; return S6-shaped dict."""
    correlation_id = str(uuid.uuid4())
    out_dir = Path(compiled_specs.get("out_dir") or (PLAYWRIGHT_DIR / "generated" / run_id))
    if not out_dir.is_dir():
        raise PlaywrightRunnerError(f"Compiled spec directory missing: {out_dir}")

    results_dir = PLAYWRIGHT_DIR / "test-results" / run_id / correlation_id
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / "report.json"

    env = os.environ.copy()
    env["QAZEN_SPEC_DIR"] = str(out_dir.resolve())
    env["QAZEN_OUTPUT_DIR"] = str(results_dir.resolve())
    env["QAZEN_JSON_REPORT"] = str(report_path.resolve())
    env["QAZEN_BASE_URL"] = base_url or os.getenv("QAZEN_BASE_URL", "https://www.saucedemo.com")
    # Headed / slow-mo for local HITL debugging (see README).
    if os.getenv("S6_HEADED", "").strip().lower() in {"1", "true", "yes", "on"}:
        env["S6_HEADED"] = "true"
    slow_mo = os.getenv("S6_SLOW_MO_MS", "").strip()
    if slow_mo:
        env["S6_SLOW_MO_MS"] = slow_mo

    cmd = "npx --yes playwright test -c playwright.config.ts"
    completed = subprocess.run(
        cmd,
        cwd=str(PLAYWRIGHT_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
        check=False,
    )
    # Playwright exits non-zero on test failures; still parse the report.
    report: dict[str, Any] = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    elif completed.returncode != 0:
        raise PlaywrightRunnerError(
            f"Playwright failed before writing a report (exit {completed.returncode}): "
            f"{completed.stderr or completed.stdout}"
        )

    results, retry_log = _parse_json_report(report, s5_output=s5_output)

    # Upload evidence artifacts (best-effort; missing MinIO should not drop results).
    evidence_manifest: list[dict[str, str]] = []
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from storage.minio_client import upload_directory  # type: ignore

        uploaded = upload_directory(results_dir, run_id=run_id, correlation_id=correlation_id)
        fallback_tc = s5_output.get("test_case_id", "TC-UNKNOWN")
        known_ids = [r["test_case_id"] for r in results]
        for item in uploaded:
            art = _infer_artifact_type(Path(item["relative_path"]))
            if art is None:
                continue
            evidence_manifest.append(
                {
                    "test_case_id": _test_case_id_for_artifact(
                        item["relative_path"], known_ids, fallback_tc
                    ),
                    "artifact_type": art,
                    "storage_uri": item["storage_uri"],
                }
            )
    except Exception as exc:  # noqa: BLE001 — evidence is best-effort in Phase 1
        evidence_manifest.append(
            {
                "test_case_id": s5_output.get("test_case_id", "TC-UNKNOWN"),
                "artifact_type": "console_log",
                "storage_uri": f"local://{results_dir.as_posix()}#minio_upload_failed:{type(exc).__name__}",
            }
        )

    return {
        "run_id": run_id,
        "correlation_id": correlation_id,
        "results": results,
        "evidence_manifest": evidence_manifest,
        "environment_metadata": {
            "browser_version": "chromium (playwright 1.48)",
            "os": platform.platform(),
            "runtime_version": platform.python_version(),
            "app_build": env["QAZEN_BASE_URL"],
            "api_schema_version": "n/a",
            "viewport": "1920x1080",
            "playwright_exit_code": completed.returncode,
        },
        "retry_log": retry_log,
    }
