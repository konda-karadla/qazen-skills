"""The deterministic Orchestrator's LangGraph definition:

    S1 -> S2 -> [H1] -> S3 -> S4 -> [H2] -> S5 -> [H3] -> S6 -> S7 -> S8 -> S9
         -> [H4] -> S10 -> [H5] -> S11 -> END

Gates are `interrupt_before` on the node that starts the *next* stage, so
the graph pauses with exactly the artifacts a human needs for that gate
already computed and persisted:
    interrupt_before "s3"  == H1 (requirement sign-off; S1+S2 already ran)
    interrupt_before "s5"  == H2 (test case review; S3+S4 already ran)
    interrupt_before "s6"  == H3 (script/code review; S5 already ran)
    interrupt_before "s10" == H4 (execution/stability review; S9 already ran)
    interrupt_before "s11" == H5 (release sign-off; S10 already ran)

This module owns sequencing only. It never generates content itself --
skill nodes call the LLM Gateway; S5 also shells to the Automation Model
Compiler; S6 runs Playwright (or the gateway mock when S6_EXECUTION_MODE=mock);
S8 uses the deterministic policy engine; S9 uses the deterministic report builder
(+ Allure results writer); S10 uses the deterministic release summary; S11 uses
the deterministic CI gate.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app import db
from app.allure_reporter import append_allure_to_summary, write_allure_results
from app.ci_gate import evaluate_and_push
from app.compiler_client import compile_s5_model
from app.config import settings
from app.gateway_client import invoke_skill
from app.policy_engine import scan_boundaries
from app.release_summary import build_s10_summary
from app.report_builder import build_s9_report
from app.s5_batch import align_s5_output, payload_for_case, unique_test_cases
from app.state import RunState


def _with_feedback(state: RunState, payload: dict[str, Any]) -> dict[str, Any]:
    """Attach review_feedback when a human requested changes on a prior gate."""
    feedback = state.get("review_feedback")
    if feedback:
        return {**payload, "review_feedback": feedback}
    return payload


def _record(state: RunState, skill_id: str, artifact_type: str, output: dict[str, Any]) -> str:
    artifact_id = db.save_artifact(state["run_id"], artifact_type, output)
    db.save_skill_execution(
        state["run_id"], skill_id, status="succeeded", model=settings.model_version, output_ref=artifact_id
    )
    return artifact_id


def _mark_running(run_id: str, stage: str) -> None:
    """Write current_stage before long work so the UI can show which node is live."""
    db.update_run(run_id, current_stage=stage, status="running")


def node_s1(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S1")
    payload = _with_feedback(state, dict(state["raw_input"]))
    result = invoke_skill("S1", payload)
    artifact_id = _record(state, "S1", "s1_normalized_requirement", result.output)
    return {
        "s1_output": result.output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S1": artifact_id},
    }


def node_s2(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S2")
    result = invoke_skill("S2", _with_feedback(state, {"s1_output": state["s1_output"]}))
    artifact_id = _record(state, "S2", "s2_ambiguity_analysis", result.output)
    db.create_pending_review(state["run_id"], "H1", artifact_id)
    db.update_run(state["run_id"], current_stage="H1_pending", status="paused")
    return {
        "s2_output": result.output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S2": artifact_id},
    }


def node_s3(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S3")
    result = invoke_skill(
        "S3",
        _with_feedback(
            state,
            {"s1_output": state["s1_output"], "s2_output": state["s2_output"]},
        ),
    )
    artifact_id = _record(state, "S3", "s3_test_cases", result.output)
    batch_version = db.next_test_cases_batch_version(state["run_id"])
    with db.get_conn() as conn:
        for tc in result.output.get("test_cases", []):
            conn.execute(
                """
                INSERT INTO test_cases (test_case_id, run_id, version, source_requirement_id, layer,
                                         obligation, expected_result, expected_result_basis, duplicate_of)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, test_case_id, version) DO NOTHING
                """,
                (
                    tc["test_case_id"],
                    state["run_id"],
                    batch_version,
                    tc["source_requirement_id"],
                    tc["layer"],
                    tc["obligation"],
                    tc["expected_result"],
                    tc["expected_result_basis"],
                    None if tc["duplicate_check"] == "new" else tc["duplicate_check"],
                ),
            )
    return {
        "s3_output": result.output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S3": artifact_id},
    }


def node_s4(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S4")
    result = invoke_skill("S4", _with_feedback(state, {"s3_output": state["s3_output"]}))
    artifact_id = _record(state, "S4", "s4_test_data", result.output)
    db.create_pending_review(state["run_id"], "H2", artifact_id)
    db.update_run(state["run_id"], current_stage="H2_pending", status="paused")
    return {
        "s4_output": result.output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S4": artifact_id},
    }


def node_s5(state: RunState) -> dict[str, Any]:
    """Invoke S5 + compile once per H2 test case so H3 sees every spec."""
    run_id = state["run_id"]
    s3_output = state.get("s3_output") or {}
    s4_output = state.get("s4_output") or {}
    cases = unique_test_cases(s3_output)
    if not cases:
        _mark_running(run_id, "S5")
        result = invoke_skill(
            "S5",
            _with_feedback(state, {"s3_output": s3_output, "s4_output": s4_output}),
        )
        artifact_id = _record(state, "S5", "s5_automation_model", result.output)
        _mark_running(run_id, "Compile")
        compiled = compile_s5_model(
            result.output, s4_output=s4_output, run_id=run_id
        )
        compiled_artifact_id = db.save_artifact(
            run_id,
            "s5_compiled_playwright",
            {
                "spec_path": compiled["spec_path"],
                "file_name": compiled["file_name"],
                "script_id": compiled["script_id"],
                "test_case_id": compiled["test_case_id"],
                "source": compiled["source"],
            },
        )
        db.create_pending_review(run_id, "H3", artifact_id)
        db.update_run(run_id, current_stage="H3_pending", status="paused")
        return {
            "s5_output": result.output,
            "compiled_specs": compiled,
            "artifact_ids": {
                **state.get("artifact_ids", {}),
                "S5": artifact_id,
                "S5_compiled": compiled_artifact_id,
            },
        }

    last_model: dict[str, Any] = {}
    last_compiled: dict[str, Any] = {}
    last_s5_artifact = ""
    last_compiled_artifact = ""
    all_compiled: list[dict[str, Any]] = []
    s5_models: list[dict[str, Any]] = []
    n = len(cases)

    for index, test_case in enumerate(cases, start=1):
        tc_id = str(test_case.get("test_case_id") or "TC-UNKNOWN")
        _mark_running(run_id, f"S5 ({index}/{n})")
        result = invoke_skill(
            "S5",
            payload_for_case(
                s3_output=s3_output,
                s4_output=s4_output,
                test_case=test_case,
                review_feedback=state.get("review_feedback"),
            ),
        )
        aligned = align_s5_output(result.output, tc_id)
        last_s5_artifact = _record(state, "S5", "s5_automation_model", aligned)
        last_model = aligned
        s5_models.append(aligned)

        _mark_running(run_id, f"Compile ({index}/{n})")
        compiled = compile_s5_model(
            aligned,
            s4_output=s4_output,
            run_id=run_id,
        )
        last_compiled_artifact = db.save_artifact(
            run_id,
            "s5_compiled_playwright",
            {
                "spec_path": compiled["spec_path"],
                "file_name": compiled["file_name"],
                "script_id": compiled["script_id"],
                "test_case_id": compiled["test_case_id"],
                "source": compiled["source"],
            },
        )
        last_compiled = compiled
        all_compiled.append(
            {
                "spec_path": compiled["spec_path"],
                "file_name": compiled["file_name"],
                "script_id": compiled["script_id"],
                "test_case_id": compiled["test_case_id"],
            }
        )

    compiled_specs = {
        **last_compiled,
        "specs": all_compiled,
        "s5_models": s5_models,
    }

    db.create_pending_review(run_id, "H3", last_s5_artifact)
    db.update_run(run_id, current_stage="H3_pending", status="paused")
    return {
        "s5_output": last_model,
        "compiled_specs": compiled_specs,
        "artifact_ids": {
            **state.get("artifact_ids", {}),
            "S5": last_s5_artifact,
            "S5_compiled": last_compiled_artifact,
        },
    }


def node_s6(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S6")
    if settings.s6_execution_mode == "mock":
        result_output = invoke_skill("S6", {"s5_output": state["s5_output"]}).output
    else:
        from app.playwright_runner import run_playwright_suite

        compiled = state.get("compiled_specs") or {}
        raw = state.get("raw_input") or {}
        base_url = raw.get("base_url") if isinstance(raw, dict) else None
        result_output = run_playwright_suite(
            run_id=state["run_id"],
            s5_output=state["s5_output"],
            compiled_specs=compiled,
            base_url=base_url,
        )

    artifact_id = _record(state, "S6", "s6_execution_result", result_output)
    with db.get_conn() as conn:
        for r in result_output.get("results", []):
            conn.execute(
                """
                INSERT INTO test_executions (run_id, test_case_id, correlation_id, status, evidence_manifest)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    state["run_id"], r["test_case_id"], result_output.get("correlation_id"),
                    r["status"], __import__("json").dumps(result_output.get("evidence_manifest", [])),
                ),
            )
    return {
        "s6_output": result_output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S6": artifact_id},
    }


