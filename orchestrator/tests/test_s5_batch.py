"""Unit tests for one-S5-invoke-per-H2-case batching (no Postgres / LLM)."""
from app.s5_batch import align_s5_output, payload_for_case, unique_test_cases


def test_unique_test_cases_dedupes_and_skips_blank():
    s3 = {
        "test_cases": [
            {"test_case_id": "TC-001", "expected_result": "dashboard"},
            {"test_case_id": "TC-002", "expected_result": "alert"},
            {"test_case_id": "TC-001", "expected_result": "dup"},
            {"expected_result": "no id"},
        ]
    }
    cases = unique_test_cases(s3)
    assert [c["test_case_id"] for c in cases] == ["TC-001", "TC-002"]
    assert unique_test_cases({}) == []
    assert unique_test_cases(None) == []


def test_payload_for_case_scopes_s3_and_matching_s4():
    s3 = {
        "title": "login",
        "test_cases": [
            {"test_case_id": "TC-001", "expected_result": "dashboard"},
            {"test_case_id": "TC-002", "expected_result": "alert"},
        ],
    }
    s4 = {
        "datasets": [
            {"dataset_id": "DS-1", "test_case_id": "TC-001", "data_values": {"u": "valid_user"}},
            {"dataset_id": "DS-2", "test_case_id": "TC-002", "data_values": {"u": "bad"}},
        ]
    }
    payload = payload_for_case(
        s3_output=s3,
        s4_output=s4,
        test_case=s3["test_cases"][1],
        review_feedback="compile invalid too",
    )
    assert payload["focus_test_case_id"] == "TC-002"
    assert payload["s3_output"]["title"] == "login"
    assert [c["test_case_id"] for c in payload["s3_output"]["test_cases"]] == ["TC-002"]
    assert payload["s4_output"]["datasets"] == [s4["datasets"][1]]
    assert payload["review_feedback"] == "compile invalid too"


def test_align_s5_output_rewrites_worked_example_ids():
    raw = {
        "script_id": "SCR-TC-001",
        "test_case_id": "TC-001",
        "layer": "UI",
        "automation_model": {
            "setup": [{"type": "navigate", "target": "/login"}],
            "actions": [],
            "assertions": [
                {
                    "type": "visible",
                    "target": "role=alert",
                    "expected_value": True,
                    "test_case_id": "TC-001",
                }
            ],
        },
        "assertions_plain": ["alert visible"],
    }
    aligned = align_s5_output(raw, "TC-002")
    assert aligned["test_case_id"] == "TC-002"
    assert aligned["script_id"] == "SCR-TC-002"
    assert aligned["automation_model"]["assertions"][0]["test_case_id"] == "TC-002"
    assert raw["test_case_id"] == "TC-001"
