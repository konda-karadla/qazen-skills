"""Unit tests for Allure results writer (no Allure CLI required)."""
import json
from pathlib import Path

from app.allure_reporter import append_allure_to_summary, write_allure_results


def _s6() -> dict:
    return {
        "results": [
            {"test_case_id": "TC-001", "status": "pass", "duration_ms": 100},
            {"test_case_id": "TC-002", "status": "fail", "duration_ms": 200},
        ],
        "evidence_manifest": [
            {
                "test_case_id": "TC-002",
                "artifact_type": "screenshot",
                "storage_uri": "s3://qa-runs/run-1/TC-002/screenshot.png",
            }
        ],
        "environment_metadata": {
            "browser_version": "chromium",
            "os": "Windows",
            "runtime_version": "3.12",
            "app_build": "demo",
            "viewport": "1920x1080",
        },
    }


def test_write_allure_results_creates_result_json(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ALLURE_ENABLED", "true")
    monkeypatch.setenv("ALLURE_GENERATE_HTML", "false")
    meta = write_allure_results(
        run_id="run-allure-1",
        s6_output=_s6(),
        s7_output={
            "classifications": [
                {
                    "test_case_id": "TC-002",
                    "classification": "app_bug",
                    "evidence_trail": ["err"],
                    "confidence": "clear",
                    "flaky_history_flag": False,
                }
            ]
        },
        s5_output={"layer": "UI"},
        s9_output={"aggregate_metrics": {"pass_rate": 0.5, "total": 2}},
        results_root=tmp_path / "results",
        generate_html=False,
    )
    assert meta["enabled"] is True
    assert meta["test_count"] == 2
    assert len(meta["result_files"]) == 2
    root = Path(meta["results_dir"])
    assert (root / "environment.properties").exists()
    payloads = []
    for name in meta["result_files"]:
        data = json.loads((root / name).read_text(encoding="utf-8"))
        payloads.append(data)
    by_name = {p["name"]: p for p in payloads}
    assert by_name["TC-001"]["status"] == "passed"
    assert by_name["TC-002"]["status"] == "failed"
    tags = [lbl["value"] for lbl in by_name["TC-002"]["labels"] if lbl["name"] == "tag"]
    assert "classification:app_bug" in tags
    assert by_name["TC-002"]["attachments"]
    att_source = by_name["TC-002"]["attachments"][0]["source"]
    assert "s3://qa-runs/run-1/TC-002/screenshot.png" in (root / att_source).read_text(
        encoding="utf-8"
    )


def test_allure_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ALLURE_ENABLED", "false")
    meta = write_allure_results(
        run_id="run-off",
        s6_output=_s6(),
        results_root=tmp_path / "results",
    )
    assert meta["enabled"] is False
    assert meta["test_count"] == 0
    assert not (tmp_path / "results").exists()


def test_append_allure_to_summary():
    text = append_allure_to_summary(
        "Execution Summary\n",
        {
            "enabled": True,
            "results_dir": "reports/allure-results/run-1",
            "report_dir": None,
            "test_count": 2,
        },
    )
    assert "Allure:" in text
    assert "reports/allure-results/run-1" in text
    assert "not generated" in text
