"""Unit tests for S6 Playwright JSON → test_case_id mapping (no Playwright / Postgres)."""
from app.playwright_runner import (
    _match_test_case_id,
    _parse_json_report,
    _test_case_id_for_artifact,
)


def _s5_latest_invalid() -> dict:
    return {
        "test_case_id": "TC-invalid_login_1",
        "script_id": "SCR-TC-invalid_login_1",
        "layer": "UI",
    }


def _spec(title: str, file: str, status: str, duration: int) -> dict:
    return {
        "title": title,
        "file": file,
        "tests": [
            {
                "projectName": "chromium",
                "results": [{"status": status, "duration": duration}],
            }
        ],
    }


def test_match_test_case_id_from_compiler_filename_and_windows_path():
    assert _match_test_case_id("TC-valid_login_1.spec.ts") == "TC-valid_login_1"
    assert (
        _match_test_case_id(
            r"C:\qazen\playwright\generated\run\TC-invalid_login_1.spec.ts"
        )
        == "TC-invalid_login_1"
    )
    assert _match_test_case_id("TC-valid_login_1") == "TC-valid_login_1"
    assert _match_test_case_id("login.spec.ts") is None


def test_artifact_path_maps_to_known_result_id():
    known = ["TC-valid_login_1", "TC-invalid_login_1"]
    assert (
        _test_case_id_for_artifact(
            "TC-valid_login_1-TC-valid_login_1-chromium/test-failed-1.png",
            known,
            "TC-UNKNOWN",
        )
        == "TC-valid_login_1"
    )
    assert (
        _test_case_id_for_artifact(
            "orphan/screenshot.png",
            known,
            "TC-invalid_login_1",
        )
        == "TC-invalid_login_1"
    )


def test_parse_json_report_maps_each_spec_file_not_latest_s5():
    report = {
        "suites": [
            {
                "title": "",
                "file": "",
                "suites": [
                    {
                        "title": "TC-invalid_login_1.spec.ts",
                        "file": r"C:\qazen\generated\776c\TC-invalid_login_1.spec.ts",
                        "specs": [
                            _spec(
                                "TC-invalid_login_1",
                                r"C:\qazen\generated\776c\TC-invalid_login_1.spec.ts",
                                "passed",
                                1098,
                            )
                        ],
                    },
                    {
                        "title": "TC-valid_login_1.spec.ts",
                        "file": r"C:\qazen\generated\776c\TC-valid_login_1.spec.ts",
                        "specs": [
                            _spec(
                                "TC-valid_login_1",
                                r"C:\qazen\generated\776c\TC-valid_login_1.spec.ts",
                                "passed",
                                886,
                            )
                        ],
                    },
                ],
            }
        ]
    }
    results, retry_log = _parse_json_report(report, s5_output=_s5_latest_invalid())
    ids = [r["test_case_id"] for r in results]
    assert ids == ["TC-invalid_login_1", "TC-valid_login_1"]
    assert [r["script_id"] for r in results] == [
        "SCR-TC-invalid_login_1",
        "SCR-TC-valid_login_1",
    ]
    assert all(r["status"] == "pass" for r in results)
    assert [r["duration_ms"] for r in results] == [1098, 886]
    assert [e["test_case_id"] for e in retry_log] == ids


def test_parse_json_report_falls_back_to_s5_when_file_has_no_tc_id():
    report = {
        "suites": [
            {
                "title": "orphan.spec.ts",
                "file": "orphan.spec.ts",
                "specs": [_spec("logs in", "orphan.spec.ts", "failed", 12)],
            }
        ]
    }
    results, _retry = _parse_json_report(report, s5_output=_s5_latest_invalid())
    assert results == [
        {
            "test_case_id": "TC-invalid_login_1",
            "script_id": "SCR-TC-invalid_login_1",
            "status": "fail",
            "duration_ms": 12,
        }
    ]


def test_parse_json_report_empty_reporter_uses_s5_fallback():
    results, retry_log = _parse_json_report({}, s5_output=_s5_latest_invalid())
    assert results[0]["test_case_id"] == "TC-invalid_login_1"
    assert results[0]["status"] == "fail"
    assert retry_log == [{"test_case_id": "TC-invalid_login_1", "attempts": 1}]
