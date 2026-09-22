"""Unit tests for the deterministic S8 policy engine."""
from app.policy_engine import scan_boundaries


def test_clean_scan_for_demo_relative_navigate():
    s5 = {
        "script_id": "SCR-TC-001",
        "test_case_id": "TC-001",
        "layer": "UI",
        "automation_model": {
            "setup": [{"type": "navigate", "target": "/"}],
            "actions": [{"type": "fill", "locator": "#user-name", "value": "standard_user"}],
            "assertions": [],
        },
    }
    out = scan_boundaries(run_id="run-1", s5_output=s5, s6_output={"environment_metadata": {}, "evidence_manifest": []})
    assert out["violations"] == []
    assert out["clean_confirmation"]


def test_blocks_production_host():
    s5 = {
        "automation_model": {
            "setup": [{"type": "navigate", "target": "https://prod.example.com/admin"}],
            "actions": [],
            "assertions": [],
        }
    }
    out = scan_boundaries(run_id="run-1", s5_output=s5)
    assert len(out["violations"]) >= 1
    assert any(v["severity"] == "deny" for v in out["violations"])
    assert out["clean_confirmation"] == ""


def test_escalates_unknown_domain():
    s5 = {
        "automation_model": {
            "setup": [{"type": "navigate", "target": "https://evil.example.org/login"}],
            "actions": [],
            "assertions": [],
        }
    }
    out = scan_boundaries(run_id="run-1", s5_output=s5)
    assert any(v["severity"] == "escalate" for v in out["violations"])


def test_allows_saucedemo_absolute_url():
    s5 = {
        "automation_model": {
            "setup": [{"type": "navigate", "target": "https://www.saucedemo.com/"}],
            "actions": [],
            "assertions": [],
        }
    }
    out = scan_boundaries(run_id="run-1", s5_output=s5)
    assert out["violations"] == []


def test_scans_additional_s5_models_from_compiled_specs():
    latest = {
        "automation_model": {
            "setup": [{"type": "navigate", "target": "/login"}],
            "actions": [],
            "assertions": [],
        }
    }
    other = {
        "automation_model": {
            "setup": [{"type": "navigate", "target": "https://prod.example.com/login"}],
            "actions": [],
            "assertions": [],
        }
    }
    out = scan_boundaries(
        run_id="run-1",
        s5_output=latest,
        compiled_specs={"s5_models": [latest, other]},
    )
    assert any(v["severity"] == "deny" for v in out["violations"])


def test_css_selector_targets_are_not_treated_as_hosts():
    s5 = {
        "automation_model": {
            "setup": [{"type": "navigate", "target": "/"}],
            "actions": [],
            "assertions": [
                {"type": "visible", "target": ".inventory_list", "expected_value": True}
            ],
        }
    }
    out = scan_boundaries(run_id="run-1", s5_output=s5)
    assert out["violations"] == []
    assert out["clean_confirmation"]
