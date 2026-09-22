"""Deterministic S10 factual release-readiness summary.

Presents facts for H5 only — never go/no-go recommendation language.
LLM Gateway fixtures remain for isolated gateway unit tests only.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# Substrings that must never appear in S10 prose (case-insensitive).
BANNED_PHRASE_PATTERNS = [
    r"\brecommend\b",
    r"\brecommendation\b",
    r"\bgo/?no-?go\b",
    r"\bshould ship\b",
    r"\bshould release\b",
    r"\blooks ready\b",
    r"\bshould be fine\b",
    r"\brisky to proceed\b",
    r"\bready to ship\b",
    r"\bapprove release\b",
    r"\bhold the release\b",
]


def build_s10_summary(
    *,
    run_id: str,
    s9_output: Optional[dict[str, Any]] = None,
    s7_output: Optional[dict[str, Any]] = None,
    s8_output: Optional[dict[str, Any]] = None,
    s6_output: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    completeness_parts: list[str] = []
    if not s9_output:
        completeness_parts.append("S9 aggregated report is missing.")
    if s8_output is None:
        completeness_parts.append("S8 violation log is missing.")

    metrics = dict((s9_output or {}).get("aggregate_metrics") or {})
    pass_fail_summary = {
        "total": int(metrics.get("total") or 0),
        "passed": int(metrics.get("passed") or 0),
        "failed": int(metrics.get("failed") or 0),
        "skipped": int(metrics.get("skipped") or 0),
        "pass_rate": float(metrics.get("pass_rate") or 0.0),
        "by_layer": dict(metrics.get("by_layer") or {}),
        "by_classification": dict(metrics.get("by_classification") or {}),
    }

    evidence_by_tc = _evidence_uris_by_test_case(s6_output)
    outstanding_app_bugs = _outstanding_app_bugs(s7_output, evidence_by_tc)

    security_violations: list[dict[str, str]] = []
    if s8_output is not None:
        for v in s8_output.get("violations") or []:
            security_violations.append(
                {
                    "action": str(v.get("action", "")),
                    "source": str(v.get("source", "")),
                    "severity": str(v.get("severity", "")),
                    "routing_target": str(v.get("routing_target", "")),
                    "detail": str(v.get("detail", "")),
                }
            )

    nv = dict((s9_output or {}).get("new_vs_known_failures") or {})
    trend = dict((s9_output or {}).get("trend_data") or {})
    baseline_run_id = trend.get("baseline_run_id")
    baseline_comparison = {
        "new": list(nv.get("new") or []),
        "known": list(nv.get("known") or []),
        "regressions": list((s9_output or {}).get("regressions") or []),
        "baseline_run_id": baseline_run_id if baseline_run_id else None,
    }
    if baseline_run_id is None and s9_output:
        completeness_parts.append(
            "Release baseline_run_id is null; new/known/regression comparison has no confirmed baseline."
        )

    unclassified = (s9_output or {}).get("unclassified_note") or ""
    if unclassified:
        completeness_parts.append(str(unclassified))

    data_completeness_note = " ".join(completeness_parts) if completeness_parts else ""

    evidence_links = _evidence_links(
        pass_fail_summary=pass_fail_summary,
        outstanding_app_bugs=outstanding_app_bugs,
        security_violations=security_violations,
        s6_output=s6_output,
    )

    factual_narrative = _factual_narrative(
        pass_fail_summary=pass_fail_summary,
        outstanding_app_bugs=outstanding_app_bugs,
        security_violations=security_violations,
        baseline_comparison=baseline_comparison,
        data_completeness_note=data_completeness_note,
    )
    _assert_no_banned_phrases(factual_narrative)
    _assert_no_banned_phrases(data_completeness_note)

    return {
        "run_id": run_id,
        "pass_fail_summary": pass_fail_summary,
        "outstanding_app_bugs": outstanding_app_bugs,
        "security_violations": security_violations,
        "baseline_comparison": baseline_comparison,
        "data_completeness_note": data_completeness_note,
        "evidence_links": evidence_links,
        "factual_narrative": factual_narrative,
    }


def contains_banned_phrasing(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pat, lowered) for pat in BANNED_PHRASE_PATTERNS)


def _assert_no_banned_phrases(text: str) -> None:
    if contains_banned_phrasing(text):
        raise ValueError("S10 output must not contain go/no-go or recommendation phrasing")


def _evidence_uris_by_test_case(s6_output: Optional[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not s6_output:
        return out
    for item in s6_output.get("evidence_manifest") or []:
        tc = str(item.get("test_case_id") or "")
        uri = str(item.get("storage_uri") or "")
        if not tc or not uri:
            continue
        out.setdefault(tc, []).append(uri)
    return out


def _outstanding_app_bugs(
    s7_output: Optional[dict[str, Any]],
    evidence_by_tc: dict[str, list[str]],
) -> list[dict[str, Any]]:
    bugs: list[dict[str, Any]] = []
    if not s7_output:
        return bugs
    for item in s7_output.get("classifications") or []:
        if item.get("classification") != "app_bug":
            continue
        tc = str(item.get("test_case_id") or "")
        trail = item.get("evidence_trail") or []
        detail_parts = [str(x) for x in trail if x]
        if item.get("confidence"):
            detail_parts.append(f"confidence={item.get('confidence')}")
        bugs.append(
            {
                "test_case_id": tc,
                "detail": "; ".join(detail_parts) if detail_parts else "classified as app_bug",
                "evidence_uris": list(evidence_by_tc.get(tc) or []),
            }
        )
    return bugs


def _evidence_links(
    *,
    pass_fail_summary: dict[str, Any],
    outstanding_app_bugs: list[dict[str, Any]],
    security_violations: list[dict[str, str]],
    s6_output: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    all_uris: list[str] = []
    if s6_output:
        for item in s6_output.get("evidence_manifest") or []:
            uri = str(item.get("storage_uri") or "")
            if uri:
                all_uris.append(uri)
    links.append(
        {
            "claim": (
                f"Execution counts: total={pass_fail_summary['total']}, "
                f"passed={pass_fail_summary['passed']}, "
                f"failed={pass_fail_summary['failed']}, "
                f"skipped={pass_fail_summary['skipped']}"
            ),
            "uris": list(dict.fromkeys(all_uris)),
        }
    )
    for bug in outstanding_app_bugs:
        links.append(
            {
                "claim": f"app_bug classification for {bug['test_case_id']}",
                "uris": list(bug.get("evidence_uris") or []),
            }
        )
    if security_violations:
        links.append(
            {
                "claim": f"S8 reported {len(security_violations)} security/boundary violation(s)",
                "uris": [],
            }
        )
    return links


def _factual_narrative(
    *,
    pass_fail_summary: dict[str, Any],
    outstanding_app_bugs: list[dict[str, Any]],
    security_violations: list[dict[str, str]],
    baseline_comparison: dict[str, Any],
    data_completeness_note: str,
) -> str:
    total = pass_fail_summary["total"]
    passed = pass_fail_summary["passed"]
    failed = pass_fail_summary["failed"]
    skipped = pass_fail_summary["skipped"]
    lines = [
        f"The execution completed with {passed} passed, {failed} failed, "
        f"and {skipped} skipped tests out of {total} total.",
        f"Pass rate (classified results only, per S9): {pass_fail_summary['pass_rate'] * 100:.1f}%.",
        f"Outstanding app-bug classifications: {len(outstanding_app_bugs)}.",
    ]
    for bug in outstanding_app_bugs:
        lines.append(f"  - {bug['test_case_id']}: {bug['detail']}")
    by_cls = pass_fail_summary.get("by_classification") or {}
    if by_cls:
        parts = [f"{k}={v}" for k, v in sorted(by_cls.items())]
        lines.append("Failure classifications: " + ", ".join(parts) + ".")
    lines.append(f"S8 security/boundary violations: {len(security_violations)}.")
    for v in security_violations:
        lines.append(
            f"  - [{v.get('severity')}] {v.get('action')}: {v.get('detail')}"
        )
    lines.append(
        "Baseline comparison — "
        f"new={len(baseline_comparison.get('new') or [])}, "
        f"known={len(baseline_comparison.get('known') or [])}, "
        f"regressions={len(baseline_comparison.get('regressions') or [])}, "
        f"baseline_run_id={baseline_comparison.get('baseline_run_id')}."
    )
    if data_completeness_note:
        lines.append(f"Data completeness: {data_completeness_note}")
    return "\n".join(lines)