def node_s7(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S7")
    s6 = state["s6_output"]
    failures = [r for r in (s6.get("results") or []) if r.get("status") == "fail"]
    failure_ids = {r["test_case_id"] for r in failures}
    evidence_for_failures = [
        e for e in (s6.get("evidence_manifest") or []) if e.get("test_case_id") in failure_ids
    ]
    retry_for_failures = [
        r for r in (s6.get("retry_log") or []) if r.get("test_case_id") in failure_ids
    ]
    result = invoke_skill(
        "S7",
        {
            "run_id": state["run_id"],
            "failures": failures,
            "retry_log": retry_for_failures,
            "evidence_manifest": evidence_for_failures,
            "environment_metadata": s6.get("environment_metadata") or {},
            "flaky_history": [],
        },
    )
    # Ensure run_id matches this run even if the mock fixture has a placeholder.
    output = dict(result.output)
    output["run_id"] = state["run_id"]
    # Drop any accidental classifications for non-failures.
    if not failures:
        output["classifications"] = []
    else:
        output["classifications"] = [
            c for c in (output.get("classifications") or []) if c.get("test_case_id") in failure_ids
        ]

    artifact_id = _record(state, "S7", "s7_classification", output)
    return {
        "s7_output": output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S7": artifact_id},
    }


def node_s8(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S8")
    output = scan_boundaries(
        run_id=state["run_id"],
        s5_output=state.get("s5_output"),
        s6_output=state.get("s6_output"),
        compiled_specs=state.get("compiled_specs"),
    )
    artifact_id = _record(state, "S8", "s8_boundary_scan", output)
    return {
        "s8_output": output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S8": artifact_id},
    }


def node_s9(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S9")
    report = build_s9_report(
        run_id=state["run_id"],
        s6_output=state["s6_output"],
        s5_output=state.get("s5_output"),
        s7_output=state.get("s7_output"),
        s8_output=state.get("s8_output"),
    )
    allure_meta = write_allure_results(
        run_id=state["run_id"],
        s6_output=state["s6_output"],
        s7_output=state.get("s7_output"),
        s5_output=state.get("s5_output"),
        s9_output=report,
    )
    report = dict(report)
    report["human_readable_summary"] = append_allure_to_summary(
        report["human_readable_summary"], allure_meta
    )
    artifact_id = _record(state, "S9", "s9_report", report)
    allure_artifact_id = db.save_artifact(state["run_id"], "s9_allure_results", allure_meta)
    db.create_pending_review(state["run_id"], "H4", artifact_id)
    db.update_run(state["run_id"], current_stage="H4_pending", status="paused")
    return {
        "s9_output": report,
        "artifact_ids": {
            **state.get("artifact_ids", {}),
            "S9": artifact_id,
            "S9_allure": allure_artifact_id,
        },
    }


def node_s10(state: RunState) -> dict[str, Any]:
    _mark_running(state["run_id"], "S10")
    summary = build_s10_summary(
        run_id=state["run_id"],
        s9_output=state.get("s9_output"),
        s7_output=state.get("s7_output"),
        s8_output=state.get("s8_output"),
        s6_output=state.get("s6_output"),
    )
    artifact_id = _record(state, "S10", "s10_release_summary", summary)
    db.create_pending_review(state["run_id"], "H5", artifact_id)
    db.update_run(state["run_id"], current_stage="H5_pending", status="paused")
    return {
        "s10_output": summary,
        "artifact_ids": {**state.get("artifact_ids", {}), "S10": artifact_id},
    }


def node_s11(state: RunState) -> dict[str, Any]:
    # Reaching this node means H5 was approved (interrupt_before s11 + approve_gate_and_resume).
    s10_artifact_id = (state.get("artifact_ids") or {}).get("S10")
    output = evaluate_and_push(
        run_id=state["run_id"],
        h5_approved=True,
        s9_output=state.get("s9_output"),
        s8_output=state.get("s8_output"),
        s6_output=state.get("s6_output"),
        s10_output=state.get("s10_output"),
        s10_artifact_id=s10_artifact_id,
    )
    artifact_id = _record(state, "S11", "s11_cicd_status", output)
    db.update_run(state["run_id"], current_stage="S11", status="completed")
    return {
        "s11_output": output,
        "artifact_ids": {**state.get("artifact_ids", {}), "S11": artifact_id},
    }


def build_graph() -> StateGraph:
    graph = StateGraph(RunState)
    for name, fn in [
        ("s1", node_s1), ("s2", node_s2), ("s3", node_s3), ("s4", node_s4),
        ("s5", node_s5), ("s6", node_s6), ("s7", node_s7), ("s8", node_s8),
        ("s9", node_s9), ("s10", node_s10), ("s11", node_s11),
    ]:
        graph.add_node(name, fn)

    graph.add_edge(START, "s1")
    graph.add_edge("s1", "s2")
    graph.add_edge("s2", "s3")
    graph.add_edge("s3", "s4")
    graph.add_edge("s4", "s5")
    graph.add_edge("s5", "s6")
    graph.add_edge("s6", "s7")
    graph.add_edge("s7", "s8")
    graph.add_edge("s8", "s9")
    graph.add_edge("s9", "s10")
    graph.add_edge("s10", "s11")
    graph.add_edge("s11", END)
    return graph


def compile_graph(checkpointer: Any) -> CompiledStateGraph:
    return build_graph().compile(
        checkpointer=checkpointer,
        interrupt_before=["s3", "s5", "s6", "s10", "s11"],
    )
