"""Unit tests for deterministic S11 CI gate adapter."""
import httpx
import pytest

from app.ci_gate import evaluate_and_push


@pytest.fixture(autouse=True)
def _default_ci_gate_mode(monkeypatch):
    monkeypatch.setenv("CI_GATE_MODE", "mock")


def _cfg(**overrides):
    base = {
        "min_pass_rate": 0.95,
        "fail_on_unresolved_security": True,
        "fail_on_critical_test_failed": True,
        "critical_test_ids": [],
        "require_suite_executed": True,
        "cicd_endpoint": "mock://local/ci-gate",
    }
    base.update(overrides)
    return base


def _s9(pass_rate: float = 1.0) -> dict:
    return {
        "aggregate_metrics": {
            "total": 1,
            "passed": 1 if pass_rate >= 1.0 else 0,
            "failed": 0 if pass_rate >= 1.0 else 1,
            "skipped": 0,
            "pass_rate": pass_rate,
            "by_layer": {},
            "by_classification": {},
        }
    }


def test_clean_pass_when_h5_approved():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(1.0),
        s8_output={"violations": []},
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        s10_output={"factual_narrative": "facts"},
        s10_artifact_id="art-10",
        config=_cfg(),
    )
    assert out["status_pushed"] == "pass"
    assert out["push_mode"] == "mock"
    assert out["linked_summary"]["artifact_type"] == "s10_release_summary"
    assert out["fail_reasons"] == []


def test_fail_on_low_pass_rate():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(0.5),
        s8_output={"violations": []},
        s6_output={"results": [{"test_case_id": "TC-001", "status": "fail"}]},
        config=_cfg(min_pass_rate=0.95),
    )
    assert out["status_pushed"] == "fail"
    assert any("pass_rate_below_threshold" in r for r in out["fail_reasons"])


def test_fail_on_security_deny():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(1.0),
        s8_output={
            "violations": [
                {
                    "action": "navigate:https://prod.example.com",
                    "source": "s5",
                    "severity": "deny",
                    "routing_target": "security/release-owner",
                    "detail": "blocked",
                }
            ]
        },
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        config=_cfg(),
    )
    assert out["status_pushed"] == "fail"
    assert any("unresolved_security_violation" in r for r in out["fail_reasons"])


def test_blocked_without_h5():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=False,
        s9_output=_s9(1.0),
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        config=_cfg(),
    )
    assert out["status_pushed"] == "blocked"
    assert "H5" in out["escalation_note"]


def test_blocked_when_threshold_missing():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(1.0),
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        config=_cfg(min_pass_rate=None),
    )
    assert out["status_pushed"] == "blocked"
    assert "threshold" in out["escalation_note"].lower() or "min_pass_rate" in out["escalation_note"]


def test_fail_on_critical_test_failed():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(0.0),
        s8_output={"violations": []},
        s6_output={"results": [{"test_case_id": "TC-CRIT", "status": "fail"}]},
        config=_cfg(critical_test_ids=["TC-CRIT"], min_pass_rate=0.0),
    )
    assert out["status_pushed"] == "fail"
    assert any("critical_test_failed" in r for r in out["fail_reasons"])


def test_fail_when_suite_not_executed():
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(0.0),
        s8_output={"violations": []},
        s6_output={"results": []},
        config=_cfg(min_pass_rate=0.0, require_suite_executed=True),
    )
    assert out["status_pushed"] == "fail"
    assert any("required_suite_not_executed" in r for r in out["fail_reasons"])


def test_http_push_success(monkeypatch):
    monkeypatch.setenv("CI_GATE_MODE", "http")

    class _Resp:
        status_code = 200

    def _post(url, json=None, headers=None, timeout=None):
        assert url == "https://ci.example/webhook"
        assert json["status"] == "pass"
        assert headers["Content-Type"] == "application/json"
        return _Resp()

    monkeypatch.setattr("app.ci_gate.httpx.post", _post)
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(1.0),
        s8_output={"violations": []},
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        config=_cfg(cicd_endpoint="https://ci.example/webhook"),
    )
    assert out["status_pushed"] == "pass"
    assert out["push_mode"] == "http"
    assert out["http_status_code"] == 200


def test_http_push_unreachable_blocks(monkeypatch):
    monkeypatch.setenv("CI_GATE_MODE", "http")

    def _post(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("app.ci_gate.httpx.post", _post)
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(1.0),
        s8_output={"violations": []},
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        config=_cfg(cicd_endpoint="https://ci.example/webhook"),
    )
    assert out["status_pushed"] == "blocked"
    assert "unreachable" in out["escalation_note"].lower()


def test_http_mode_requires_real_endpoint(monkeypatch):
    monkeypatch.setenv("CI_GATE_MODE", "http")
    out = evaluate_and_push(
        run_id="run-1",
        h5_approved=True,
        s9_output=_s9(1.0),
        s8_output={"violations": []},
        s6_output={"results": [{"test_case_id": "TC-001", "status": "pass"}]},
        config=_cfg(cicd_endpoint="mock://local/ci-gate"),
    )
    assert out["status_pushed"] == "blocked"
    assert "cicd_endpoint" in out["escalation_note"]
