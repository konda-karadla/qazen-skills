"""Unit tests for deterministic S10 release summary (no Postgres / gateway)."""
from app.release_summary import build_s10_summary, contains_banned_phrasing


def _s6() -> dict:
    return {
        "results": [
            {"test_case_id": "TC-001", "status": "pass"},
            {"test_case_id": "TC-002", "status": "fail"},
        ],
        "evidence_manifest": [
            {
                "test_case_id": "TC-002",
                "artifact_type": "screenshot",
                "storage_uri": "s3://qa-runs/run-1/TC-002/screenshot.png",
            }
        ],
    }


def _s9() -> dict:
    return {
        "run_id": "run-1",
        "aggregate_metrics": {
            "total": 2,
            "passed": 1,
            "failed": 1,
            "skipped": 0,
            "pass_rate": 0.5,
            "by_layer": {"UI": {"passed": 1, "failed": 1}},
            "by_classification": {"app_bug": 1},
        },
        "trend_data": {"baseline_run_id": None, "stability_metrics": {}},
        "new_vs_known_failures": {"new": ["TC-002"], "known": []},
        "regressions": [],
        "human_readable_summary": "Execution Summary",
    }


def _s7() -> dict:
    return {
        "run_id": "run-1",
        "classifications": [
            {
                "test_case_id": "TC-002",
                "classification": "app_bug",
                "evidence_trail": ["HTTP 500 on checkout"],
                "confidence": "clear",
                "flaky_history_flag": False,
            }
        ],
    }


def test_s10_folds_metrics_app_bugs_and_evidence():
    s8 = {
        "violations": [
            {
                "action": "navigate:https://prod.example.com",
                "source": "s5",
                "severity": "deny",
                "routing_target": "security/release-owner",
                "detail": "blocked host",
            }
        ],
        "clean_confirmation": "",
    }
    summary = build_s10_summary(
        run_id="run-1",
        s9_output=_s9(),
        s7_output=_s7(),
        s8_output=s8,
        s6_output=_s6(),
    )
    assert summary["pass_fail_summary"]["passed"] == 1
    assert summary["pass_fail_summary"]["failed"] == 1
    assert len(summary["outstanding_app_bugs"]) == 1
    assert summary["outstanding_app_bugs"][0]["test_case_id"] == "TC-002"
    assert "s3://qa-runs/run-1/TC-002/screenshot.png" in summary["outstanding_app_bugs"][0]["evidence_uris"]
    assert len(summary["security_violations"]) == 1
    assert summary["baseline_comparison"]["new"] == ["TC-002"]
    assert "baseline_run_id is null" in summary["data_completeness_note"]
    assert not contains_banned_phrasing(summary["factual_narrative"])
    assert "521" not in summary["factual_narrative"]  # sanity: uses real counts
    assert "1 passed" in summary["factual_narrative"] or "1 passed," in summary["factual_narrative"]


def test_s10_notes_missing_s9():
    summary = build_s10_summary(run_id="run-1", s9_output=None, s8_output={"violations": []})
    assert "S9 aggregated report is missing" in summary["data_completeness_note"]
    assert summary["pass_fail_summary"]["total"] == 0


def test_s10_has_no_recommendation_language():
    summary = build_s10_summary(
        run_id="run-1",
        s9_output=_s9(),
        s7_output=_s7(),
        s8_output={"violations": [], "clean_confirmation": "clean"},
        s6_output=_s6(),
    )
    blob = summary["factual_narrative"] + "\n" + summary["data_completeness_note"]
    for phrase in ("recommend", "looks ready", "should ship", "go/no-go", "risky to proceed"):
        assert phrase not in blob.lower()
