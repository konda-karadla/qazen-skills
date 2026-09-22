"""Unit tests for deterministic S9 report builder (no Postgres / gateway)."""
from app.report_builder import build_s9_report


def _s6_mixed() -> dict:
    return {
        "run_id": "run-1",
        "correlation_id": "corr-1",
        "results": [
            {"test_case_id": "TC-001", "script_id": "SCR-TC-001", "status": "pass", "duration_ms": 100},
            {"test_case_id": "TC-002", "script_id": "SCR-TC-002", "status": "fail", "duration_ms": 200},
        ],
        "evidence_manifest": [
            {
                "test_case_id": "TC-002",
                "artifact_type": "screenshot",
                "storage_uri": "s3://qa-runs/run-1/corr-1/TC-002/screenshot.png",
            },
            {
                "test_case_id": "TC-002",
                "artifact_type": "trace",
                "storage_uri": "s3://qa-runs/run-1/corr-1/TC-002/trace.zip",
            },
        ],
        "environment_metadata": {
            "browser_version": "chromium (playwright 1.48)",
            "os": "Windows",
            "runtime_version": "3.12",
            "app_build": "https://www.saucedemo.com",
            "api_schema_version": "n/a",
            "viewport": "1920x1080",
        },
        "retry_log": [{"test_case_id": "TC-002", "attempts": 1}],
    }


def test_report_counts_and_evidence_uris_from_s6():
    report = build_s9_report(run_id="run-1", s6_output=_s6_mixed(), s5_output={"layer": "UI"})
    metrics = report["aggregate_metrics"]
    assert metrics["total"] == 2
    assert metrics["passed"] == 1
    assert metrics["failed"] == 1
    assert metrics["skipped"] == 0
    assert metrics["by_layer"]["UI"]["passed"] == 1
    assert metrics["by_layer"]["UI"]["failed"] == 1
    assert "unclassified_note" in report
    summary = report["human_readable_summary"]
    assert "Execution Summary" in summary
    assert "s3://qa-runs/run-1/corr-1/TC-002/screenshot.png" in summary
    assert "TC-002: fail" in summary
    assert "Pass Rate:" in summary


def test_report_folds_s7_and_excludes_unclassified_from_pass_rate():
    s7 = {
        "run_id": "run-1",
        "classifications": [
            {
                "test_case_id": "TC-002",
                "classification": "app_bug",
                "evidence_trail": ["HTTP 500"],
                "confidence": "clear",
                "flaky_history_flag": False,
            }
        ],
    }
    report = build_s9_report(run_id="run-1", s6_output=_s6_mixed(), s7_output=s7)
    assert report["aggregate_metrics"]["by_classification"]["app_bug"] == 1
    assert report["aggregate_metrics"]["pass_rate"] == 0.5
    assert "app_bug: 1" in report["human_readable_summary"]
    assert "unclassified_note" not in report


def test_report_includes_s8_violations():
    s8 = {
        "run_id": "run-1",
        "violations": [
            {
                "action": "navigate:https://prod.example.com",
                "source": "s5.automation_model.setup",
                "severity": "deny",
                "routing_target": "security/release-owner",
                "detail": "blocked host",
            }
        ],
        "clean_confirmation": "",
    }
    report = build_s9_report(run_id="run-1", s6_output=_s6_mixed(), s8_output=s8)
    assert "Violations: 1" in report["human_readable_summary"]
    assert "prod.example.com" in report["human_readable_summary"]
