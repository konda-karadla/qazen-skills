"""Deterministic S9 report builder.

AI does not invent metrics — this module aggregates S6 results (and optional
S7 classifications / S8 violations) into a schema-valid s9_report. The LLM
Gateway fixture/path remains for isolated gateway unit tests only.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

CLASSIFICATION_PENDING = "unclassified_pending_triage"


def build_s9_report(
    *,
    run_id: str,
    s6_output: dict[str, Any],
    s5_output: Optional[dict[str, Any]] = None,
    s7_output: Optional[dict[str, Any]] = None,
    s8_output: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    results = list(s6_output.get("results") or [])
    evidence = list(s6_output.get("evidence_manifest") or [])
    env = dict(s6_output.get("environment_metadata") or {})

    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    skipped = sum(1 for r in results if r.get("status") == "skip")

    by_layer = _by_layer(results, s5_output)
    classification_by_tc = _classification_map(s7_output)
    by_classification = _count_classifications(classification_by_tc)

    unclassified_failures = _unclassified_failure_ids(results, classification_by_tc)
    classified_failed = failed - len(unclassified_failures)
    # Unclassified failures must not contribute to pass-rate (AGENT_INSTRUCTIONS §5).
    rate_denom = passed + max(classified_failed, 0) + skipped
    if rate_denom > 0:
        pass_rate = passed / rate_denom
    elif total == 0:
        pass_rate = 0.0
    else:
        pass_rate = 0.0

    unclassified_note = ""
    if failed and not s7_output:
        unclassified_note = (
            f"{failed} failure(s) are pending S7 classification and are excluded "
            "from pass-rate / classification metrics."
        )
    elif unclassified_failures:
        ids = ", ".join(unclassified_failures)
        unclassified_note = (
            f"{len(unclassified_failures)} failure(s) remain unclassified/pending "
            f"triage and are excluded from pass-rate metrics: {ids}."
        )

    summary = _human_readable_summary(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        pass_rate=pass_rate,
        results=results,
        env=env,
        evidence=evidence,
        by_classification=by_classification,
        s8_output=s8_output,
        unclassified_note=unclassified_note,
    )

    report: dict[str, Any] = {
        "run_id": run_id,
        "aggregate_metrics": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round(pass_rate, 4),
            "by_layer": by_layer,
            "by_classification": by_classification,
        },
        "trend_data": {"baseline_run_id": None, "stability_metrics": {}},
        "new_vs_known_failures": {"new": [], "known": []},
        "regressions": [],
        "human_readable_summary": summary,
    }
    if unclassified_note:
        report["unclassified_note"] = unclassified_note
    return report


def _by_layer(
    results: list[dict[str, Any]], s5_output: Optional[dict[str, Any]]
) -> dict[str, Any]:
    layer = None
    if s5_output and isinstance(s5_output.get("layer"), str):
        layer = s5_output["layer"]
    if not layer:
        return {}
    bucket = {"passed": 0, "failed": 0, "skipped": 0}
    for r in results:
        status = r.get("status")
        if status == "pass":
            bucket["passed"] += 1
        elif status == "fail":
            bucket["failed"] += 1
        elif status == "skip":
            bucket["skipped"] += 1
    return {layer: bucket}


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


def _count_classifications(classification_by_tc: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for cls in classification_by_tc.values():
        counts[cls] += 1
    return dict(counts)


def _unclassified_failure_ids(
    results: list[dict[str, Any]], classification_by_tc: dict[str, str]
) -> list[str]:
    ids: list[str] = []
    for r in results:
        if r.get("status") != "fail":
            continue
        tc = str(r.get("test_case_id", ""))
        cls = classification_by_tc.get(tc)
        if cls is None or cls == CLASSIFICATION_PENDING:
            ids.append(tc)
    return ids


def _human_readable_summary(
    *,
    total: int,
    passed: int,
    failed: int,
    skipped: int,
    pass_rate: float,
    results: list[dict[str, Any]],
    env: dict[str, Any],
    evidence: list[dict[str, Any]],
    by_classification: dict[str, int],
    s8_output: Optional[dict[str, Any]],
    unclassified_note: str,
) -> str:
    lines: list[str] = [
        "Execution Summary",
        "",
        f"Total:        {total}",
        f"Passed:       {passed}",
        f"Failed:       {failed}",
        f"Skipped:      {skipped}",
        "",
        f"Pass Rate:    {pass_rate * 100:.1f}%",
        "",
        "Environment:",
        f"  Browser:      {env.get('browser_version', 'n/a')}",
        f"  OS:           {env.get('os', 'n/a')}",
        f"  Runtime:      {env.get('runtime_version', 'n/a')}",
        f"  Application:  {env.get('app_build', 'n/a')}",
        f"  Viewport:     {env.get('viewport', 'n/a')}",
        "",
        "Results:",
    ]
    if not results:
        lines.append("  (no tests executed)")
    else:
        for r in results:
            dur = r.get("duration_ms")
            dur_s = f" ({dur}ms)" if dur is not None else ""
            lines.append(f"  - {r.get('test_case_id')}: {r.get('status')}{dur_s}")

    if by_classification:
        lines.extend(["", "Failure classifications:"])
        for cls, count in sorted(by_classification.items()):
            lines.append(f"  - {cls}: {count}")

    lines.extend(["", "Artifacts:"])
    if not evidence:
        lines.append("  (none)")
    else:
        by_type: dict[str, list[str]] = defaultdict(list)
        for item in evidence:
            by_type[str(item.get("artifact_type", "unknown"))].append(
                str(item.get("storage_uri", ""))
            )
        for artifact_type in sorted(by_type):
            lines.append(f"  {artifact_type}:")
            for uri in by_type[artifact_type]:
                lines.append(f"    {uri}")

    if s8_output is not None:
        lines.extend(["", "Security / boundary scan (S8):"])
        violations = list(s8_output.get("violations") or [])
        if not violations:
            lines.append(
                f"  {s8_output.get('clean_confirmation') or 'No violations found.'}"
            )
        else:
            lines.append(f"  Violations: {len(violations)}")
            for v in violations:
                lines.append(
                    f"  - [{v.get('severity', '?')}] {v.get('action', '?')} "
                    f"({v.get('source', '?')}): {v.get('detail', '')}"
                )

    if unclassified_note:
        lines.extend(["", f"Note: {unclassified_note}"])

    return "\n".join(lines)
