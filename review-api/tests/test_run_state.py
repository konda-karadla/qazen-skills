"""Unit tests for canonical run UI state mapping."""
from app.run_state import derive_run_ui_state, resolve_current_node_id


def test_h3_pending_awaiting_review():
    ui = derive_run_ui_state(
        status="paused",
        current_stage="H3_pending",
        pending_gate="H3",
        artifacts=[
            {"type": "s5_automation_model"},
            {"type": "s5_compiled_playwright"},
        ],
        reviews=[
            {"gate": "H1", "decision": "approved"},
            {"gate": "H2", "decision": "approved"},
            {"gate": "H3", "decision": "pending"},
        ],
    )
    assert ui["uiStatus"] == "awaiting_review"
    assert ui["currentNodeId"] == "H3"
    assert ui["primaryCta"] == "open_review"
    assert ui["stopRunAvailable"] is False
    assert ui["listStatusPill"]["key"] == "awaiting_review"


def test_rejected_h2():
    ui = derive_run_ui_state(
        status="failed",
        current_stage="H2_rejected",
        pending_gate=None,
        reviews=[
            {"gate": "H1", "decision": "approved"},
            {"gate": "H2", "decision": "rejected"},
        ],
    )
    assert ui["uiStatus"] == "rejected"
    assert ui["currentNodeId"] == "H2"
    assert next(n for n in ui["pipelineNodes"] if n["id"] == "H2")["state"] == "failed"


def test_completed_s11():
    assert resolve_current_node_id(status="completed", current_stage="S11") == "S11"
    ui = derive_run_ui_state(status="completed", current_stage="S11", pending_gate=None)
    assert ui["uiStatus"] == "completed"
    assert ui["primaryCta"] == "view_report"


def test_revising_h3():
    ui = derive_run_ui_state(status="running", current_stage="H3_revising")
    assert ui["uiStatus"] == "revising"
    assert ui["currentNodeId"] == "H3"
    assert ui["progressMessage"] == "Revising the prior phase, then this gate will reopen."


def test_running_s1_not_revising_even_with_changes_requested_history():
    ui = derive_run_ui_state(
        status="running",
        current_stage="S1",
        reviews=[{"gate": "H1", "decision": "changes_requested"}],
    )
    assert ui["uiStatus"] == "running"
    assert ui["currentNodeId"] == "S1"
    assert ui["progressMessage"] == "Normalizing the requirement…"


def test_running_s2_progress():
    ui = derive_run_ui_state(status="running", current_stage="S2")
    assert ui["uiStatus"] == "running"
    assert ui["currentNodeId"] == "S2"
    assert ui["progressMessage"] == "Analyzing ambiguities…"


def test_paused_h1_has_no_progress_message():
    ui = derive_run_ui_state(status="paused", current_stage="H1_pending", pending_gate="H1")
    assert ui["uiStatus"] == "awaiting_review"
    assert ui["progressMessage"] is None
